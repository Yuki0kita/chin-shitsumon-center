"""参議院・衆議院の質問主意書一覧および本文ページのパース。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .constants import HOUSE_SANGIIN, HOUSE_SHUGIIN, SANGIIN_BASE, SHUGIIN_BASE


@dataclass
class Question:
    house: str  # 参議院 / 衆議院
    session: int  # 国会回次
    number: int  # 提出番号
    title: str  # 件名
    submitter: str  # 提出者
    question_url: str  # 質問本文（html）
    answer_url: str  # 答弁本文（html）。未受領なら ""
    q_excerpt: str = ""  # 質問本文の抜粋（注目質問のみ）
    a_excerpt: str = ""  # 答弁本文の抜粋（注目質問のみ）
    score: int = 0

    @property
    def item_id(self) -> str:
        prefix = "s" if self.house == HOUSE_SANGIIN else "h"
        return f"{prefix}-{self.session}-{self.number}"

    @property
    def has_answer(self) -> bool:
        return bool(self.answer_url)


def _strip_tags(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def parse_sangiin_list(html: str, session: int) -> list[Question]:
    """参議院の一覧（3行1組のテーブル）から質問主意書を取り出す。

    1行目: 件名（meisaiリンク）
    2行目: 提出番号・提出者・質問本文/答弁本文リンク
    """
    questions: list[Question] = []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    current_title = ""
    for row in rows:
        title_m = re.search(
            r'<a href="meisai/m\d+\.htm"[^>]*>\s*(.*?)\s*</a>', row, re.S
        )
        if title_m:
            current_title = _strip_tags(title_m.group(1))
            continue
        if "提出者" not in row or not current_title:
            continue
        num_m = re.search(r'headers="t\d+"[^>]*>\s*(\d+)', row)
        submitter_m = re.search(r'rowspan="2" class="ta_l">\s*(.*?)\s*</td>', row, re.S)
        q_m = re.search(r'href="(syuh/s\d+\.htm)"', row)
        a_m = re.search(r'href="(touh/t\d+\.htm)"', row)
        if not (num_m and q_m):
            continue
        questions.append(
            Question(
                house=HOUSE_SANGIIN,
                session=session,
                number=int(num_m.group(1)),
                title=current_title,
                submitter=_strip_tags(submitter_m.group(1)) if submitter_m else "",
                question_url=f"{SANGIIN_BASE}/{session}/{q_m.group(1)}",
                answer_url=f"{SANGIIN_BASE}/{session}/{a_m.group(1)}" if a_m else "",
            )
        )
        current_title = ""
    return questions


def parse_shugiin_list(html: str, session: int) -> list[Question]:
    """衆議院の一覧（1行1件のテーブル）から質問主意書を取り出す。"""
    questions: list[Question] = []
    rows = re.findall(r"<TR[^>]*>(.*?)</TR>", html, re.S | re.I)
    for row in rows:
        cells = re.findall(r"<T[DH][^>]*>(.*?)</T[DH]>", row, re.S | re.I)
        if len(cells) < 6:
            continue
        number_text = _strip_tags(cells[0])
        if not number_text.isdigit():
            continue  # ヘッダー行
        # 「質問受理」直後は本文未掲載でリンクが存在しない。件名だけ登録する
        q_m = re.search(r'href="(a\d+\.htm)"', row, re.I)
        a_m = re.search(r'href="(b\d+\.htm)"', row, re.I)
        questions.append(
            Question(
                house=HOUSE_SHUGIIN,
                session=session,
                number=int(number_text),
                title=_strip_tags(cells[1]),
                submitter=_strip_tags(cells[2]),
                question_url=f"{SHUGIIN_BASE}/{q_m.group(1)}" if q_m else "",
                answer_url=f"{SHUGIIN_BASE}/{a_m.group(1)}" if a_m else "",
            )
        )
    return questions


# 本文抜粋から除外する定型行の特徴
_BOILERPLATE_PATTERNS = (
    "質問主意書",  # 件名の繰り返し行
    "に対する答弁書",  # 件名の繰り返し行（答弁側）
    "君提出",  # 「衆議院議員◯◯君提出…」の定型
    "別紙答弁書を送付する",
    "答弁書を送付する",
    "内閣総理大臣",
    "議長",
    "殿",
    "受領",
    "経過へ",
    "質問本文",
    "答弁本文",
    "JavaScript",
)
_EXCERPT_MIN_LINE_LEN = 40
_EXCERPT_MAX_LEN = 220


def extract_excerpt(html: str) -> str:
    """本文ページから最初の実質的な段落を抜粋する。

    ナビゲーションや定型文（提出文・宛名）を飛ばし、
    40文字以上の本文行を最大220文字まで拾う。
    """
    text = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    excerpt = ""
    for line in lines:
        if len(line) < _EXCERPT_MIN_LINE_LEN:
            continue
        if any(p in line for p in _BOILERPLATE_PATTERNS):
            continue
        excerpt += line
        if len(excerpt) >= _EXCERPT_MAX_LEN:
            break
    if len(excerpt) > _EXCERPT_MAX_LEN:
        excerpt = excerpt[:_EXCERPT_MAX_LEN] + "…"
    return excerpt
