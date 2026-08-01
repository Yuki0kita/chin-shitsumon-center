# 日本珍質問センター

国会に提出された質問主意書のうち、題材に意外性のある質問を
全国共通形式で配信する個人運営サイト。

- 公開URL: https://chin-shitsumon-center.pages.dev/ （Cloudflare Pages）
- 出典: 参議院・衆議院ウェブサイトの質問主意書情報
- 収集: GitHub Actions（毎日JST 07:00、`python -m scraper.run`）
- 配信: Cloudflare Pages（静的シェル）+ GitHub raw（日次更新データ）。
  GitHub Pages（yuki0kita.github.io/chin-shitsumon-center）にも同内容を自動デプロイ

サイトのコード（`site/`）を変更したら、Cloudflare Pagesへ再デプロイする:

```sh
npx -y wrangler@3 pages deploy site --project-name chin-shitsumon-center --branch main
```

データ（items.json）は日次のGitHub Actionsがコミットし、サイトは
raw.githubusercontent.com から直接読むため、データ更新に再デプロイは不要。

## セットアップ

```sh
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/
.venv/bin/python -m scraper.run
```

## X自動投稿

```sh
.venv/bin/python -m poster.post --chance 1.0   # 予行演習（投稿しない）
.venv/bin/python -m poster.post --post         # 実投稿（認証情報が必要）
```

有効化には、Xアカウントとdeveloperアプリを作ったうえで、GitHubのRepository secretsに
`X_API_KEY` `X_API_SECRET` `X_ACCESS_TOKEN` `X_ACCESS_SECRET` を登録する
（アプリの権限は Read and write）。未登録のあいだ、ワークフローは予行演習だけを実行する。

## 編集方針

- 掲載内容はすべて両院が公表している実在の質問主意書で、全文は公式ページへリンクする
- 選定は件名の機械的なキーワード基準のみ。特定の議員・政党への評価は行わない
- 深刻な題材（事故・被害等）は選定対象から除外する

当サイトは国会・各議院および政府とは関係ありません。
