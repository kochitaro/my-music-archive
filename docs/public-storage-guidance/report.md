# 一般公開向けデータ保存・バックアップ案内の改訂

2026-11-27 UTC。基準main: `7e8ae500aca3738cdf7ec5cc634e895c0e5e2378`（開始時のGitHub APIとgit ls-remoteで一致）。

## 変更と範囲

`index.html` の静的な `#backup-guide` 内、日英各6段落を更新。承認済みの穏やかな説明方針に沿って、β前提の段落を保存保護機能の説明へ置換し、JSONバックアップ推奨、複数タブ時の対応、容量回収の制約、正式URL・同じブラウザからの継続利用を案内する。既存の説明と統合し、段落・見出し・折りたたみ等のHTML構成を増やしていない。

本体の変更は文面だけ。全script要素・style要素・HTMLタグ構造、案内外の内容は基準と一致。保存・写真・JSON・復元前回収・検索・通信・世代競合案内、規約・プライバシーポリシー・ビルドallowlistは変更なし。

## 維持した注意事項

- ブラウザ内保存、運営者のバックアップ・クラウド同期なし。
- サイトデータ消去・端末故障等で記録を失う可能性。
- 容量不足時は新規保存や変更ができなくなる可能性。
- 定期JSONバックアップ、Files等の実ファイル存在確認、別端末等への保管推奨。
- JSON復元はListening・Collection・Liveすべての置換で、追加・結合ではない。
- 端末・ブラウザ等の間で自動共有されないこと。オリジン間非共有の規約も無変更。
- プライベートブラウズ継続利用への注意、アプリ内ブラウザ・ホーム画面では保存領域が分かれる場合がある説明。
- 未保存文章のコピー、写真原本保管・再選択、破棄確認、再読込後の保存済み記録確認。
- 復元前内部退避と外部JSONの差、内部退避の次回復元による更新条件。
- 安全な保存に必要なブラウザ機能が利用できない場合の保存制約を静的案内にも明記。Safari以外を一律禁止しない。
- 世代競合時は古い候補をそのまま再保存できるとは限らない既存案内・保護処理。

ホーム画面Webアプリへの新しい禁止・非推奨文言は追加していない。安全を絶対保証する表現は追加せず、技術的未検証事項の個別列挙を利用者向け本文から外した。

## 検証

隔離Linux、Chromium 156.0.8078.79、Python Playwright。localhost、新規コンテキスト・合成データのみ。外部HTTPSはブラウザテストで遮断。個人記録・公開サイトの保存領域にアクセスしない。

- 静的不変確認: script/style/タグ構造、案内外全文、バックアップ・復元の先頭2節が基準と一致。β表記なし。`git diff --check`成功。
- 文面レビュー: 日英の説明範囲一致、重要注意事項維持、過剰な保証・不安を煽る技術列挙なし。
- 案内表示: source/dist × 日英 × 320/375/390/430px × 3領域 = 48条件。言語可視性・開閉状態維持、初期折りたたみ、Enter/Spaceの開閉、横はみ出しなし、summary 44px以上、pageerrorなし。390px日英画像を目視確認。
- `python tests/static_build.py`: 5件成功。
- `node scripts/build-static.cjs`: 17ファイル生成。
- `python tests/static_distribution.py`: source/dist（HTML URL・clean URL）× root/subpath × 日英の12条件成功。3領域CRUD・写真・IDB/JSON往復・規約遷移・404の既存配布検証。

初回の通常sandbox実行はChromium起動時のsocket権限で停止。ネットワーク権限を付与した隔離実行でブラウザを起動できた。製品のassert失敗とは区別する。

大容量、保存中断、API通信、合格済みiPhone操作は再実施していない。旧保存方式に依存する `tests/backup_guide.py` は今回の実行対象とせず、現行IDB起動に対応した案内限定の検証で確認した。アプリ・既存テストの期待値の緩和はない。

## 追加実機報告と残存リスク

運営者共有の2026-11-27 iPhone Safari報告を採用する。複数タブ・保存保護は9項目成功、全タブ終了後の記録・写真保持と再起動後の新規保存を含む。Save lock busyは未発生で、当該エラー後の実機復帰経路の追加合格とはしない。

復元前JSONは設定・記録編集・再読込後の内部退避、Files保存、回収JSONから記録・写真復元、復元後再読込まで全工程成功との報告。実機操作・目視確認であり、JSON内部の厳密比較は未実施。この変更に伴い再試験していない。

次は引き続き未検証または公開後改善候補。文面改訂によって解消・合格・受容承認済みとは扱わない。

- Save lock busyの実機発生原因・復帰経路の詳細。
- IndexedDBの実容量不足、端末の空き容量不足（例外注入合格とは別）。
- OS強制終了・電源断、ブラウザによる保存領域削除。
- 不要写真GC、多数の独立写真の実用上限。
- ホーム画面Webアプリの正式対応評価。

最終的なリスク受容とmainマージは別工程。今回の承認範囲は専用PR・検証・Preview反映まで。Production・DNS・Access・GitHub Pages設定は変更しない。

## 日英の変更前・変更後（変更対象2節の全文）

先頭のバックアップ・復元2節は全文無変更。以下に保存失敗・保存説明の2節を省略せず掲載する。

### 日本語・変更前

**「保存できませんでした」と表示されたら**

保存失敗と表示された場合は、保存できたと判断せず、画面の案内を確認してください。

入力フォームに内容が残っている場合は、「入力に戻る」で必要な文章を選択してコピーしてください。「やり直す」で確認し、「破棄して再読み込み」を選ぶと未保存の変更は失われます。

写真は元ファイルを保管し、入力し直す際に選び直してください。

再読み込み後は最新の保存済み記録を確認してから入力し直してください。Safariの終了やページの喪失後まで未保存入力が保持される保証はありません。

バックアップの復元に失敗した場合は、選択した元ファイルを保管してください。保存済みデータを読み込めない場合の原本回収ファイルは、通常のバックアップではなく、そのまま正常に復元できるとは限りません。原本を保持し、復元には正常なMLAバックアップを使用してください。

**記録の保存について**

MLAはアカウント不要で、記録を利用中のブラウザ内に保存します。MLAによるクラウド同期や、運営者による記録のバックアップはありません。

端末やブラウザが違うと、同じ記録は自動的には表示されません。アプリ内ブラウザやホーム画面からの利用でも、保存領域が分かれる場合があります。

継続して使用するブラウザを決め、記録を移すときはJSONバックアップを使用してください。

ブラウザのサイトデータ消去や端末の故障などによって、記録を失う可能性があります。プライベートブラウズでの継続利用は避け、定期的にバックアップしてください。

保存容量には限りがあります。写真などのデータが蓄積すると、新しい記録や変更を保存できなくなる場合があります。

保存完了前の入力は、Safariの終了やOSによるページ破棄の後まで保持されることを保証していません。保存失敗時には、画面を閉じる前に必要な文章をコピーしてください。

小規模β版では、Safariで実際に保存容量が不足した場合や、OSによるページ破棄・強制終了など、一部の条件について検証が完了していません。

大切な音楽の記録を長く残すため、定期的なJSONバックアップをおすすめします。

### 日本語・変更後

**「保存できませんでした」と表示されたら**

保存失敗と表示された場合は、保存できたと判断せず、画面の案内を確認してください。複数のタブでMLAを開いている場合は、他のタブでの保存処理が終わってから再試行してください。

入力フォームに内容が残っている場合は、「入力に戻る」で必要な文章を選択してコピーしてください。「やり直す」で確認し、「破棄して再読み込み」を選ぶと未保存の変更は失われます。

問題が続く場合は、未保存の文章や写真の元ファイルを別途保管し、他のMLAのタブを閉じてから、画面の案内に従ってください。ブラウザのサイトデータは削除しないでください。写真は入力し直す際に選び直してください。

再読み込み後は最新の保存済み記録を確認してから入力し直してください。Safariの終了やページの喪失後まで未保存入力が保持される保証はありません。

バックアップの復元に失敗した場合は、選択した元ファイルを保管してください。保存済みデータを読み込めない場合の原本回収ファイルは、通常のバックアップではなく、そのまま正常に復元できるとは限りません。原本を保持し、復元には正常なMLAバックアップを使用してください。

**記録の保存について**

MLAはアカウント不要で、記録を利用中のブラウザ内に保存します。MLAによるクラウド同期や、運営者による記録のバックアップはありません。

端末やブラウザが違うと、同じ記録は自動的には表示されません。アプリ内ブラウザやホーム画面からの利用でも、保存領域が分かれる場合があります。

継続してご利用いただく際は、同じブラウザからMLAの正式URL（https://mylisteningarchive.com/）を開くことをおすすめします。端末やブラウザを変更する際は、JSONバックアップをご利用ください。安全な保存に必要なブラウザ機能が利用できない場合は、保存できません。

ブラウザのサイトデータ消去や端末の故障などによって、記録を失う可能性があります。プライベートブラウズでの継続利用は避け、定期的にバックアップしてください。

保存できるデータの容量は、お使いの端末やブラウザによって異なります。写真などのデータが蓄積すると、新しい記録や変更を保存できなくなる場合があります。また、復旧用データなどが保持されるため、記録や写真を削除しても使用容量がすぐに減るとは限りません。

保存完了前の入力は、Safariの終了やOSによるページ破棄の後まで保持されることを保証していません。保存失敗時には、画面を閉じる前に必要な文章をコピーしてください。

MLAでは、保存時のエラーや複数タブ間の競合に備えたデータ保護機能を設けています。

大切な記録を長く残していただくため、定期的なJSONバックアップをおすすめします。

### English・変更前

**If You See a Save Failure**

If a save failure is displayed, do not assume that your changes were saved. Check the on-screen guidance.

If your input is still in the form, use Return to Editing to select and copy any text you want to keep. Start Again opens a confirmation; Discard and Reload loses your unsaved changes.

Keep the original photo files and select them again when entering your changes.

After reloading, check the latest saved records before entering your changes again. Unsaved input is not guaranteed to survive Safari closing or the page being lost.

If restoring a backup fails, keep the original file you selected. A recovered original of unreadable saved data is not a regular backup and may not be restorable as-is. Keep the original and use a valid MLA backup to restore records.

**About Data Storage**

MLA does not require an account and stores records in the browser you are using. MLA does not provide cloud synchronization, and the operator does not back up your records.

The same records do not automatically appear on a different device or in a different browser. Storage may also be separate when using an in-app browser or opening the app from the Home Screen.

Choose a browser for ongoing use, and use JSON backups when moving your records.

You may lose records if browser site data is cleared, your device fails, or similar problems occur. Avoid ongoing use in private browsing mode, and back up regularly.

Storage capacity is limited. As data such as photos accumulates, you may become unable to save new records or changes.

Input whose save has not completed is not guaranteed to be retained after Safari closes or the OS discards the page. If saving fails, copy any text you want to keep before closing the screen.

In this small-scale beta, testing has not been completed for some conditions, including actual storage exhaustion in Safari and page discarding or forced termination by the OS.

We recommend regular JSON backups to preserve your important music records over time.

### English・変更後

**If You See a Save Failure**

If a save failure is displayed, do not assume that your changes were saved. Check the on-screen guidance. If MLA is open in multiple tabs, wait for any saving in other tabs to finish before trying again.

If your input is still in the form, use Return to Editing to select and copy any text you want to keep. Start Again opens a confirmation; Discard and Reload loses your unsaved changes.

If the problem persists, keep a separate copy of any unsaved text and original photos, close the other MLA tabs, and follow the on-screen guidance. Do not clear your browser’s site data. Select the photos again when entering your changes.

After reloading, check the latest saved records before entering your changes again. Unsaved input is not guaranteed to survive Safari closing or the page being lost.

If restoring a backup fails, keep the original file you selected. A recovered original of unreadable saved data is not a regular backup and may not be restorable as-is. Keep the original and use a valid MLA backup to restore records.

**About Data Storage**

MLA does not require an account and stores records in the browser you are using. MLA does not provide cloud synchronization, and the operator does not back up your records.

The same records do not automatically appear on a different device or in a different browser. Storage may also be separate when using an in-app browser or opening the app from the Home Screen.

For ongoing use, we recommend accessing MLA’s official URL (https://mylisteningarchive.com/) using the same browser. Use JSON backups when moving your records to another device or browser. Saving is unavailable if the browser features needed to save safely are not available.

You may lose records if browser site data is cleared, your device fails, or similar problems occur. Avoid ongoing use in private browsing mode, and back up regularly.

Available storage capacity varies depending on your device and browser. As data such as photos accumulates, you may become unable to save new records or changes. Because recovery data and other stored data may be retained, deleting records or photos may not immediately reduce storage usage.

Input whose save has not completed is not guaranteed to be retained after Safari closes or the OS discards the page. If saving fails, copy any text you want to keep before closing the screen.

MLA includes safeguards designed to protect your records against save errors and conflicts between multiple tabs.

To help preserve your listening memories over time, we recommend making regular JSON backups.

## 証跡

[evidence](evidence/) に案内48条件の結果、日英390px画像、静的不変確認・ビルド・配布ログを収録。開発資料は既存allowlistによりdistへ入らない。
