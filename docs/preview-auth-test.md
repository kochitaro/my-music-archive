# MLA Preview 認証テスト専用ブランチ

`deploy/preview` はCloudflare Pages PreviewとCloudflare Accessの閲覧制限を
ユーザーが確認するための静的ページ専用ブランチ。
基点は `deploy/holding-page` の `3cfb40b0a4a52f652b0873b326fcc7cde88d8222`。
本ブランチでは本書を優先し、継承した `docs/holding-page.md` と
`docs/static-hosting.md` はそれぞれ待機版・本体配信に関する過去の説明として扱う。
mainへのマージは行わない。

## 既存Cloudflare設定との対応

| 項目 | 値 |
| --- | --- |
| Project | `my-listening-archive` |
| Repository | `kochitaro/my-music-archive` |
| Production branch | `deploy/holding-page`（変更なし） |
| Preview対象 | `deploy/preview` |
| Build command | `node scripts/build-static.cjs` |
| Build output directory | `dist` |
| Root directory | リポジトリルート |

今回のGitHubブランチ作成によるPreview自動デプロイは依頼で許可されている。
Cloudflare管理設定、Accessポリシー、DNS、正式ドメイン、GitHub Pages設定は変更しない。
main、deploy/holding-page、PR #52は変更・マージしない。
発行URLと実際のAccessの許可・拒否はユーザー側で確認する。
このページが表示できるだけでは認証が有効である証明にはならない。

## ビルドと公開内容

Node標準機能のみを使用し、依存パッケージのインストール不要。
`node scripts/build-static.cjs` は固定許可リストの2ファイルをコピーし、
空の `.nojekyll` を生成する。distは毎回作り直し、生成物をコミットしない。

```text
dist/
  index.html
  404.html
  .nojekyll
```

両HTMLは同一内容で「MLA Preview 認証テスト中」と明示する。
待機版とは見出し、PREVIEW表記、背景色で区別できる。
静的HTMLとインラインCSSのみ。JavaScript、外部リソース、外部API、解析、
フォーム、リンク、転送は実装しない。IndexedDB、Cookie、localStorage、
sessionStorage、アーカイブ、写真、利用者データにはアクセスしない。
CSPでも外部リソース・スクリプト実行を禁止する。
Cloudflare Access自体の認証処理・Cookie等はページ実装とは別のサービス側の動作。

MLA本体のソース・履歴は基点から継承するが、公開成果物には一切含めない。
リポジトリルートを公開せず、公開ディレクトリには必ずdistを指定する。
404.htmlを含めてCloudflare Pagesの既定SPAフォールバックを避ける。

## 検証結果（2026-11-25）

Node v24.22.3でビルド成功。以下の専用検証も成功。

```sh
node scripts/build-static.cjs
python tests/preview_distribution.py
```

Python PlaywrightとChromiumを用いたローカル検証で、以下を確認した。

- 出力ファイル集合がindex.html、404.html、.nojekyllだけであること。
- 再ビルドのハッシュ一致と、古い疑似個人データ成果物の削除。
- 本体JS、疑似バックアップ、.env、CNAME、_redirects、法的文書の混入なし。
- 入力欠落・入力シンボリックリンクで失敗し、distを残さないこと。
- distのシンボリックリンクを拒否し、リンク先を削除しないこと。
- 320/390/1280px、JavaScript有効/無効でindexと404を表示可能。
- 見出し表示、横はみ出しなし、追加リソース要求なし、ページエラーなし。
- JavaScript有効時に保存領域・Cookieへのアクセス監視を置き、アクセス0件。
- JavaScript無効時の390pxスクリーンショットを目視確認。

SHA-256（index.htmlと404.htmlは同一）:

```text
index.html / 404.html
b4f50c8239e30692719d7cfbce470aaebf74ee6c01ec5a8c366dc6549a40b7f1
.nojekyll (empty)
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

リモートの基点ツリーと一致する既存ファイルを別のローカル作業ディレクトリに
コピーして実装・検証した。リモートコミットはその基点ツリーを継承し、
HTML2件、ビルドスクリプトのコメント、専用テストの置換、本書だけを変更する。
旧 `tests/holding_distribution.py` はPreview用 `tests/preview_distribution.py` に置換する。
本体を配信しないため、本体用の回帰試験は今回の検証対象外。
404は直接アクセスで表示確認しており、Cloudflare上のHTTPステータスや
Accessの実動作、実機モバイルブラウザは今回未検証。
