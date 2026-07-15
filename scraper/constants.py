"""国会 質問主意書（参議院・衆議院）関連の定数。"""

SANGIIN_BASE = "https://www.sangiin.go.jp/japanese/joho1/kousei/syuisyo"
SHUGIIN_BASE = "https://www.shugiin.go.jp/internet/itdb_shitsumon.nsf/html/shitsumon"

# 収集対象の国会回次（古い側）。これ以降の回次を巡回する（208 = 2022年常会）
MIN_SESSION = 208
# 存在確認する回次の上限余裕。最新回次+2程度まで404を許容して探索する
SESSION_PROBE_AHEAD = 2
# 既知の最新回次（探索の起点。実際の最新はここから前後に探索して決める）
KNOWN_LATEST_SESSION = 221

# リクエスト間の待機秒数（相手は公的サービス。負荷をかけない）
REQUEST_INTERVAL_SEC = 1.0

# 本文抜粋を取得する珍質問スコアの閾値と最大取得件数
EXCERPT_THRESHOLD = 40
EXCERPT_MAX_FETCH = 60

HOUSE_SANGIIN = "参議院"
HOUSE_SHUGIIN = "衆議院"


def sangiin_list_url(session: int) -> str:
    return f"{SANGIIN_BASE}/{session}/syuisyo.htm"


def shugiin_list_url(session: int) -> str:
    return f"{SHUGIIN_BASE}/kaiji{session}_l.htm"
