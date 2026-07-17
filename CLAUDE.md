# 日本珍質問センター

参議院・衆議院の質問主意書を収集し、題材に意外性のある質問を珍質問度スコア付きの
静的フィードとして配信する個人サービス。「日本不審者情報センター」のフォーマット
（散在する公式発表を標準化して配信）を国会の質問主意書に転用したもの。
姉妹サイト: 日本珍拾得物センター（~/dev/otoshimono-center）。

## 構成

- `scraper/` — 標準ライブラリのみのスクレイパー（依存ゼロ）
  - `client.py` — GET+リトライ。参議院はUTF-8、衆議院はcp932
  - `parse.py` — 一覧（参: 3行1組 / 衆: 1行1件）と本文抜粋のパース
  - `score.py` — 珍質問度。ブロック語（深刻な題材は必ず除外）が最重要
  - `run.py` — MIN_SESSION以降の回次を巡回。注目質問のみ本文・答弁抜粋を取得
- `site/` — 静的サイト（Vanilla JS）。`site/data/items.json` を読むだけ
- `.github/workflows/build-deploy.yml` — 毎日JST 07:00収集→コミット→GitHub Pagesデプロイ

## 公開先

- 主URL: https://chin-shitsumon-center.pages.dev/ （Cloudflare Pages、wrangler@3で手動デプロイ）
- 副URL: https://yuki0kita.github.io/chin-shitsumon-center/ （GitHub Pages、push時自動デプロイ）
- データはapp.jsのDATA_SOURCESでGitHub rawを最優先で読むため、日次データ更新に
  Cloudflare側の再デプロイは不要。site/のコード変更時のみ `npx -y wrangler@3 pages deploy site
  --project-name chin-shitsumon-center --branch main` を実行する

## 開発

- テスト: `.venv/bin/python -m pytest tests/`（fixturesは実レスポンスHTML）
- 収集: `.venv/bin/python -m scraper.run`（ローカルPythonは3.9なので `from __future__ import annotations` 必須）
- プレビュー: launch.json の `chin-shitsumon-center`（ポート8648）

## ドメイン知識

- 参議院一覧: `.../syuisyo/<回次>/syuisyo.htm`（ヘッダーIDは連番 t1..tN）
- 衆議院一覧: `.../kaiji<回次>_l.htm`（Shift_JIS。「質問受理」直後は本文リンクなし）
- 衆議院の質問/答弁本文: a<回次><番号>.htm / b<回次><番号>.htm
- 本文抜粋は40文字以上の行から定型文（宛名・提出文・件名繰り返し）を除いて抽出

## デザイン方針

- ポップ路線（丸ゴシック・紫グラデ・角丸カード・会話吹き出し）だが、**絵文字は使わない**
  （ユーザーの明示要望）。顔は「議」「政」の円形アバター、分類は色付きチップで表現する
- 各質問は「議員の吹き出し（件名から機械生成）→ 政府の吹き出し（答弁定型文のカジュアル意訳、
  scraper/reply.py で分類）」の2吹き出しで「何があったか」を一言で伝える

## 運用ルール（編集方針）

- ブロック語（score.py の `_BLOCK_TERMS`）は削らない。事故・被害・民族・薬物など
  深刻な題材を「珍質問」枠に載せる事故を防ぐ最後の砦
- 短いカタカナ語（2文字以下）は境界チェック必須（「アイヌ」に「イヌ」を誤検出した実績あり）
- 提出者・件名は公表情報をそのまま掲載し、評価・論評を加える文言は書かない
- about.html の「制度や提出者を揶揄する意図はない」という編集方針の記述は消さない
