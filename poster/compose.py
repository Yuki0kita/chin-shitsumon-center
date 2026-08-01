"""投稿する質問の選定と、投稿文の組み立て。

質問主意書は国政調査の正式な制度であり、投稿文は事実（件名・答弁の定型文）
のみを扱う。提出者個人を揶揄する表現や、政治的な論評は入れない。
"""

from __future__ import annotations

import random
import re

from .x_client import TWEET_WEIGHT_LIMIT, weighted_length

SITE_URL = "https://chin-shitsumon-center.pages.dev/"

# 投稿対象にする最低スコア（sites側の「注目の質問」と同じ基準）
MIN_SCORE = 40
# 件名が長すぎる場合の打ち切り文字数
MAX_TITLE_LEN = 60

# 冒頭のフック。毎回同じだと機械的に見えるため複数から選ぶ
_HOOKS = (
    "【国会で実際にあったやり取り】",
    "【実話】国会でのこんな質問と答え",
    "【今日の質問主意書】",
    "【国会にはこんな質問も出ています】",
)

# 「はぐらかし系」の答弁が付いたものを優先的に選ぶ（意外性が伝わりやすい）
_PRIORITY_TAGS = ("質問返し", "回答困難", "ノーコメント", "未把握")

_TITLE_SUFFIX_RE = re.compile(r"(等)?に(関|係)する(再)?質問主意書$")


def title_core(title: str) -> str:
    """件名から定型末尾を外して「お題」にする。"""
    return _TITLE_SUFFIX_RE.sub("", title) or title


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def compose(item: dict, rng: random.Random | None = None) -> str:
    """1件ぶんの投稿文を組み立てる。"""
    chooser = rng or random
    topic = _truncate(title_core(item["title"]), MAX_TITLE_LEN)
    reply = item.get("reply") or "（答弁書は公開されています）"
    lines = [
        chooser.choice(_HOOKS),
        "",
        f"議員「{topic}について教えてください」",
        f"政府「{reply}」",
        "",
        f"第{item['session']}回国会 / {item['house']} 第{item['number']}号",
        SITE_URL,
    ]
    text = "\n".join(lines)

    # 長すぎる場合は件名をさらに詰める
    while weighted_length(text) > TWEET_WEIGHT_LIMIT and len(topic) > 10:
        topic = _truncate(topic.rstrip("…")[:-5], MAX_TITLE_LEN)
        lines[2] = f"議員「{topic}について教えてください」"
        text = "\n".join(lines)
    return text


def select_candidates(items: list[dict], posted_ids: set[str]) -> list[dict]:
    """投稿候補を、優先度の高い順に並べて返す。

    条件: 未投稿・スコアが基準以上・答弁の意訳がある。
    はぐらかし系の答弁を優先し、同順位内では新しい国会回次を先にする。
    """
    candidates = [
        item
        for item in items
        if item["id"] not in posted_ids
        and item.get("score", 0) >= MIN_SCORE
        and item.get("reply")
    ]

    def sort_key(item: dict) -> tuple:
        tag = item.get("reply_tag", "")
        priority = _PRIORITY_TAGS.index(tag) if tag in _PRIORITY_TAGS else len(_PRIORITY_TAGS)
        return (priority, -item.get("session", 0), -item.get("score", 0))

    return sorted(candidates, key=sort_key)
