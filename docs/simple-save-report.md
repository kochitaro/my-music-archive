# 保存失敗UIの再整理・未保存入力JSON回収の撤去

基準main: `f4d41ef1ad3493060dc6e9a76bd6e872592721d6`（PR #16統合後）。専用ブランチ: `codex/simple-save-failure`。main直接変更・マージ・デプロイなし。

## 事前影響調査と移行方針

実装前に `captureDraft` / `showDraft` / `pendingDraft` / `preserveDraft` / `draftRecovered` / `saveDB` / `commitDB` / `canReplaceForm` / `beforeunload` と呼び出し元を調査した。

`captureDraft`は入力値・実File参照・処理済み写真と選択の対応・フォームセッションを保持する。`pendingDraft`は別操作・フォーム閉鎖・置き換えを拒否する基準であり、回収画面を表示する必要はない。`saveDB`は完全な同一フォームの保存成功と一致する復元の成功に限ってdraftを解消する。`commitDB`は保存済みDBの検証・排他・競合検出・書き込みを担当する。これらと表示状態を分離できることを確認した。

| 経路 | 既存の依存・リスク | 今回の代替操作・維持した保護 |
| --- | --- | --- |
| 3領域の新規/編集失敗 | draftが閉鎖・フォーム置き換えを拒否 | フォーム保持、文章コピー、確認付き再読み込み。同一フォームの再保存成功による解消を維持 |
| 写真処理失敗 | 変換前File・他の入力を保持する必要 | 入力と実Fileを保持。原写真保管・再選択を案内。未知の例外内容を原因として表示しない |
| 写真削除後の未保存入力 | 写真削除のみ保存済みで他の入力は未保存になり得る | 部分保存の既存説明を短く維持。draftと写真対応判定を保持し、完全保存または明示破棄まで閉鎖拒否 |
| 非同期処理中の入力変更 | 保存済み候補と現在のフォームが一致しない可能性 | 現在のフォームのdraftを保持し、内容が異なる説明を表示。書き込み済みデータを巻き戻さない |
| 保存中のフォーム切替 | 候補・対象・Fileの混在 | 既存のoperationBusy・トークン・セッション照合を維持。やり直す/破棄確定もoperationBusyとsavingで拒否 |
| JSONバックアップ復元失敗 | 選択した元バックアップが真の原本。未保存入力JSONにはアーカイブ全体を複製していない | 元ファイル保管、最新記録確認、正常バックアップで再試行を案内。通常の入力保持文言は使わない。同じ復元候補の成功でdraft解消、無関係な置換は拒否 |
| 記録削除失敗 | 削除候補を確定せず、編集フォームとdraftを保持 | コピー/確認付き再読み込み。未保存入力を捨てる別操作・再削除は既存どおり拒否。保存済み記録を変更しない |
| 旧形式移行失敗 | 元文字列を確保し、新形式DBへの不正な上書きを防ぐ | 既存の保存停止・原本回収を維持。未保存入力JSONは使用しない |
| 保存済みDBの読み込み不能 | 空の初期DBを正規データとして書く危険 | 保存停止、操作無効化、取得できた原文だけを変更せず回収。取得不能は回収不可と表示 |
| 別タブ競合・ロック失敗 | 古いDB候補の上書き・二重保存 | Web Locks、保存済みraw照合、storage通知、再試行拒否を維持 |

未保存入力JSONを残さなければ成立しない保護経路はなかったため、そのUIは全経路から撤去した。内部draftの構造・写真参照は維持し、外部出力は行わない。`draftRecovered`をtrueにする利用者向け操作は廃止し、通知閉鎖・破棄キャンセルによって保護解除しない。バックアップ/原本回収は別の既存経路で維持する。

## 撤去したUIと維持した機能

撤去: 入力内容を回収、未保存入力の回収ボタン、未保存入力JSONダウンロード、JSON全文欄、回収確認による閉鎖許可、専用回収パネルと関連ハンドラ。古い「未保存JSON出力が必要」という案内も更新した。

維持: 内部draft、実File/処理済み写真の対応、セッション・トークン保護、未保存入力の閉鎖/置き換え拒否、beforeunload、同一フォーム保存成功時の解消、復元候補一致による解消。DB version 3・保存キー・候補DB検証・書き込み後確定・Web Locks・raw競合検出・保存停止・不正JSON/未対応形式/重複ID拒否・JSONバックアップ/正常な復元・読み込み不能原文回収。

通知と確認は一つの表示状態で排他的に切り替える。やり直すで通知を隠して確認を表示し、キャンセルで通知へ戻る。別タブ更新の背景通知もdraftがある間は重ねない。入力に戻るは表示だけを閉じ、フォーム・draft・DB・競合状態・保護を保持する。

破棄確定は再読み込みだけを行う。localStorageの書き込み・削除・初期化はしない。beforeunloadの例外は明示確定した1回に限る。確認前の隠れた確定ボタンや保存処理中の確定はハンドラでも拒否する。

## 通知全文

### 通常フォーム・別タブ競合（日本語）

> 保存できませんでした
>
> 別のタブで記録が更新されています。
>
> 入力内容はこの画面に残っています。必要な文章はコピーしてから、再読み込みして入力し直してください。

操作: **入力に戻る** / **やり直す**

### Regular form / tab conflict (English)

> Couldn’t Save Changes
>
> The records were updated in another tab.
>
> Your input is still on this screen. Copy any text you want to keep, then reload the page and enter your changes again.

Actions: **Return to Editing** / **Start Again**

通常の本文は、draftのセッション・領域・実際に開いているフォームが一致し、復元操作でない場合に限って表示する。既知の保存拒否・入力検証は既存の説明、未知原因は理由を空欄とする。写真選択がある場合は「写真は元ファイルを保管し、やり直す際に選び直してください。 / Keep the original photo files and select them again when you start over.」を追加する。

### 破棄確認

> 未保存の入力を破棄しますか？
>
> 保存できなかった変更は失われます。必要な文章は、先にコピーしてください。

操作: **キャンセル** / **破棄して再読み込み**

> Discard unsaved changes?
>
> Your unsaved changes will be lost. Copy any text you want to keep before continuing.

Actions: **Cancel** / **Discard and Reload**

### バックアップ復元失敗時の本文（フォーム保持を主張しない）

> 選択したバックアップの元ファイルを保管してください。再読み込みして最新の記録を確認してから、正常なバックアップで復元をやり直してください。

> Keep the original backup file you selected. Reload to check the latest records, then retry restoring a valid backup.

フォームがない場合の戻るボタンは **閉じる / Close**。

### 読み込み不能時の原本回収案内

> 読み込みできなかった保存データの回収です。通常のJSONバックアップではありません。内容を変更せず書き出します。原本を保管してください。このファイルをそのまま正常に復元できるとは限りません。復元には正常なMLAバックアップを使用してください。

> Recover the saved data that could not be loaded. This is not a normal JSON backup. The original text is exported unchanged. Keep this original; it may not be restorable as-is. Use a valid MLA backup to restore records.

## 変更ファイル

| ファイル | 変更内容 |
| --- | --- |
| `index.html` | 回収UI/参照撤去、通知/確認の排他表示、フォーム実在判定、既知原因表示、原本回収・バックアップ案内更新 |
| `tests/compact_recovery.py` | PR #16の12通りの検証を新しい2操作へ移行。旧UI不存在・全文・コピー・DB不変・モバイル・証跡を検証 |
| `tests/save_failure_safety.py` | 既知/未知原因の切り替え、写真処理中の破棄拒否、復元失敗の別案内、原本回収の検証 |
| `tests/draft_visibility.py` | PR #16との内部draft比較6通り、通知閉鎖/キャンセルで保護維持、完全保存による解消 |
| `tests/pr_b_browser.py` | 既存70シナリオを維持し、JSON回収UI依存を内部draft・File・文章選択・置換拒否の検証へ変更 |
| `tests/pr_b_draft_review.py` | 既存36境界試験を維持。回収確認を破棄キャンセルに置き換えて再編集時の保護を検証 |
| `tests/pr_b_draft.test.cjs` | 通知フォーカス用のDOMスタブを追加。保存可否の検証は維持 |
| `tests/data_preservation.py` | 回収確認による閉鎖から、キャンセル/明示破棄/再読み込みへ変更。DB保持・後続保存を検証 |
| `tests/backup_guide.py` / `tests/fixtures/backup-guide-copy.json` | PR #14のバックアップ/復元説明の原文保持を検証。失敗案内を新仕様のコピーへ更新 |
| `tests/browser_smoke.py` | 必須入力の旧alert前提を新通知へ変更。拒否・手動修正・保存を維持 |
| `docs/simple-save-report.md` / `docs/simple-save-evidence/` | 調査、日英全文、証跡、試験ログ |

## 自動検証

合成データと隔離されたChromiumプロファイルを使用。以下のログを [証跡フォルダ](simple-save-evidence/) に収録する。

| 試験 | 結果・確認範囲 |
| --- | --- |
| Node `tests/*.test.cjs` | 126件成功。データ検証・保存保護・検索 |
| `compact_recovery.py` | 日英 × 3領域 × 新規/編集の12通り。実別タブ更新、通知全文、旧JSON UI不存在、入力/draft保持、文章選択、再保存拒否、閉鎖/unload保護、確認キャンセル/確定、再読み込み後DB raw完全一致 |
| `save_failure_safety.py` | 日英の3領域で既知検証後の未知障害・実File保持・非同期処理中のやり直す/破棄拒否。復元失敗ではフォーム保持を主張しない。正常バックアップ出力、同じ復元候補の成功、破損/未対応DBの原文回収と保存停止 |
| `draft_visibility.py` | 6通りの内部draftをPR #16の出力と比較（reason説明文だけ除外）。閉鎖拒否、キャンセル保持、再編集、完全保存成功時の解消 |
| `pr_b_browser.py` | 保存/競合/ロック/写真/復元拒否/移行競合の既存70シナリオ成功 |
| `pr_b_draft_review.py` | 同一フォーム再保存、写真削除部分保存、選択差し替え、別操作拒否、二重操作、非同期入力変更等の36境界試験成功 |
| `pr_a_browser.py` | 必須項目144ケース、不正データ32ケース、互換性・移行・原文回収・復元/描画境界・ID保護等57シナリオ成功 |
| `data_preservation.py` | 削除/編集/写真失敗、元プロパティ有無、読取例外/破損原本、後続保存/再読み込みが成功 |
| `backup_guide.py` | 日英全文、バックアップ/復元説明の原文保持、24モバイル配置、キーボード開閉、3領域の入力保持/再保存が成功 |
| `ui_v0322.py` / `ui_v0322_followup.py` | 通常の登録/編集/削除、日英、評価、フィルタ、正確なJSONバックアップ/復元/再読み込みが成功 |
| `browser_smoke.py` | 既存検索・保存・入力修正・障害再試行の回帰成功（外部応答はfixtures） |

320/375/390/430pxで通常通知とフォームの横はみ出しを検証。390px証跡: [日本語通知](simple-save-evidence/notice-listening-ja-390.png)、[English notice](simple-save-evidence/notice-listening-en-390.png)、[日本語破棄確認](simple-save-evidence/discard-listening-ja-390.png)、[English confirmation](simple-save-evidence/discard-listening-en-390.png)。Collection/Liveも同名パターンで収録。[復元失敗](simple-save-evidence/restore-failure-ja-390.png)、[読み込み不能原本回収](simple-save-evidence/unreadable-ja-390.png)も日英で収録。

従来の回収UIテストは削除せず、内部draftの同等性・文章選択・閉鎖拒否・明示破棄・成功時解消へ移行した。回収確認による閉鎖許可は仕様から撤去したため、通常通知の閉鎖やキャンセルで同等の許可が発生しないことを検証する。

## 未対応・未検証事項

Safari実機およびDP-08実容量不足試験は未実施。画面幅はChromiumで検証した。容量不足・写真処理・ロック例外等は合成障害で検証し、SafariのOS破棄後まで入力が残るとは保証しない。OSの実クリップボード操作は自動化せず、テキスト選択可能性と入力不変を検証した。

未保存入力JSON出力は全経路から撤去し、代替として入力/写真参照を保持する。利用者が明示的に破棄した後は入力や処理済み写真を回復できない。元写真は別途保持する必要がある。読み込み不能原本の内容修復・復元可能性の自動判定は今回追加せず、原本保持と正常バックアップ使用を区別して案内する。

新規外部ライブラリ、DB形式変更、回収JSON読み込み、その他対象外機能の追加なし。実装保留の経路なし。レビュー承認前のマージ・デプロイは行わない。
