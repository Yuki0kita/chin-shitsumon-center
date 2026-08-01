import pytest

from poster.compose import compose, select_candidates, title_core
from poster.x_client import (
    MissingCredentials,
    TWEET_WEIGHT_LIMIT,
    load_credentials,
    weighted_length,
)


def _item(**kwargs) -> dict:
    base = {
        "id": "s-219-47", "house": "参議院", "session": 219, "number": 47,
        "title": "闘犬と動物愛護・動物福祉に関する質問主意書",
        "submitter": "テスト太郎君", "score": 90,
        "reply": "ノーコメントです", "reply_tag": "ノーコメント",
    }
    base.update(kwargs)
    return base


class TestWeightedLength:
    def test_ascii_counts_one_each(self):
        assert weighted_length("abc") == 3

    def test_japanese_counts_two_each(self):
        assert weighted_length("国会") == 4

    def test_url_counts_as_23(self):
        assert weighted_length("https://example.com/very/long/path") == 23

    def test_empty(self):
        assert weighted_length("") == 0


class TestTitleCore:
    def test_strips_suffix(self):
        assert title_core("闘犬に関する質問主意書") == "闘犬"

    def test_strips_re_question_suffix(self):
        assert title_core("昆虫食に関する再質問主意書") == "昆虫食"

    def test_keeps_non_standard_title(self):
        assert title_core("その他") == "その他"


class TestCompose:
    def test_contains_topic_and_reply(self):
        text = compose(_item())
        assert "闘犬と動物愛護・動物福祉" in text
        assert "ノーコメントです" in text

    def test_within_tweet_limit(self):
        assert weighted_length(compose(_item())) <= TWEET_WEIGHT_LIMIT

    def test_long_title_still_within_limit(self):
        text = compose(_item(title="あ" * 200 + "に関する質問主意書"))
        assert weighted_length(text) <= TWEET_WEIGHT_LIMIT

    def test_includes_site_url(self):
        assert "chin-shitsumon-center.pages.dev" in compose(_item())

    def test_missing_reply_has_fallback(self):
        text = compose(_item(reply=""))
        assert "政府「" in text


class TestSelectCandidates:
    def test_excludes_already_posted(self):
        items = [_item(id="a"), _item(id="b")]
        assert [i["id"] for i in select_candidates(items, {"a"})] == ["b"]

    def test_excludes_low_score(self):
        assert select_candidates([_item(score=10)], set()) == []

    def test_excludes_without_reply(self):
        assert select_candidates([_item(reply="", reply_tag="")], set()) == []

    def test_prioritises_dodge_replies(self):
        items = [
            _item(id="forward", reply_tag="検討中", reply="検討します"),
            _item(id="dodge", reply_tag="質問返し", reply="ご質問の意味がわかりませんでした"),
        ]
        assert select_candidates(items, set())[0]["id"] == "dodge"

    def test_newer_session_first_within_same_tag(self):
        items = [_item(id="old", session=210), _item(id="new", session=221)]
        assert select_candidates(items, set())[0]["id"] == "new"

    def test_empty_input(self):
        assert select_candidates([], set()) == []


class TestLoadCredentials:
    def test_raises_when_missing(self):
        with pytest.raises(MissingCredentials):
            load_credentials({"X_API_KEY": "only-one"})

    def test_returns_all_four(self):
        env = {
            "X_API_KEY": "k", "X_API_SECRET": "s",
            "X_ACCESS_TOKEN": "t", "X_ACCESS_SECRET": "ts",
        }
        assert load_credentials(env) == env
