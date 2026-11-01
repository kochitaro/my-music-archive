# ①向け PR #12 一次レビュー対応：必須項目

2026-11-01。判定 **A：①による再レビューが可能**。これは①の承認・マージ判断を代行するものではない。DP-05は引き続き未解決で、β公開可能とは判定しない。

## 調査結果

指摘の検証漏れを確認した。修正前コミット`0f970cc295c0e0f9f67a8343fb169a46c27593d4`のversion 3では、Listening／Collectionのtitle・artist、Liveのtitleの欠落・nullが通過した。Liveの空タイトル・空白タイトルも通過した。数値・boolean・配列・オブジェクトの指定は既存の型検証で拒否していた。

48種類（3領域×2項目×8値）の合成入力を、修正前HTMLでも復元・通常保存・起動で実行した。上記12種類が3入口すべてで誤受理される計36結果を確認。Liveの単数形artistは領域の必須項目ではなく、他の未知プロパティと同様に保持する。

### 確定した検証条件

| 形式・領域 | 必須項目 | 欠落・null・非文字列 | 空文字・空白のみ | 保持方法 |
| --- | --- | --- | --- | --- |
| 正式旧配列（Listening） | title・artist（加えて従来のid文字列） | 拒否 | 互換性のため許可 | 原文を保持しtrim・補完しない |
| version 3 Listening | title・artist | 拒否 | 互換性のため許可 | 同上 |
| version 3 Collection | title・artist | 拒否 | 互換性のため許可 | 同上 |
| version 3 Live | title | 拒否 | 拒否 | 非空タイトルもtrimせず保持 |
| version 3 Live | artistは必須でない | 検証対象外 | 検証対象外 | 存在すれば未知JSON値として保持 |

Liveの複数形artistsは従来どおり任意。欠落・空配列を許可し、出演者配列からタイトルを生成しない。出演者がいてもtitle欠落は拒否する。出演者の順序・重複を維持する。その他の任意項目を必須化していない。

## 互換性の根拠

Git履歴を直接確認し、うち2経路は旧コードをNode VMで抽出実行して自動テストにした。コード上の保存能力と実データの存在は区別している。実利用者データや全歴史バックアップを調査したものではなく、確認できないデータを「正常な旧データ」と認定していない。

- 初期旧配列 [`32946ca`](https://github.com/kochitaro/my-music-archive/commit/32946ca)：`add()`はid・title・artist・release・added・listened・genre・rating・memoを生成。artistはクレジット結合または「不明」。正式なJSON復元はid／title／artistの文字列型を要求するが非空検証はなく、空artistと空白titleを保存できる。起動時の旧filterでも、非空idと空白titleの記録は残る。実際の旧復元ハンドラを実行し、空artist・空白titleの保存文字列と今回の移行保持を検証した。旧配列にCollection／Live／手動登録UIはない（PR-A仕様の空作品IDの旧配列互換性は継続）。
- 初期version 3 [`a0e35db`](https://github.com/kochitaro/my-music-archive/commit/a0e35db)：Listening／Collectionの`addAlbum()`はAPI由来の`r.title`を非空検証せずそのまま保存。artistクレジットの結合はtrimしない。旧producerを合成APIオブジェクトで実行し、空title・空白artistが保存候補になることを確認した。実際のMusicBrainzに空titleが存在したと認定したものではない。過去の保存経路に非空保証がない以上、今回これらの文字列を新たに拒否しない。
- Collection手動登録導入 [`c5aab02`](https://github.com/kochitaro/my-music-archive/commit/c5aab02)、全アルバムタイトル編集 [`cdddc54`](https://github.com/kochitaro/my-music-archive/commit/cdddc54)、Listening手動登録 [`29d0e92`](https://github.com/kochitaro/my-music-archive/commit/29d0e92)：手動入力はtitle／artistをtrimし非空を要求。現行の登録／編集UIも同様。検索クレジット未取得時の空artistは未保存のpendingRecordであり、現行保存ハンドラが直接入力を要求する（`c262ab3`以降）。今回、このUIの入力条件を緩めていない。
- Liveは初期version 3 `a0e35db`から登録／編集とも`title.trim()`の非空を確認して保存。単数形artistは生成しない。複数出演者導入 [`e4e51a4`](https://github.com/kochitaro/my-music-archive/commit/e4e51a4)もtitleを置き換えず、artistsは任意の別情報。従ってLiveだけ空／空白titleを拒否する根拠がある。
- 既存`tests/ui_v0322.py`、`tests/integration_pr6_pr7.py`、`tests/data_preservation.py`は、3領域の通常保存、手動登録の必須入力、旧Liveと任意項目欠落、保存例外時の保全を検証している。今回も変更せず再実行した。

空artistが正式旧配列からversion 3へ移行された後、version 3側で出自を識別する情報はない。そのためアルバムの空文字は旧配列だけに限定せずversion 3でも保持する。空文字を「値が欠落している」状態へ変換しない。

### 互換性への影響

欠落／nullの必須項目を含むデータは、これまでPR-Aが受理していても今後は全体拒否または起動時保存停止となる。自動修復・補完・行除外はしない。元rawは保持・回収可能。Liveの空titleも同様。過去の緩い復元や不正API入力で保存されたデータが該当する可能性はあるが、正常な正式生成データと認定する根拠はない。

一方、PR-A初版の旧配列titleにあった`trim()`非空制約は旧復元の文字列条件より強いため除去した。旧配列の空／空白titleは文字列のまま保持し、後続のversion 3検証とも整合させた。既存IDやスコア、任意項目の挙動は変更していない。

## 修正内容・ファイル

- `index.html`：`migrate()`内の`record()`のみ変更。領域別の必須文字列検証とLiveの空白title拒否を追加。旧配列のid検証は維持し、title検証を共通条件へ統合。本体差分は5行追加・1行削除。
- `tests/pr_a_required.test.cjs`：新規66件。version 3の領域別48ケース、旧配列16ケース、履歴実行2件。検証中の入力不変も確認。
- `tests/pr_a_browser.py`：追加144シナリオ。各入力について復元・通常保存・起動、拒否時のraw／メモリ／書込件数不変、原本ダウンロードを確認。修正前HTMLを指定して観測するテストモードも追加。
- `tests/pr_a.test.cjs`およびブラウザの既存合成fixture：正常ケースのtitle／artistを明示。以前「任意項目欠落」のfixtureに必須項目まで欠落させていた不備を訂正した。拒否系fixtureも対象外の必須値を埋め、元のID・スコア・日付異常まで到達するようにした。必須項目欠落そのものは追加マトリクスで検証しており、問題を合格扱いに隠していない。
- `docs/pr-a-report.md`：本対応への参照追加。本報告と`docs/pr-a-evidence/review-*.txt`を追加。

保存境界・復元ハンドラ・起動停止・原本回収・ID操作・UI・DB version・PR-B領域は変更していない。

## テスト結果

| 試験区分 | 成功 | 失敗 | 未実施 |
| --- | --- | --- | --- |
| 追加必須項目単体・履歴実行 | 66件 | 0 | なし |
| 追加必須項目ブラウザ（復元／通常保存／起動） | 144シナリオ | 0 | なし |
| PR-A既存単体 | 19件 | 0 | なし |
| PR-A既存ブラウザ | 57シナリオ | 0 | なし |
| DP-01・02・06保存保護 `data_preservation.py` | 14シナリオ | 0 | なし |
| 日英保存統合 `integration_pr6_pr7.py` | 8群 | 0 | なし |
| 主要UI・JSON往復 `ui_v0322.py` | 6群 | 0 | なし |
| `git diff --check` | 成功 | 0 | なし |

単位が異なるため総数は合算しない。旧配列／version 3の復元、手動登録、旧新Live混在、任意項目欠落、同一作品複数記録、特殊キー保持、正常登録・編集・削除、保存例外・描画例外、JSON書出し・復元・再読込を含む。既存保存保護・主要UIテストは無変更。

実装前の同じ66件では49成功・17失敗。内訳はversion 3の12件の誤受理、旧配列の欠落／null artist誤受理2件、旧配列空／空白titleの過剰拒否2件、その履歴互換性テスト1件。修正後66件すべて合格。ブラウザの修正前48入力観測でも12入力×3入口の誤受理を独立確認した。再現結果と修正後合格を区別して記録した。

初回履歴単体実行はsandboxの子プロセス制約でGit実行2件がEPERMとなったため、既存ブラウザと同じ許可済み実行環境で再実行してから実装前証跡を確定した。最終結果に環境エラーは含まない。ユーザーの状況確認で一度ツール呼出しが中断されたが、プロセス未開始を確認して検証を再開し、完了・終了コードを確認した。

[実装前の単体証跡](pr-a-evidence/review-unit-before.txt)、[修正前3入口の観測](pr-a-evidence/review-browser-before.txt)、[最終回帰結果](pr-a-evidence/review-results.txt)。

実機Safari・実容量不足・実利用者バックアップ・DP-05複数タブ競合は未検証。検索専用テスト・ブランド寸法等の全テスト群は今回再実行していない（初回PR-Aで実行済み）。必須項目以外の機能拡張はない。

## PR情報・未解決事項

既存PR [#12](https://github.com/kochitaro/my-music-archive/pull/12)、既存ブランチ`codex/pr-a-data-preservation`へ追加コミットをpushする。修正コミットは提出メッセージとPRのCommitsを参照。開始時のmainとリモートPR先端はそれぞれ`4f08f9d`・`0f970cc`で、無関係な変更はなかった。

mainとの差分は初回PR-A（DP-03・04・07と証跡）＋今回の必須検証・追加テスト・報告のみ。新規PR・main直接変更・マージ・デプロイ・実データ操作・DB version変更は行わない。

今回の検証漏れに未解決のテスト失敗はない。空文字の互換例外と影響範囲は上表のとおりで、①が再レビューできる状態。①の現在の判定BをCodexが承認へ置き換えるものではない。DP-05の競合、実データ全件および実機Safariの確認範囲外は引き続き残る。
