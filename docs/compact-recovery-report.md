# 保存失敗通知・未保存入力回収UI改善

基準: `90d051d38e259a43cda85fe0c264c65e389b67d5`（PR #15統合後）。ブランチ: `codex/compact-save-recovery`。mainの直接変更・マージ・デプロイは実施しない。

## 変更理由・影響範囲

保存失敗の初期表示を短い通知へ変更した。「入力に戻る」は表示だけを閉じ、フォーム・draft・写真参照・回収確認状態を保持する。「入力内容を回収」または既存の回収ボタンで回収画面を開く。JSON全文はnative detailsで初期折りたたみとし、ダウンロード失敗時は全文を展開・選択して手動コピーへ案内する。PR #14の長文案内は既存の折りたたみのまま、日英とも原文を維持した。

判定できない例外の通知は「保存できませんでした」のみを原因表示とする。従来の汎用説明にあった「変更は反映されていません」という断定を回収データのreasonからも除いた。既知の保存拒否・検証エラーは既存説明、競合は指定の短文を使う。

破棄経路の実装前に、`canReplaceForm`、`pendingDraft`、`draftRecovered`、フォームセッション、クリック捕捉、`beforeunload`、既存の再読み込み経路を調査した。draftはメモリ内に保持され、閉鎖保護は回収パネルの表示とは別である。新しい確認画面は初期フォーカスをキャンセルに置き、明示的な「破棄して再読み込み」でのみ1回のbeforeunloadを許可する。再読み込みがメモリ内入力を破棄し、最新の保存データを読み込む。破棄処理からDB・localStorageに書き込みや削除はしない。処理中は破棄を拒否する。通常の通知閉鎖・回収画面閉鎖・破棄キャンセルは保護を解除しない。

## 日英通知全文（別タブ競合）

### 日本語

> 保存できませんでした
>
> 別のタブで記録が更新されています。
>
> 入力内容はこの画面に残っています。必要な内容をコピーするか、回収用ファイルに保存してください。

操作: **入力に戻る** / **入力内容を回収**

### English

> Couldn’t Save Changes
>
> The records were updated in another tab.
>
> Your input is still on this screen. Copy anything you want to keep, or save it to a recovery file.

Actions: **Return to Editing** / **Recover Input**

### 破棄確認

> 未保存の入力を破棄しますか？
>
> この画面で保存できなかった変更は失われます。必要な文章や写真がある場合は、先にコピーまたは回収してください。

操作: **キャンセル** / **破棄して再読み込み**

> Discard unsaved input?
>
> Changes that could not be saved on this screen will be lost. Copy or recover any text or photos you need first.

Actions: **Cancel** / **Discard and Reload**

## 変更ファイル

| ファイル | 内容 |
| --- | --- |
| `index.html` | 通知・回収表示状態、JSON折りたたみ、出力失敗時の選択、確認付き再読み込み |
| `tests/compact_recovery.py` | 新規UI・別タブ競合・破棄・日英・モバイル・証跡の自動検証 |
| `tests/draft_visibility.py` | 明示的回収への遷移に対応、旧版回収データ比較、未知原因の簡潔表示検証 |
| `tests/backup_guide.py` | PR #14案内の原文比較を維持し、新しい回収遷移に対応 |
| `tests/pr_b_browser.py` | 回収の明示的選択を追加し、既存保存保護検証を維持 |
| `tests/pr_a_browser.py` / `tests/data_preservation.py` | 保存失敗のalert断定文検証を、新しい通知・未知原因の非表示検証へ更新 |
| `tests/pr_b_draft_review.py` | 既存36境界試験で保存失敗後に回収を選択 |
| `docs/compact-recovery-report.md` | 本レポート |
| `docs/compact-recovery-evidence/` | 自動試験ログ、390px画面証跡18枚 |

## 回収・データ保全への影響

DB version 3、保存キー、Web Locks、raw文字列比較とstorageイベントの競合検出、候補DBの検証と書き込み順序は変更しない。回収JSONの構造・formatVersion・写真の対応判定・ダウンロード方式も変更しない。理由文の安全な文言修正以外、固定日時・固定IDで旧版の回収データと一致することをListening／Collection／Liveの新規・編集6通りで検証する。

回収未確認時のフォーム閉鎖拒否・beforeunload、回収確認後の従来の閉鎖許可、確認後に編集した場合の再保護、同一フォームの再保存成功時のdraft解消を維持する。回収確認は従来どおりdraftそのものを即時削除しない。写真回収の制約と元写真の保管案内も維持する。

## 検証結果

最終ログは [証跡フォルダ](compact-recovery-evidence/) に収録。

- `node --test tests/*.test.cjs`: 126件成功。
- `python tests/compact_recovery.py`: 日英 × 3領域 × 新規/編集の12通り。実際の別タブ更新、通知、入力/draft保持、競合再試行拒否、回収、JSONダウンロード/全文選択/出力失敗時の代替経路、閉鎖・beforeunload保護、破棄キャンセル、確定後のDB文字列完全一致を検証。320/375/390/430pxで通知・ダイアログの横はみ出しなし。
- `python tests/draft_visibility.py`: 6通りの旧版データ比較（reason文言修正のみ除外）、回収確認、閉鎖保護、再保存成功時の解消。
- `python tests/backup_guide.py`: PR #14日英全文の一致、キーボード開閉、24通りのモバイル配置、3領域の保存失敗時案内・フォーム/回収内容/DB保持。
- `python tests/pr_b_draft_review.py`: 写真・セッション・回収状態・非同期処理の境界36件成功。
- `python tests/pr_b_browser.py`: 実Web Locks、同時保存、API不在、ロック取得失敗・解放、raw不一致、回収、写真、復元拒否、移行競合を含む70シナリオ成功。
- `python tests/ui_v0322.py` / `python tests/ui_v0322_followup.py`: 保存・編集・削除・日英・評価・フィルタ・正確なJSONバックアップ/復元/再読み込み等が成功。
- `python tests/browser_smoke.py`: 検索・入力保持・データ保存・390px幅・障害再試行の既存試験成功。外部応答はfixturesで検証。
- `python tests/pr_a_browser.py`: 必須項目144ケース、不正データ32ケース、互換性・移行・保存/描画境界・ID保護を含む57シナリオ成功。
- `python tests/data_preservation.py`: 3領域の削除/編集/写真/保存失敗、元プロパティの有無、読み込み不能データの原文回収、後続保存/再読み込みが成功。

## 画面証跡（390px）

| 領域 | 日本語 | English |
| --- | --- | --- |
| Listening | [通知](compact-recovery-evidence/notice-listening-ja-390.png) / [回収](compact-recovery-evidence/recovery-listening-ja-390.png) / [破棄確認](compact-recovery-evidence/discard-listening-ja-390.png) | [Notice](compact-recovery-evidence/notice-listening-en-390.png) / [Recovery](compact-recovery-evidence/recovery-listening-en-390.png) / [Discard](compact-recovery-evidence/discard-listening-en-390.png) |
| Collection | [通知](compact-recovery-evidence/notice-collection-ja-390.png) / [回収](compact-recovery-evidence/recovery-collection-ja-390.png) / [破棄確認](compact-recovery-evidence/discard-collection-ja-390.png) | [Notice](compact-recovery-evidence/notice-collection-en-390.png) / [Recovery](compact-recovery-evidence/recovery-collection-en-390.png) / [Discard](compact-recovery-evidence/discard-collection-en-390.png) |
| Live | [通知](compact-recovery-evidence/notice-live-ja-390.png) / [回収](compact-recovery-evidence/recovery-live-ja-390.png) / [破棄確認](compact-recovery-evidence/discard-live-ja-390.png) | [Notice](compact-recovery-evidence/notice-live-en-390.png) / [Recovery](compact-recovery-evidence/recovery-live-en-390.png) / [Discard](compact-recovery-evidence/discard-live-en-390.png) |

## 未対応・未検証

追加のSafari実機試験、DP-08実容量不足試験は実施しない。容量不足・ロックAPI例外・写真処理失敗は合成障害で検証する。画面幅検証・証跡はChromiumによるものでSafari実機の保証ではない。クリップボードAPIは追加せず、OSの選択・コピー操作を使う。ダウンロード済みファイルの利用者による確認は従来どおり必要。メモリ内draftのため、確認付き破棄やページ喪失後の自動回復機能はない。依頼の対象外機能・外部ライブラリは追加しない。
