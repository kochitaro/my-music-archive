# Production待機ブランチ

`deploy/holding-page` はCloudflare PagesのProduction branchとして選択するための
待機ページ専用ブランチ。main `f864e1fb390335652fd3d1af33830145291e89ba` を基点とする。
mainへのマージ用ではない。PR #52（`feat/legal-pages`）は取り込まない。
このブランチでは本書が `docs/static-hosting.md` の本体配信用手順より優先する。

## Cloudflare Pagesで後日設定する値

| 項目 | 値 |
| --- | --- |
| Production branch | `deploy/holding-page` |
| Framework preset | None |
| Root directory | リポジトリルート |
| Build command | `node scripts/build-static.cjs` |
| Build output directory | `dist` |

設定・連携・デプロイは今回実施しない。DNS・ドメイン・既存GitHub Pages設定も変更しない。
GitHub ActionsやCloudflare設定ファイルは追加しない。

## 出力と情報の分離

ビルドはNode標準機能だけで動作する。パッケージインストール不要。
既存のビルドコマンド、出力先、明示的な許可リスト、古いdistの削除、
シンボリックリンク拒否、入力検証失敗時の出力削除を維持する。
ブランチ専用の許可リストは `index.html` と `404.html` のみ。
環境変数による本体への切替や、法的文書の自動追加はない。
空の `.nojekyll` を加え、成果物は計3ファイル。
`dist` は既存の `.gitignore` に従ってコミットしない。

両HTMLは同一の「公開準備中」ページで、静的HTMLとインラインCSSのみ。
404.htmlを含め、Cloudflare Pagesの既定SPAフォールバックを避ける。
JavaScript、外部画像・フォント・API、解析、リンク、フォーム、自動転送はない。
CSPはスクリプト・接続等を禁止し、表示用インラインCSSのみ許可する。
Cookie、localStorage、sessionStorage、IndexedDBにアクセスするコードはない。
アーカイブの記録、写真、個人情報を読み込まない。

本体JS等はブランチのGit履歴・ソースツリーに残るが、distには入らない。
公開ディレクトリにリポジトリルートを指定しないこと。
今回の差分は `index.html`、`404.html`、ビルドスクリプト、本書、
専用テストのみ。その他の既存ファイルは基点のまま保持する。

## 検証結果（2026-11-25）

Node v24.22.3で `node scripts/build-static.cjs` 成功。
`python tests/holding_distribution.py` 成功（Python PlaywrightとChromiumが必要）。

- distのファイル集合が上記3ファイルと完全一致。
- 再ビルドのハッシュ一致、古い疑似個人データ成果物の削除。
- 本体JS、疑似バックアップ、.env、CNAME、_redirects、法的文書があっても出力に混入しない。
- 入力欠落・入力シンボリックリンクで失敗しdistを残さない。
- distシンボリックリンクは拒否し、リンク先を削除しない。
- ローカルChromium、320/390/1280px、JavaScript有効/無効で両ページを確認。
- 「公開準備中」が表示され、横はみ出し・追加リソース要求・ページエラーなし。
- JavaScript有効時に保存領域とCookieへのアクセスを検知する監視を入れ、アクセス0件。

SHA-256:

```text
index.html / 404.html
91a620cdeb103a0b66ccb0c3b7aa5234ba5b205ae180a6d71ba6972e79967f7e
.nojekyll (empty)
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

作業環境からGitHubへの直接cloneが接続できないため、GitHub接続ツールで
基点ツリー・必要ソースを取得し、変更ファイルをローカルで検証した。
リモートコミットは基点ツリーを継承し、上記5ファイルだけを変更する。
本体を配信しないブランチのため、本体用の回帰試験は対象外。
Cloudflare実配信でのHTTPステータス・ヘッダー・クリーンURL・DNS/TLSは未検証。
ローカル検証では404.htmlを直接開いて表示を確認している。
