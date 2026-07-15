"""収集の実行エントリポイント。

使い方:
    python3 -m scraper.run

MIN_SESSION 以降の全回次の一覧を両院から収集し、件名でスコアリング。
注目質問（EXCERPT_THRESHOLD 以上）は本文・答弁の抜粋も取得する。
結果は data/items.json（蓄積）と site/data/items.json（配信用）へ書き出す。
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import pathlib

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
from .score import score_question

logger = logging.getLogger(__name__)

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
        misses = 0
        parsed = (
            parse_sangiin_list(html, session)
            if house_is_sangiin
            else parse_shugiin_list(html, session)
        )
        logger.info(
            "%s 第%d回: %d件",
            HOUSE_SANGIIN if house_is_sangiin else "衆議院", session, len(parsed),
        )
        questions.extend(parsed)
        session += 1
    return questions


def _to_record(q: Question) -> dict:
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
    }


def _load_existing() -> dict[str, dict]:
    if not DATA_PATH.exists():
        return {}
    payload = json.loads(DATA_PATH.read_text())
    return {rec["id"]: rec for rec in payload.get("items", [])}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    client = WebClient()
    existing = _load_existing()

    questions = _collect_house(client, house_is_sangiin=True) + _collect_house(
        client, house_is_sangiin=False
    )
    for q in questions:
        q.score = score_question(q)

    # 注目質問の本文抜粋。既取得分（答弁済み）は再取得しない
    fetched = 0
    for q in sorted(questions, key=lambda x: x.score, reverse=True):
        if q.score < EXCERPT_THRESHOLD or fetched >= EXCERPT_MAX_FETCH:
            break
        prev = existing.get(q.item_id)
        if prev and prev.get("q_excerpt") and (prev.get("a_excerpt") or not q.has_answer):
            q.q_excerpt = prev["q_excerpt"]
            q.a_excerpt = prev.get("a_excerpt", "")
            continue
        enc = _SANGIIN_ENC if q.house == HOUSE_SANGIIN else _SHUGIIN_ENC
        try:
            q.q_excerpt = extract_excerpt(client.get(q.question_url, enc))
            if q.answer_url:
                q.a_excerpt = extract_excerpt(client.get(q.answer_url, enc))
            fetched += 1
        except NotFound:
            logger.warning("本文が見つかりません: %s", q.question_url)

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
