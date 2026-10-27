"""収集の実行エントリポイント。

使い方:
    python3 -m scraper.run [--excerpt-budget 300]

MIN_SESSION 以降の全回次の一覧を両院から収集し、件名でスコアリング。
注目質問（EXCERPT_THRESHOLD 以上）は質問・答弁の抜粋を取得し、
それ以外も答弁の抜粋を予算（--excerpt-budget）の範囲で新しい順に取得する。
答弁抜粋は「政府の返事」吹き出しの分類に使う。
結果は data/items.json（蓄積）と site/data/items.json（配信用）へ書き出す。
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import pathlib
import urllib.error

from .client import NotFound, WebClient
from .constants import (
    EXCERPT_MAX_FETCH,
    EXCERPT_THRESHOLD,
    HOUSE_SANGIIN,
    KNOWN_LATEST_SESSION,
    MIN_SESSION,
    SESSION_PROBE_AHEAD,
    sangiin_list_url,
    shugiin_list_url,
)
from .parse import Question, extract_excerpt, parse_sangiin_list, parse_shugiin_list
from .reply import classify_answer
from .score import score_question

logger = logging.getLogger(__name__)

# 一時的な通信失敗として扱い、該当ページだけ飛ばす例外
_FETCH_ERRORS = (urllib.error.URLError, TimeoutError, ConnectionError)


class ListStructureChanged(Exception):
    """一覧が取得できたのに1件も読めない。HTML構造の変更を疑う。"""

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "items.json"
SITE_DATA_PATH = ROOT / "site" / "data" / "items.json"

_SANGIIN_ENC = "utf-8"
_SHUGIIN_ENC = "cp932"


def _collect_house(client: WebClient, house_is_sangiin: bool) -> list[Question]:
    """MIN_SESSION から最新回次まで一覧を巡回する。404が続いたら打ち切る。"""
    questions: list[Question] = []
    session = MIN_SESSION
    misses = 0
    while misses <= SESSION_PROBE_AHEAD or session <= KNOWN_LATEST_SESSION:
        url = (
            sangiin_list_url(session)
            if house_is_sangiin
            else shugiin_list_url(session)
        )
        try:
            html = client.get(url, _SANGIIN_ENC if house_is_sangiin else _SHUGIIN_ENC)
        except NotFound:
            misses += 1
            session += 1
            continue
        except _FETCH_ERRORS as exc:
            # 1回次の取得失敗で全体を止めない。既存データは main() の統合で残る
            logger.warning("一覧を取得できませんでした（飛ばします）: %s %s", url, exc)
            misses += 1
            session += 1
            continue
        parsed = (
            parse_sangiin_list(html, session)
            if house_is_sangiin
            else parse_shugiin_list(html, session)
        )
        if parsed:
            misses = 0
        else:
            # 200で0件（ソフト404や構造変更）も未存在と同じく数える。
            # 数えないと存在しない回次を無限に巡回し続ける
            logger.warning("一覧から1件も読めませんでした（構造変更の可能性）: %s", url)
            misses += 1
        logger.info(
            "%s 第%d回: %d件",
            HOUSE_SANGIIN if house_is_sangiin else "衆議院", session, len(parsed),
        )
        questions.extend(parsed)
        session += 1
    if not questions:
        # 全回次で0件は構造変更か全面的な取得失敗。古いデータを上書きしないよう止める
        raise ListStructureChanged(
            "参議院" if house_is_sangiin else "衆議院"
        )
    return questions


def _fill_excerpts(client: WebClient, questions: list[Question], budget: int) -> int:
    """本文抜粋を予算の範囲で取得し、使ったリクエスト数を返す。

    注目質問（質問+答弁）を優先し、残り予算で全質問の答弁抜粋
    （政府の返事の分類に使う）を新しい順に埋める。
    個別ページの失敗は記録して飛ばし、翌日の実行で再取得する。
    """
    remaining = budget
    featured = [
        q for q in sorted(questions, key=lambda x: x.score, reverse=True)
        if q.score >= EXCERPT_THRESHOLD
    ][:EXCERPT_MAX_FETCH]
    rest = sorted(
        (q for q in questions if q.score < EXCERPT_THRESHOLD),
        key=lambda x: (x.session, x.number), reverse=True,
    )
    for q in featured + rest:
        if remaining <= 0:
            break
        enc = _SANGIIN_ENC if q.house == HOUSE_SANGIIN else _SHUGIIN_ENC
        targets = []
        if q.score >= EXCERPT_THRESHOLD and q.question_url and not q.q_excerpt:
            targets.append(("q_excerpt", q.question_url))
        if q.answer_url and not q.a_excerpt:
            targets.append(("a_excerpt", q.answer_url))
        for attr, url in targets:
            if remaining <= 0:
                break
            remaining -= 1
            try:
                setattr(q, attr, extract_excerpt(client.get(url, enc)))
            except NotFound:
                logger.warning("本文が見つかりません: %s", url)
            except _FETCH_ERRORS as exc:
                logger.warning("本文を取得できませんでした（飛ばします）: %s %s", url, exc)
    return budget - remaining


def _to_record(q: Question) -> dict:
    reply = classify_answer(q.a_excerpt)
    return {
        "id": q.item_id,
        "house": q.house,
        "session": q.session,
        "number": q.number,
        "title": q.title,
        "submitter": q.submitter,
        "question_url": q.question_url,
        "answer_url": q.answer_url,
        "has_answer": q.has_answer,
        "q_excerpt": q.q_excerpt,
        "a_excerpt": q.a_excerpt,
        "score": q.score,
        "reply": reply.text if reply else "",
        "reply_tag": reply.tag if reply else "",
    }


def _load_existing() -> dict[str, dict]:
    if not DATA_PATH.exists():
        return {}
    payload = json.loads(DATA_PATH.read_text())
    return {rec["id"]: rec for rec in payload.get("items", [])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--excerpt-budget", type=int, default=300,
        help="1回の実行で本文抜粋を取得する最大リクエスト数",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    client = WebClient()
    existing = _load_existing()

    questions = _collect_house(client, house_is_sangiin=True) + _collect_house(
        client, house_is_sangiin=False
    )
    for q in questions:
        q.score = score_question(q)
        prev = existing.get(q.item_id)
        if prev:
            q.q_excerpt = prev.get("q_excerpt", "")
            q.a_excerpt = prev.get("a_excerpt", "")

    fetched = _fill_excerpts(client, questions, args.excerpt_budget)

    records = {q.item_id: _to_record(q) for q in questions}
    # 一覧から消えた回次の既存データは残す（保存期間の制約がないため）
    for item_id, rec in existing.items():
        records.setdefault(item_id, rec)

    ordered = sorted(
        records.values(), key=lambda r: (r["session"], r["number"]), reverse=True
    )
    payload = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "参議院・衆議院 質問主意書情報",
        "items": ordered,
    }
    for path in (DATA_PATH, SITE_DATA_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    logger.info(
        "一覧%d件（抜粋新規取得%d件）/ 蓄積%d件 を書き出しました",
        len(questions), fetched, len(ordered),
    )


if __name__ == "__main__":
    main()
