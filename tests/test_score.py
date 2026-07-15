from scraper.parse import Question
from scraper.score import FEATURED_THRESHOLD, score_question


def _q(title: str) -> Question:
    return Question(
        house="参議院", session=219, number=1, title=title,
        submitter="テスト太郎君", question_url="https://example.invalid/q",
        answer_url="https://example.invalid/a",
    )


class TestScoreQuestion:
    def test_occult_title_exceeds_threshold(self):
        assert score_question(_q("幽霊の存在に関する質問主意書")) >= FEATURED_THRESHOLD

    def test_food_title_exceeds_threshold(self):
        assert score_question(_q("カレーライスの普及に関する質問主意書")) >= FEATURED_THRESHOLD

    def test_policy_title_scores_zero(self):
        assert score_question(_q("令和八年度予算編成の基本方針に関する質問主意書")) == 0

    def test_serious_topic_is_blocked(self):
        # キーワード（温泉）を含んでも深刻な題材（死亡事故）は必ず0
        assert score_question(_q("温泉スキー場で児童死亡事故を招いた施設に関する質問主意書")) == 0

    def test_animal_damage_topic_is_blocked(self):
        assert score_question(_q("クマ被害拡大に対する包括的対策に関する質問主意書")) == 0

    def test_everyday_title_without_keywords_scores_zero(self):
        assert score_question(_q("消費税に関する質問主意書")) == 0

    def test_katakana_substring_not_matched(self):
        # 「アイヌ」に「イヌ」を誤検出しない（ブロック語より先に境界で弾かれることも確認）
        assert score_question(_q("アイヌ文化振興に関する質問主意書")) == 0
        # 「リハーサル」に「サル」を誤検出しない
        assert score_question(_q("式典のリハーサル実施要領に関する質問主意書")) == 0

    def test_katakana_word_with_boundary_matches(self):
        assert score_question(_q("イヌの登録義務に関する質問主意書")) > 0

    def test_drug_topic_is_blocked(self):
        # グミ（45点）を含んでも薬物議題は0
        assert score_question(_q("危険ドラッグを含有するグミの呼称に関する質問主意書")) == 0

    def test_keywords_accumulate(self):
        single = score_question(_q("猫に関する質問主意書"))
        combo = score_question(_q("猫と犬の多頭飼育に関する質問主意書"))
        assert combo > single

    def test_score_never_negative(self):
        assert score_question(_q("")) == 0
