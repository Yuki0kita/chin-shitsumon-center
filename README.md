# 日本珍質問センター

国会に提出された質問主意書のうち、題材に意外性のある質問を
全国共通形式で配信する個人運営サイト。

- 出典: 参議院・衆議院ウェブサイトの質問主意書情報
- 収集: GitHub Actions（毎日JST 07:00、`python -m scraper.run`）
- 配信: GitHub Pages（`site/` を静的配信）

## セットアップ

```sh
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests/
.venv/bin/python -m scraper.run
```

## 編集方針

- 掲載内容はすべて両院が公表している実在の質問主意書で、全文は公式ページへリンクする
- 選定は件名の機械的なキーワード基準のみ。特定の議員・政党への評価は行わない
- 深刻な題材（事故・被害等）は選定対象から除外する

当サイトは国会・各議院および政府とは関係ありません。
