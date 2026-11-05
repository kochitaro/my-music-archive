# β公開向けバックアップ・復元・保存案内 実装報告

①開発・検証ルーム #2 レビュー向け。2026-11-05 UTC。

## 基準・範囲

- GitHub APIで最新mainを確認し、git fetchでも照合。`82f3f11ddb5a06c6496f79f30f1359cb87b5ef51` と一致、指定基準との差分なし。
- 専用ブランチ: `codex/beta-backup-storage-guide`。mainへのコミット、マージ、デプロイなし。
- アプリ変更は `index.html` の案内HTMLと案内に限定したCSS。既存全script要素が基準と完全一致することを自動検証。
- DB version 3、保存キー、全データ形式、JSON復元/CSV、Web Locks、raw比較、保存失敗保護、回収/確認/フォーム閉鎖保護、写真、外部API処理は変更なし。実利用者データにアクセスしていない。

## UI

Backup & Restore内に標準のdetails/summaryを追加。通常は全4項目を一括開閉し、初期は閉じた状態。既存のExport JSON/CSV、Import JSONはそのまま使用可能。
回収画面の先頭にも、第3項全文を開くdetailsを設置。既存showDraftに従ってフォーム内へ移動するため、その場で閲覧できる。
ネイティブの開閉状態・キーボード操作を使用。16px、行間1.75、番号付き手順、折り返しを設定。追加ライブラリ・保存キー・イベント処理なし。
既存言語切り替えで更新されるhtml lang属性にCSSが追従し、非表示言語はdisplay:none。開閉状態を言語切り替えでも保持。

## 原稿照合

日本語確定全文を、見出し・段落・番号付き手順単位で fixture とDOMを照合し、4項目すべて一致。第3項の回収画面側も一致。句読点・表記・注意事項を省略していない。③の修正文言として指示書に収録された確定稿を採用。別途の未提示原稿は使用していない。
英語版も同じ構造で全文照合。保存保証やDB状態の断定を避け、通常バックアップと回収JSONの相違、写真の制約、未検証条件を明記。

## 自動検証

隔離したChromiumプロファイル、合成データ、ループバックHTTPを使用。外部HTTPS要求は遮断。

- `node --test tests/*.test.cjs`: 126件成功、失敗0。
- `python -u tests/backup_guide.py`: 全文照合、初期/反復/Enter/Space開閉、言語切り替え、開閉保持、320/375/390/430px × 日英 × 3領域（24レイアウト）、44px以上のsummary、DB書き込みなし。
- 同試験で3領域の保存失敗を注入し、回収画面から閲覧、日英開閉前後の入力/回収テキスト/JSONダウンロードのバイト一致、保存済みDB不変、確認前の閉鎖防止と確認後の閉鎖を検証。
- `python -u tests/pr_b_draft_review.py`: 36件成功、失敗0、未実施0。
- `python -u tests/pr_b_browser.py`: 70シナリオ成功。
- `python -u tests/ui_v0322.py`: 6グループ成功。通常登録/編集/削除、JSON Export/Import、CSV Export、再読み込みを含む。
- `python -u tests/data_preservation.py`: 保存失敗時の削除/編集/写真/読込失敗の保全回帰確認。
- `git diff --check`: 成功。

初回の権限なし実行では、既存単体試験のgit子プロセス2件がEPERM、ブラウザ試験のHTTPソケット作成がPermissionErrorとなった。環境に必要な実行権限を付けて再実行し解消。製品のテスト失敗ではない。

## 表示証跡・未実施事項

[証跡フォルダ](backup-guide-evidence/) に実行ログ、390×844相当の日本語/英語スクリーンショットを格納。通常案内は要素全体、回収案内は各領域の先頭/末尾ビューポートを撮影（長文はスクロールで閲覧）。実iPhone Safariの撮影ではない。
Safari実機・VoiceOver実機、実容量不足、OSページ破棄/強制終了、OS保存先の実ファイル確認は未実施。自動試験の保存失敗は例外注入であり、実容量不足の検証を意味しない。ネイティブdetailsの読み上げはブラウザ支援機能に依存する。

main・正式環境・実利用者データは未変更。①の明示承認前のマージ/正式環境デプロイは行わない。

## 掲載英語全文

### Back Up Your Important Records

MLA records are stored in the browser you are using. Export JSON backups regularly and save them somewhere such as the Files app on your iPhone.

We also recommend making a backup after adding important records and before changing devices or browsers.

Backups include your Listening, Collection, and Live records, along with photo data stored within the app. However, they do not contain the original photo files themselves. They also do not contain the actual album artwork images displayed from external sources.

After exporting, check that the file exists at the save destination. To prepare for problems such as device failure, we also recommend keeping a copy on another device or in cloud storage.

### Restore from a Backup

To restore your records, use a regular JSON backup exported from MLA.

Restoring from JSON replaces all current Listening, Collection, and Live records with the records in the file. It does not add to or merge with your current records.

1. Before restoring, save your current records as a JSON backup.
2. Select the JSON backup file you want to restore.
3. Read the confirmation about replacing your records, then proceed with the restore.
4. After restoring, check your Listening, Collection, and Live records and saved photos.

If restoring fails, keep the original backup file and check the guidance displayed on screen.

CSV is for viewing and analyzing records. Use JSON for a complete backup and restore.

### If You See a Save Failure

Do not close or reload the page until you have recovered your input.

If a save failure is displayed, do not assume that your input has been saved. Follow the on-screen recovery guidance to keep a copy.

If guidance for recovering unsaved input appears after a save failure, follow these steps to keep a copy of your input.

1. Download and save the recovery JSON file.
2. Check that the file exists at the save destination, then open it and check that it contains your input.
3. If you cannot download it, copy the recovery text displayed on screen and save it in a note or file.
4. Once you have checked that you have recovered your input, use the app's recovery confirmation control.

The recovery JSON file is for retrieving input that could not be saved. Its format differs from a regular JSON backup, and it cannot be used to restore a backup.

Original photo files are not included in the recovery JSON. Processed photo data may also be unavailable for recovery, so keep the original photos separately.

If an update in another tab caused the failure, reload the page after recovering your input and check the latest records.

If insufficient storage or a similar issue caused the failure, also secure a JSON backup of your saved records before addressing the issue.

If Safari closes or the page is lost before recovery, you may be unable to retrieve your unsaved input.

### About Data Storage

MLA does not require an account and stores records in the browser you are using. MLA does not provide cloud synchronization, and the operator does not back up your records.

The same records do not automatically appear on a different device or in a different browser. Storage may also be separate when using an in-app browser or opening the app from the Home Screen.

Choose a browser for ongoing use, and use JSON backups when moving your records.

You may lose records if browser site data is cleared, your device fails, or similar problems occur. Avoid ongoing use in private browsing mode, and back up regularly.

Storage capacity is limited. As data such as photos accumulates, you may become unable to save new records or changes.

Input whose save has not completed is not guaranteed to be retained after Safari closes or the OS discards the page. If saving fails, recover your unsaved input before closing the screen.

In this small-scale beta, testing has not been completed for some conditions, including actual storage exhaustion in Safari and page discarding or forced termination by the OS.

We recommend regular JSON backups to preserve your important music records over time.

## 変更ファイル一覧

- `index.html`
- `tests/backup_guide.py`
- `tests/fixtures/backup-guide-copy.json`
- `docs/backup-guide-report.md`
- `docs/backup-guide-evidence/backup-en-390.png`
- `docs/backup-guide-evidence/backup-ja-390.png`
- `docs/backup-guide-evidence/existing-ui.log`
- `docs/backup-guide-evidence/guide-ui.log`
- `docs/backup-guide-evidence/pr-b.log`
- `docs/backup-guide-evidence/preservation.log`
- `docs/backup-guide-evidence/recovery-collection-en-390-end.png`
- `docs/backup-guide-evidence/recovery-collection-en-390.png`
- `docs/backup-guide-evidence/recovery-collection-ja-390-end.png`
- `docs/backup-guide-evidence/recovery-collection-ja-390.png`
- `docs/backup-guide-evidence/recovery-listening-en-390-end.png`
- `docs/backup-guide-evidence/recovery-listening-en-390.png`
- `docs/backup-guide-evidence/recovery-listening-ja-390-end.png`
- `docs/backup-guide-evidence/recovery-listening-ja-390.png`
- `docs/backup-guide-evidence/recovery-live-en-390-end.png`
- `docs/backup-guide-evidence/recovery-live-en-390.png`
- `docs/backup-guide-evidence/recovery-live-ja-390-end.png`
- `docs/backup-guide-evidence/recovery-live-ja-390.png`
- `docs/backup-guide-evidence/recovery-review.log`
- `docs/backup-guide-evidence/unit.log`
