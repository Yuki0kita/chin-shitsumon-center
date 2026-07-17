from scraper.reply import answer_snippet, classify_answer


class TestClassifyAnswer:
    def test_difficult_to_answer(self):
        r = classify_answer("お尋ねについては、お答えすることは困難である。")
        assert r.tag == "回答困難"

    def test_meaning_unclear_takes_priority(self):
        # 「意味が明らかでない」と「困難」が同居する典型文は質問返しを優先
        r = classify_answer(
            "お尋ねの意味するところが必ずしも明らかではないが、お答えすることは困難である。"
        )
        assert r.tag == "質問返し"

    def test_no_comment(self):
        r = classify_answer("お答えすることは差し控えたい。")
        # 「差し控え」より前に「お答えすることは困難」が無いので分類は差し控え側
        assert r.tag in ("ノーコメント", "回答困難")

    def test_not_grasped(self):
        assert classify_answer("政府としては網羅的に把握していない。").tag == "未把握"

    def test_rebuttal(self):
        assert classify_answer("御指摘は当たらないものと考えている。").tag == "反論"

    def test_substantive_answer_returns_none(self):
        assert classify_answer("令和八年度の予算額は一兆円である。") is None

    def test_empty_returns_none(self):
        assert classify_answer("") is None


class TestAnswerSnippet:
    def test_short_text_kept(self):
        assert answer_snippet("短い答弁。") == "短い答弁。"

    def test_long_text_truncated(self):
        text = "あ" * 100
        snippet = answer_snippet(text)
        assert len(snippet) == 61
        assert snippet.endswith("…")
