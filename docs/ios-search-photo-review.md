# iPhone検索フォーカス・Live写真選び直し フォローアップ

基準: 最新main `498992f9a0eb2db88e92d39a6330845d4ef6d61e`（PR #27マージ後）

## 修正内容

- `index.html`: Listening／Collection検索入力を16pxに固定。従来は継承した15pxで、iPhone Safariのフォーカス自動拡大が起こる条件だった。viewportによるズーム禁止は行わず、利用者のピンチズームは維持する。
- Liveの写真が未選択／未保存なら「写真を追加 / Add Photo」、選択済み・保存済みなら「写真を変更 / Replace Photo」。削除で未選択に戻ると「追加」に戻る。編集画面のフィールド見出しも中立的な「写真（任意・1枚）」に変更。
- 写真選択済みの場合、「保存前でも、このボタンから別の写真を選び直せます。」を日英表示。Liveを登録せず写真ライブラリへ再度アクセスできる導線を明示する。
- 従来は未接続の一時inputをclickしていた。Safari向けに一時ファイル入力をDOMへ接続してから、ユーザーのタップ処理内で同期的に起動。確定したFileListのみ既存フォームへ渡し、選択確定／キャンセル時に一時入力を破棄。次回起動時にも残った一時入力を除去する。元の選択ファイルを先に消さないので、キャンセルしても選択・その他の入力を保持する。
- `tests/ios_search_photo.py`: 日英×320/375/390/430/1280px、検索の実測文字サイズ、横はみ出し、追加／変更ラベル、登録前の再選択、キャンセル、キーボード起動、DB書込みゼロ、新規・編集の保存を検証。
- `tests/compact_live_ui.py`: 既存写真回帰試験の証跡出力先を環境変数で指定可能にした。

DB形式・保存処理・競合検出・回収処理の変更なし。保存前の写真選択／再選択によるレコードDB書込みは0。

## iOS標準画面との境界

添付された「1枚の写真を選択中」の画面はiOSの標準UIで、Webアプリから画面内の戻るボタン等は追加できない。右上の青い✓は写真選択を確定する操作であり、Live記録の保存ではない。

Web側の導線は **「写真を追加」→ iOSで選択確定 → MLAプレビュー →「写真を変更」→ 再び写真ライブラリ**。Liveの登録・変更保存を挟まずに選び直せる。iOS標準画面そのものに変更は加えていない。

## 自動検証

Chromium / Playwright、合成データ、外部通信遮断。ログは[証跡ディレクトリ](ios-search-photo-evidence/)に保存。

| 試験 | 結果 |
|---|---|
| Node既存試験（5ファイル） | 137件すべてPASS (`node.log`) |
| 今回追加の検索・写真選び直し試験 | 日英×5幅 PASS (`ios_search_photo.log`, `matrix.json`) |
| 既存写真操作・保存失敗・再保存の回帰 | 日英×5幅 PASS (`compact_live_ui.log`) |
| 保存失敗時保護・非同期操作・JSON復元失敗保護 | PASS (`save_failure_safety.log`) |
| 検索方式・整列・ページング・検索エラー・応答競合 | PASS (`browser_smoke.log`) |
| 差分空白チェック | `git diff --check` PASS |

検索文字サイズはListening／Collectionとも全幅16px。ユーザーズームを禁止するviewport設定なし。新規・編集の双方で保存前にpickerを複数回起動。キャンセル時は同じFileオブジェクトを保持し、再選択時は新しいFileへ置換。公演名・会場・メモの保持、変更後の登録・編集保存を確認した。

## 日英の変更前後・操作証跡（390px）

| 内容 | 日本語 | 英語 |
|---|---|---|
| 検索フォーカス・変更前 | [画面](ios-search-photo-evidence/before-search-ja.png) | [画面](ios-search-photo-evidence/before-search-en.png) |
| 検索フォーカス・変更後 | [画面](ios-search-photo-evidence/after-search-ja.png) | [画面](ios-search-photo-evidence/after-search-en.png) |
| 写真未選択・変更前 | [画面](ios-search-photo-evidence/before-add-photo-ja.png) | [画面](ios-search-photo-evidence/before-add-photo-en.png) |
| 写真未選択・「写真を追加」 | [画面](ios-search-photo-evidence/after-add-photo-ja.png) | [画面](ios-search-photo-evidence/after-add-photo-en.png) |
| 登録せず別写真へ再選択・案内表示 | [画面](ios-search-photo-evidence/after-reselected-ja.png) | [画面](ios-search-photo-evidence/after-reselected-en.png) |

## 未検証事項

**実機iPhone Safariのフォーカス時ズーム解消と、iOS標準写真ライブラリの実操作は未確認。** Chromiumで16pxの算出値とWeb側の選択操作・保持を確認しており、実機確認の代替ではない。VoiceOverも未実行。検索の本番API疎通は未実行（既存fixture試験を使用）。

新規レビュー用PRで提出し、今回の承認前にはマージしない。手動デプロイも行わない。
