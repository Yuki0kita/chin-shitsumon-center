"""収集処理の異常系（取得失敗・HTML構造変更）。通信はフェイクで差し替える。"""

import pathlib
import urllib.error

import pytest

from scraper import run
from scraper.client import NotFound
from scraper.constants import KNOWN_LATEST_SESSION, MIN_SESSION
from scraper.parse import Question

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class FakeClient:
    """URLに含まれる文字列ごとに応答を決める。未定義のURLは404。"""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, encoding):
        self.calls.append(url)
        for key, value in self.routes.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise NotFound(url)


def _sangiin_list():
    return (FIXTURES / "sangiin_list_219.html").read_text(encoding="utf-8")


class TestCollectHouse:
    def test_server_error_on_one_session_does_not_stop_others(self):
        client = FakeClient({
            "/218/": urllib.error.HTTPError("u", 503, "busy", None, None),
            "/219/": _sangiin_list(),
        })
        questions = run._collect_house(client, house_is_sangiin=True)
        assert len(questions) == 95
        # 503の後も最新回次まで巡回を続けている
        assert any(f"/{KNOWN_LATEST_SESSION}/" in u for u in client.calls)

    def test_network_error_is_skipped(self):
        client = FakeClient({
            "/208/": urllib.error.URLError("dns"),
            "/219/": _sangiin_list(),
        })
        assert len(run._collect_house(client, house_is_sangiin=True)) == 95

    def test_structure_change_raises_instead_of_silently_emptying(self):
        client = FakeClient({"syuisyo": "<html><table><tr><td>新形式</td></tr></table></html>"})
        with pytest.raises(run.ListStructureChanged):
            run._collect_house(client, house_is_sangiin=True)

    def test_all_sessions_missing_raises(self):
        with pytest.raises(run.ListStructureChanged):
            run._collect_house(FakeClient({}), house_is_sangiin=False)

    def test_probe_stops_after_consecutive_misses(self):
        client = FakeClient({"/219/": _sangiin_list()})
        run._collect_house(client, house_is_sangiin=True)
        assert len(client.calls) <= KNOWN_LATEST_SESSION - MIN_SESSION + 1 + 3


def _q(number, score=0, answer=True):
    return Question(
        house="衆議院", session=220, number=number, title="t", submitter="s",
        question_url=f"https://x/a220{number:03d}.htm",
        answer_url=f"https://x/b220{number:03d}.htm" if answer else "",
        score=score,
    )


_BODY = "<p>" + "本文" * 30 + "</p>"


class TestFillExcerpts:
    def test_one_failure_does_not_abort_the_rest(self):
        client = FakeClient({
            "b220001": urllib.error.HTTPError("u", 500, "err", None, None),
            "b220002": TimeoutError(),
            "b220003": _BODY,
        })
        qs = [_q(1), _q(2), _q(3)]
        run._fill_excerpts(client, qs, budget=10)
        assert qs[0].a_excerpt == "" and qs[1].a_excerpt == ""
        assert qs[2].a_excerpt.startswith("本文")

    def test_budget_counts_failed_requests(self):
        client = FakeClient({"b220": urllib.error.URLError("down")})
        used = run._fill_excerpts(client, [_q(n) for n in range(1, 6)], budget=3)
        assert used == 3
        assert len(client.calls) == 3

    def test_featured_fetches_question_and_answer(self):
        client = FakeClient({"a220001": _BODY, "b220001": _BODY})
        q = _q(1, score=run.EXCERPT_THRESHOLD)
        assert run._fill_excerpts(client, [q], budget=10) == 2
        assert q.q_excerpt and q.a_excerpt

    def test_existing_excerpt_is_not_refetched(self):
        client = FakeClient({})
        q = _q(1)
        q.a_excerpt = "取得済み"
        assert run._fill_excerpts(client, [q], budget=10) == 0
        assert client.calls == []
