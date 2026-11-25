# MLA 静的公開成果物（第1段階）

この変更は公開ファイルの準備だけを行う。Cloudflare連携、DNS、ドメイン、
デプロイ、GitHub Pages設定、解析有効化を行うワークフローは含まない。
アプリ本体、IndexedDB保存形式、写真処理、JSON仕様は変更しない。

## ビルド

Node.js 22以上（検証環境は24）を用意し、リポジトリルートで実行する。
パッケージのインストールやネットワークアクセスは不要。

```sh
node scripts/build-static.cjs
```

- Cloudflare Pages framework preset: None
- Build command: `node scripts/build-static.cjs`
- Build output directory: `dist`
- Root directory: リポジトリルート
- Production branch、プレビュー、ドメイン等の設定は別段階で承認後に行う。

`dist`は毎回削除して作り直す。正常なビルドの出力は同じ入力から同じファイル名・
内容となり、元ファイルをバイト単位でコピーする。時刻・コミット情報等は挿入しない。
検証失敗時は終了コード1で停止し、古い成果物を残さない。
`dist`や入力ファイルがシンボリックリンクの場合は停止する。
`dist`は生成物なのでコミットしない。

## 公開対象

| ファイル | 用途 |
| --- | --- |
| `index.html` | 本体HTML、インラインCSS・JavaScript |
| `insights.css` / `insights.js` | 統計表示 |
| `archive-toolbar.css` / `archive-toolbar.js` | アーカイブ操作バー |
| `search.js` | MusicBrainz検索 |
| `mobile-navigation.js` | ページ移動・再読込み |
| `archive-store.js` | IndexedDB保存 |
| `photo-store.js` / `photo-lifecycle.js` | 写真・旧保存元との互換処理 |
| `recovery-export.js` | 回収用書き出し |
| `404.html` | 日英の静的404ページ |
| `.nojekyll` | ビルド時に生成する空ファイル。GitHub Pagesで静的配信する際の補助 |

PR #52の以下4ファイルは**一式が存在するときだけ**追加する。

```text
terms.html
privacy.html
legal.css
legal.js
```

現行mainでは13ファイル、4ファイル導入後は17ファイル。
4ファイルがすべて不在なら正常終了し、法的文書の代用品は生成しない。
一部だけ存在する場合はビルド失敗とする。PR #52を自動取得・マージしたり、
文書や本体を書き換えたりしない。PR #52に含まれる本体フッターも別途必要であり、
4ファイルをコピーするだけでフッターが追加されるわけではない。

許可リスト以外は公開しない。`docs/`、テスト、スクリーンショット、
JSON/CSVバックアップ、README、ビルドスクリプト、`.git`、`.env`、`CNAME`、
`_redirects`等を探索してコピーする処理はない。
新しいランタイムファイルが必要になったら許可リストと本書をレビューで更新する。
HTMLの引用符付きsrc/hrefとCSSのurl()について、ローカル参照先が許可リスト内か検査する。
これはJavaScriptが実行時に組み立てるURLまで解析するものではないため、
アプリ変更時はブラウザ検証も必要。

## Cloudflare Pages / GitHub Pagesの共通利用

両ホストへ同じ`dist`の内容を配信できる。新たな先頭スラッシュ付きパス、
固定ドメイン、`base`要素、環境別のURL置換、転送処理は加えない。
GitHub Pagesの想定配置は`/my-music-archive/`。
将来のGitHub Actionsでは`dist`をPages用アーティファクトとしてアップロードする。
この段階ではActionsや公開設定を追加しない。
独自ドメイン用`CNAME`を避難版へ持ち込まない。

Cloudflareは`terms.html`を`terms`へ転送する場合がある。
文書内の`legal.css`・`legal.js`・`./`はその場合も同じ配置のファイルへ解決される。
GitHub Pagesでは`.html`付きリンクで利用する。

404は外部依存もJavaScriptも持たず、保存領域へアクセスしない。
自動転送やトップへの固定リンクも置かない。任意の深さの存在しないパスから、
相対URLだけで配信ベースを一意に判断できないため、URL確認とブックマーク利用を案内する。
ルート直下に`404.html`を含めることでCloudflareの既定SPAフォールバックを避ける。
GitHub Pagesもこのカスタム404を利用する。

ローカルのルート配信確認例（公開・デプロイではない）:

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory dist
```

この標準サーバーはCloudflareのクリーンURLやカスタム404応答を再現しない。
それらとサブパスの検証には以下のテストサーバーを使う。

## 検証

```sh
python tests/static_build.py
node --test tests/*.test.cjs
python tests/static_distribution.py
```

ブラウザテストはPython Playwrightと`/usr/bin/chromium`が必要。
localhostの一時ポート・隔離コンテキストと合成データだけを使い、外部HTTPS通信を遮断する。
ソース版とdist版のルート／サブパス、日英、390px／1280pxを比較する。
3領域のUI作成・写真取込み・編集・削除、IndexedDB保持、実ファイルJSON書き出し・
復元・再読込み、写真表示、日英法的文書と戻るリンク、深いパスの404を確認する。
Cloudflare式の拡張子なしURLもローカル模擬で確認する。
法的文書・404往復前後の保存領域を比較する。

PR #52適用後は、本体を含む同PRの差分を別の**ローカル検証用コピー**に適用し、
そのコピーにも本変更を置いてビルドする。続いて同じブラウザテストを実行する。
例（リポジトリへマージする操作ではない）:

```sh
python tests/static_distribution.py --source /path/to/local-combined-copy
```

単体テストは履歴参照に`git show`を使うものがあるため、必要な履歴を取得したcheckoutで実行する。
ブラウザテストは公開ホストのTLS・DNS・HTTPヘッダー設定、外部API実通信、
iPhone実機やホーム画面起動を保証しない。これらは構築・公開前の別段階に残る。
