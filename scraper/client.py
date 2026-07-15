"""参議院・衆議院サイトの取得クライアント（標準ライブラリのみ）。

リクエストごとに REQUEST_INTERVAL_SEC 待機し、一時的な失敗はリトライする。
参議院はUTF-8、衆議院はShift_JIS（cp932）でデコードする。
"""

from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request

from .constants import REQUEST_INTERVAL_SEC

logger = logging.getLogger(__name__)

_USER_AGENT = "chin-shitsumon-center/0.1 (personal aggregator; polite crawl)"
_REQUEST_TIMEOUT_SEC = 30
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SEC = 5


class NotFound(Exception):
    """404。回次がまだ存在しない場合に投げる。"""


class WebClient:
    def __init__(self, interval_sec: float = REQUEST_INTERVAL_SEC) -> None:
        self._interval = interval_sec
        self._opener = urllib.request.build_opener()
        self._opener.addheaders = [("User-Agent", _USER_AGENT)]

    def get(self, url: str, encoding: str) -> str:
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            time.sleep(self._interval)
            try:
                with self._opener.open(url, timeout=_REQUEST_TIMEOUT_SEC) as res:
                    return res.read().decode(encoding, errors="replace")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise NotFound(url) from exc
                if attempt == _RETRY_ATTEMPTS:
                    raise
                logger.warning(
                    "HTTP %d (%d/%d), retrying in %ss: %s",
                    exc.code, attempt, _RETRY_ATTEMPTS, _RETRY_BACKOFF_SEC, url,
                )
                time.sleep(_RETRY_BACKOFF_SEC)
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == _RETRY_ATTEMPTS:
                    raise
                logger.warning(
                    "request failed (%d/%d), retrying in %ss: %s",
                    attempt, _RETRY_ATTEMPTS, _RETRY_BACKOFF_SEC, exc,
                )
                time.sleep(_RETRY_BACKOFF_SEC)
        raise AssertionError("unreachable")
