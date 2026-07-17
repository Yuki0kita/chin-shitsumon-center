"""政府答弁の定型文（霞が関文学）分類。

答弁書の抜粋から定型パターンを検出し、カジュアルな一言に意訳する。
定型表現の翻訳であり、答弁の意味は変えない。特定の個人を揶揄する
文言は入れない（プロジェクトの編集方針）。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reply:
    text: str  # 吹き出しに出すカジュアル意訳
    tag: str  # 分類チップの表示名


# 優先順に評価する。答弁抜粋（先頭220字）に最初に一致したものを採用する
_PATTERNS: tuple[tuple[str, Reply], ...] = (
    ("意味するところが必ずしも明らかではない",
     Reply("ご質問の意味がわかりませんでした", "質問返し")),
    ("意味するところが明らかではない",
     Reply("ご質問の意味がわかりませんでした", "質問返し")),
    ("お答えすることは困難",
     Reply("お答えするのは…むずかしいです", "回答困難")),
    ("差し控え",
     Reply("ノーコメントです", "ノーコメント")),
    ("把握していない",
     Reply("把握していません", "未把握")),
    ("承知していない",
     Reply("聞いていません", "未把握")),
    ("指摘は当たらない",
     Reply("その指摘は当たりません", "反論")),
    ("考えていない",
     Reply("やる予定はありません", "予定なし")),
    ("検討",
     Reply("検討します", "検討中")),
    ("引き続き",
     Reply("ひきつづき取り組みます", "継続")),
)

_SNIPPET_LEN = 60


def classify_answer(a_excerpt: str) -> Reply | None:
    """答弁抜粋を定型パターンで分類する。どれにも当たらなければ None。"""
    if not a_excerpt:
        return None
    for pattern, reply in _PATTERNS:
        if pattern in a_excerpt:
            return reply
    return None


def answer_snippet(a_excerpt: str) -> str:
    """定型に当たらない答弁用の冒頭スニペット。"""
    if len(a_excerpt) <= _SNIPPET_LEN:
        return a_excerpt
    return a_excerpt[:_SNIPPET_LEN] + "…"
