# SKY SOCIAL LAB

lab.sky-social.com

AIが記事を起案し、人間が承認して公開する媒体。

## 構成

```
index.html        トップ（記録の一覧）
about.html        運営方針・AI開示
style.css         共通スタイル
articles/         記事本体
ledger/           台帳
  articles.json     記事
  rinji.json        稟議
  nippou.json       日報
```

## 台帳について

`ledger/` が記録の正本。記事の公開、稟議の起票と承認、日報はすべてここに残る。
Git の履歴に残るため、後から書き換えても改変の記録が消えない。

## 公開の流れ

1. AIが記事を起案し `articles/` に置く
2. 同時に `ledger/rinji.json` へ稟議を起票（status: pending）
3. 人間が確認し承認（status: approved、承認者と時刻を記入）
4. `index.html` に一覧を追加し、リポジトリへ反映
5. Cloudflare Pages が自動で公開

## 決めていること

- 広告を掲載しない
- 外れた判断も削除しない
- AIが起案した旨と稟議番号を全記事に明記
- 誤りは黙って書き換えず、訂正を明記して修正
- 機密情報（APIキー等）はこのリポジトリに置かない

