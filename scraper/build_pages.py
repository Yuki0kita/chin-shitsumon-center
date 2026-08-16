"""検索の受け皿になる静的ページを生成する。

背景:
    このサイトは本文をJavaScriptで描画しているため、初期HTMLには
    「読み込んでいます…」しか入っていない。検索エンジンから見ると
    2908件のデータがあっても着地できるページが2枚しかない状態になる。

方針:
    スコアの付いた質問（＝サイトの中身そのもの）だけを個別ページにする。
    全件を量産すると中身の薄いページが大量に並び、かえって評価を落とす。

生成物:
    site/q/<id>.html   個別ページ
    site/sitemap.xml
    site/robots.txt
    site/404.html
"""

from __future__ import annotations

import html
import json
import pathlib
import re
from datetime import datetime, timezone

BASE_URL = "https://chin-shitsumon-center.pages.dev"

SITE_DIR = pathlib.Path(__file__).resolve().parent.parent / "site"
DATA_PATH = SITE_DIR / "data" / "items.json"
DETAIL_DIR = SITE_DIR / "q"

# 個別ページを作る下限スコア。これ未満は題材の意外性が確認できておらず、
# 単独のページとして成立しないため一覧の中だけで扱う
MIN_SCORE_FOR_PAGE = 2

# idが想定外の文字を含む場合にパスとして使わないための検査
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]+$")

ICON = (
    "data:image/svg+xml,&lt;svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'&gt;"
    "&lt;rect width='100' height='100' rx='22' fill='%236741d9'/&gt;"
    "&lt;text x='50' y='72' font-size='60' text-anchor='middle' fill='white' "
    "font-family='sans-serif' font-weight='bold'&gt;珍&lt;/text&gt;&lt;/svg&gt;"
)


def esc(value) -> str:
    """HTMLに埋め込む前に必ず通す。件名や提出者名は外部サイト由来のため"""
    return html.escape("" if value is None else str(value), quote=True)


def load_items() -> list[dict]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return data.get("items", [])


def page_items(items: list[dict]) -> list[dict]:
    """個別ページを作る対象を、スコアの高い順に返す"""
    picked = [i for i in items if (i.get("score") or 0) >= MIN_SCORE_FOR_PAGE]
    picked = [i for i in picked if SAFE_ID.match(str(i.get("id") or ""))]
    picked.sort(key=lambda i: i.get("score") or 0, reverse=True)
    return picked


def detail_html(item: dict) -> str:
    title = esc(item.get("title"))
    house = esc(item.get("house"))
    session = esc(item.get("session"))
    number = esc(item.get("number"))
    submitter = esc(item.get("submitter"))
    q_excerpt = esc(item.get("q_excerpt"))
    a_excerpt = esc(item.get("a_excerpt"))
    url = f"{BASE_URL}/q/{item['id']}.html"

    # 検索結果に出る説明文。件名だけでは中身が伝わらないため議院と回次を添える
    description = esc(
        f"第{item.get('session')}回国会で{item.get('house')}に提出された"
        f"「{item.get('title')}」の概要と政府答弁。提出者は{item.get('submitter')}。"
    )

    sources = []
    if item.get("question_url"):
        sources.append(f'<li><a href="{esc(item["question_url"])}">質問主意書の全文（公式）</a></li>')
    if item.get("answer_url"):
        sources.append(f'<li><a href="{esc(item["answer_url"])}">答弁書の全文（公式）</a></li>')
    sources_html = "\n        ".join(sources) or "<li>公式ページのリンクは準備中です。</li>"

    excerpt_blocks = []
    if q_excerpt:
        excerpt_blocks.append(f"<h2>質問の抜粋</h2>\n      <p>{q_excerpt}</p>")
    if a_excerpt:
        excerpt_blocks.append(f"<h2>答弁の抜粋</h2>\n      <p>{a_excerpt}</p>")
    excerpts_html = "\n\n      ".join(excerpt_blocks)

    jsonld = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Article",
                    "headline": item.get("title"),
                    "description": (
                        f"第{item.get('session')}回国会で{item.get('house')}に提出された"
                        f"質問主意書と政府答弁の概要。"
                    ),
                    "inLanguage": "ja",
                    "url": url,
                    "isPartOf": {"@type": "WebSite", "name": "日本珍質問センター", "url": BASE_URL + "/"},
                },
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "日本珍質問センター", "item": BASE_URL + "/"},
                        {"@type": "ListItem", "position": 2, "name": item.get("title"), "item": url},
                    ],
                },
            ],
        },
        ensure_ascii=False,
        indent=2,
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}｜日本珍質問センター</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{url}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta property="og:title" content="{title}｜日本珍質問センター">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE_URL}/og.png">
  <meta property="og:site_name" content="日本珍質問センター">
  <meta property="og:locale" content="ja_JP">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="{ICON}">
  <link rel="stylesheet" href="../css/style.css">
  <script type="application/ld+json">
{jsonld}
  </script>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="../">日本珍質問センター</a></h1>
      <p class="site-tagline">国会でホントにあった質問と、政府のホントの返事を、ゆるっと配信しています。</p>
    </div>
  </header>

  <main class="container">
    <article class="about-body">
      <p><a href="../">一覧に戻る</a></p>

      <h1>{title}</h1>
      <p class="item-meta">{house}／第{session}回国会／第{number}号／提出者 {submitter}</p>

      {excerpts_html}

      <h2>原文を読む</h2>
      <p>ここに載せているのは抜粋です。全文は公式ページで確認できます。</p>
      <ul>
        {sources_html}
      </ul>
    </article>
  </main>

  <footer class="site-footer">
    <div class="container">
      <p>出典: 参議院・衆議院ウェブサイトの質問主意書情報を編集して配信しています。</p>
      <p>質問主意書は国会法に基づく国政調査の正式な制度です。当サイトは制度や提出者を揶揄する意図を持ちません。</p>
      <p>当サイトは国会・各議院とは関係のない個人運営のサイトです。<a href="../about.html">このサイトについて</a></p>
    </div>
  </footer>
</body>
</html>
"""


def not_found_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ページが見つかりません｜日本珍質問センター</title>
  <meta name="robots" content="noindex">
  <link rel="icon" href="{ICON}">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <h1 class="site-title"><a href="/">日本珍質問センター</a></h1>
    </div>
  </header>
  <main class="container">
    <article class="about-body">
      <h1>ページが見つかりません</h1>
      <p>お探しのページは移動したか、URLが間違っている可能性があります。</p>
      <p><a href="/">一覧から探す</a></p>
    </article>
  </main>
</body>
</html>
"""


def archive_block(detail: list[dict]) -> str:
    """トップに置く静的な一覧。

    ふたつの役割がある。
      1. 個別ページへのリンク経路を作る。sitemapだけでは孤立ページになりやすい
      2. 初期HTMLに実際の文字を載せる。JavaScriptでの描画だけだと、
         検索エンジンから見たときに中身が空のページになる
    """
    rows = "\n".join(
        f'        <li><a href="q/{esc(i["id"])}.html">{esc(i.get("title"))}</a>'
        f' <span class="item-meta">{esc(i.get("house"))}／第{esc(i.get("session"))}回</span></li>'
        for i in detail
    )
    return (
        '    <section aria-labelledby="archive-heading">\n'
        '      <h2 id="archive-heading" class="section-heading">珍質問アーカイブ</h2>\n'
        "      <p>とくに題材が変わっている質問を、個別のページにまとめています。</p>\n"
        '      <ul class="archive-list">\n'
        f"{rows}\n"
        "      </ul>\n"
        "    </section>"
    )


def inject_archive(detail: list[dict]) -> None:
    """index.html のマーカー間を書き換える"""
    path = SITE_DIR / "index.html"
    text = path.read_text(encoding="utf-8")

    start = "<!-- ARCHIVE:START 以下は scraper/build_pages.py が生成する。手で編集しない -->"
    end = "<!-- ARCHIVE:END -->"

    if start not in text or end not in text:
        raise SystemExit("index.html に ARCHIVE マーカーが見つかりません")

    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)

    path.write_text(
        f"{head}{start}\n{archive_block(detail)}\n    {end}{tail}",
        encoding="utf-8",
    )


def build_sitemap(detail: list[dict]) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [(f"{BASE_URL}/", "1.0"), (f"{BASE_URL}/about.html", "0.4")]
    urls += [(f"{BASE_URL}/q/{i['id']}.html", "0.7") for i in detail]

    body = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        f"    <priority>{priority}</priority>\n  </url>"
        for loc, priority in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )


def build_robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n"


def main() -> None:
    items = load_items()
    detail = page_items(items)

    DETAIL_DIR.mkdir(parents=True, exist_ok=True)

    # 前回生成したページのうち、今回対象から外れたものを消す
    keep = {f"{i['id']}.html" for i in detail}
    for stale in DETAIL_DIR.glob("*.html"):
        if stale.name not in keep:
            stale.unlink()

    for item in detail:
        (DETAIL_DIR / f"{item['id']}.html").write_text(detail_html(item), encoding="utf-8")

    inject_archive(detail)

    (SITE_DIR / "sitemap.xml").write_text(build_sitemap(detail), encoding="utf-8")
    (SITE_DIR / "robots.txt").write_text(build_robots(), encoding="utf-8")
    (SITE_DIR / "404.html").write_text(not_found_html(), encoding="utf-8")

    print(f"個別ページ: {len(detail)}件（全{len(items)}件中、スコア{MIN_SCORE_FOR_PAGE}以上）")
    print(f"sitemap: {len(detail) + 2}URL")


if __name__ == "__main__":
    main()
