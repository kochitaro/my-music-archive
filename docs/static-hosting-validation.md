# 静的公開準備 第1段階 検証報告

検証日: 2026-11-25

## 対象

- main: `7b697c32970c2ee9ac2393c3e7fcccebc8878bed`
- PR #52: `0f396dd115cc0bbd2105a30647ad8dcc86d5cd3e`（Draft・未マージ）
- Node v24.22.3 / Python 3.12 / Python Playwright / Linux Chromium
- 本変更: ビルドスクリプト、404、gitignore、手順書、検証コード・記録の追加のみ

mainのランタイム全ファイルをGit blob SHAで確認し、アプリ本体を変更していない。
別のローカル検証用コピーにPR #52の`index.html`と法的文書4ファイルを重ね、
その5ファイルもPR headのGit blob SHAと一致することを確認した。
PR #52のブランチ・文書・Draft状態は変更していない。

## 結果

| 検証 | main構成 | PR #52適用構成 |
| --- | --- | --- |
| 通常ビルド | 成功・13ファイル | 成功・17ファイル |
| コピー元とdist内の全配信ファイル | バイト一致 | バイト一致 |
| 連続ビルドのファイル名・SHA-256 | 一致 | 一致 |
| 既存Node回帰テスト | 166成功・0失敗 | 166成功・0失敗 |
| ブラウザによるソース版／dist版比較 | 12ケース成功 | 12ケース成功 |
| 日英法的文書 | 未導入・生成なし | 13条／11条、言語切替・戻る導線成功 |
| JavaScript無効の法的文書 | 対象外 | 両文書の日英全文を表示 |

ブラウザの12ケースは以下の直積:

- 配信方式3通り: ソースそのまま / distそのまま / distでCloudflare式クリーンURLを模擬
- パス2通り: `/` / `/my-music-archive/`
- 言語・画面幅2通り: 日本語390px / 英語1280px

各ケースで実施:

1. 正常な空の保存領域へ写真付きの合成JSONをUIから復元する。
2. 再読込み後、実ファイルのJSONダウンロードが合成原本と一致する。
3. Listening / Collection / Liveで、写真付き作成、メモ編集、削除を実際のUIから行う。
4. 取り込んだ写真がJPEGとなり、既存写真も表示される。
5. 作成記録の削除後、残った全記録が合成原本と一致する。
6. ソース版／dist版の各領域のアーカイブ表示DOMが一致する。
7. PR #52適用時は、本体フッターから文書へ移動し、日英切替、戻るリンク、横はみ出しを確認。
8. 文書往復前後でIndexedDB全DB・全ストアとlocalStorageが一致する。
9. 実際にダウンロードしたJSONを再取込みし、再読込み後も内容・写真が一致する。
10. 深い存在しないURLが404ステータスと日英404本文を返し、保存領域を変えない。
11. 期待した404以外のローカルHTTPエラーとJavaScript例外がない。

写真は全3領域に埋め込まれた合成データ。実利用者のデータは使用していない。
外部HTTPS通信は遮断した。新しいテストはアプリへテスト用APIを追加しない。

ビルド境界の独立テスト5件も成功:

- 固定許可リスト、再現性、古いdistファイルの除去、余計な入力ファイルの排除
- 法的文書の全有／全無、部分導入の拒否、導入後に削除した場合の古い成果物排除
- 必須ファイル欠落時の失敗と古いdist除去
- 許可外依存・ルート絶対パスの拒否
- 入力／出力symlinkの拒否とリンク先保護

開発資料・スクリーンショット・テスト・バックアップ・CNAME等は成果物に含まれない。
ビルド時の公開対象一覧は手順書の通り。

## 再実行

```sh
node scripts/build-static.cjs
python tests/static_build.py
node --test tests/*.test.cjs
python tests/static_distribution.py
```

既存Nodeテストの一部は歴史的ソースを`git show`で確認するため履歴が必要。
PR #52との組合せは、実際のPRをマージせずローカルコピーで行った。
手順の詳細は[静的公開手順](static-hosting.md)を参照。

検証ログは[mainブラウザ](static-hosting-evidence/browser-main.txt)、
[PR #52ブラウザ](static-hosting-evidence/browser-legal.txt)、
[main Node](static-hosting-evidence/node-main.txt)、
[PR #52 Node](static-hosting-evidence/node-legal.txt)、
[ビルド境界](static-hosting-evidence/build-tests.txt)。
mainのブラウザログの「legal」は共通処理ラベルであり、文書不在時はその分岐を実行しない。

## 未検証・残作業

- 実際のCloudflare Pages / GitHub Pages配信は未実施。クリーンURLと404はローカル模擬。
- WebKit実行バイナリは環境に存在せず、今回のブラウザ確認はChromiumのみ。
- iPhone Safari実機、ホーム画面起動、TLS・DNS・HTTPヘッダー、外部API実通信は次段階。
- 今回は既存Node全166件と新しいブラウザ検証を実施し、過去のPython UI全スクリプトは再実行していない。
- PR #52のホスティング／解析／法的記載の最終確認は別作業。文書内容は変更していない。
- ビルドは公開制御を行わない。将来Pagesを連携する際はProductionの自動デプロイ停止等を別途設定する。

Cloudflare連携、DNS・ドメイン変更、デプロイ、一般公開、GitHub Pages設定変更、
解析有効化、mainへのマージは行っていない。
