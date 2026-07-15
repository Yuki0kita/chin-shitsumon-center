import pathlib

from scraper.parse import extract_excerpt, parse_sangiin_list, parse_shugiin_list

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _load(name: str, encoding: str = "utf-8") -> str:
    return (FIXTURES / name).read_text(encoding=encoding, errors="replace")


class TestParseSangiinList:
    def test_parses_all_questions(self):
        questions = parse_sangiin_list(_load("sangiin_list_219.html"), 219)
        assert len(questions) == 95

    def test_first_question_fields(self):
        q = parse_sangiin_list(_load("sangiin_list_219.html"), 219)[0]
        assert q.number == 1
        assert q.title == "奨学金返還に係る負担軽減策に関する質問主意書"
        assert q.submitter == "塩村 あやか君"
        assert q.house == "参議院"
        assert q.question_url.endswith("/219/syuh/s219001.htm")
        assert q.answer_url.endswith("/219/touh/t219001.htm")
        assert q.item_id == "s-219-1"

    def test_empty_html(self):
        assert parse_sangiin_list("", 219) == []


class TestParseShugiinList:
    def test_parses_all_questions(self):
        questions = parse_shugiin_list(_load("shugiin_list_221.html", "cp932"), 221)
        assert len(questions) == 36

    def test_first_question_fields(self):
        q = parse_shugiin_list(_load("shugiin_list_221.html", "cp932"), 221)[0]
        assert q.number == 1
        assert q.title == "行き過ぎた緊縮志向に関する質問主意書"
        assert q.submitter == "緒方林太郎君"
        assert q.house == "衆議院"
        assert q.question_url.endswith("/a221001.htm")
        assert q.answer_url.endswith("/b221001.htm")
        assert q.item_id == "h-221-1"

    def test_question_received_without_body_links(self):
        # 「質問受理」段階は本文未掲載。件名・提出者のみでURLは空
        questions = parse_shugiin_list(_load("shugiin_list_221.html", "cp932"), 221)
        q30 = next(q for q in questions if q.number == 30)
        assert q30.question_url == ""
        assert q30.answer_url == ""
        assert not q30.has_answer
        assert q30.submitter == "落合貴之君"

    def test_empty_html(self):
        assert parse_shugiin_list("", 221) == []


class TestExtractExcerpt:
    def test_sangiin_question_body(self):
        excerpt = extract_excerpt(_load("sangiin_question_body.html"))
        assert len(excerpt) > 40
        assert "国会法" not in excerpt  # 提出定型文を含まない
        assert "サイトマップ" not in excerpt  # ナビゲーションを含まない

    def test_shugiin_answer_body(self):
        excerpt = extract_excerpt(_load("shugiin_answer_body.html", "cp932"))
        assert len(excerpt) > 40
        assert excerpt.startswith("お尋ね") or "について" in excerpt

    def test_excerpt_is_capped(self):
        excerpt = extract_excerpt(_load("shugiin_answer_body.html", "cp932"))
        assert len(excerpt) <= 221  # 220 + 省略記号

    def test_empty_html(self):
        assert extract_excerpt("") == ""
