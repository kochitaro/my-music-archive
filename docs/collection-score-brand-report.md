# ①向け作業報告：Collectionスコア統一・ブランド見出し拡大

作業日：2026-10-30。

## 基準と変更内容

- 開始時の最新main：`f264ee6ff928f96dfdbda5ef0f32b78b5962e8d0`。
- PR #10が上記SquashコミットでmergedであることをGitHubとfetchしたmainで確認。
- 新規独立ブランチ：`feat/mla-collection-score-brand-size`。旧ブランチは流用していない。

Collectionの登録・編集・詳細・一覧・並び替え・星操作説明・読み上げ名・入力検証メッセージを「スコア／Score」に統一。全領域で同じ表記となるため、共通ラベルとアルバム欄にあったCollection専用の分岐を削除。初期HTML、翻訳辞書とプレフィックスも更新した。未評価／Unratedは維持。

モバイル（540px以下）の `.brand h1` だけに `font-size:clamp(20px,calc(10vw - 12px),30px)` を適用。フォント・太さ・色・em単位の文字間隔・ロゴ・横並び・余白・他見出しは維持。デスクトップは既存サイズを維持。

指示書の「現行25px」は汎用h1の指定に存在するが、後段の `.brand h1` が上書きしていた。実測では390pxで16pxだった。現行の文字間隔とロゴを維持すると390pxで30pxは収まらない（自然文字幅約326px、利用可能幅308px）。そのため390pxでは27px、430pxでは目標30pxとした。

## 画面幅ごとの比較

隔離Chromium・日本語UI・同じベースコミットのHTMLと変更後HTMLで測定。単位px。

| 画面幅 | 変更前 | 変更後 | 変更後の文字幅 | 利用可能幅 | 結果 |
| --- | --- | --- | --- | --- | --- |
| 320 | 16 | 20 | 217.42 | 238 | はみ出し・切れ・重なりなし |
| 375 | 16 | 25.5 | 277.22 | 293 | 同上 |
| 390 | 16 | 27 | 293.52 | 308 | 同上 |
| 430 | 16.34 | 30 | 326.14 | 348 | 同上 |
| 768 | 26 | 26 | 282.66 | 668 | デスクトップ無変更 |

document全体のscrollWidth、文字Rangeの実境界、h1のscrollWidth/clientWidth、ロゴ境界を確認。font-family・font-weight・color・文字間隔のem比率・ロゴSVG／寸法・h2のcomputed font-sizeは変更前後で一致。画像でも320pxと390pxの前後を確認した。

| 幅 | 変更前 | 変更後 |
| --- | --- | --- |
| 320 | [画像](screenshots/collection-score-brand/brand-320-before.png) | [画像](screenshots/collection-score-brand/brand-320-after.png) |
| 375 | [画像](screenshots/collection-score-brand/brand-375-before.png) | [画像](screenshots/collection-score-brand/brand-375-after.png) |
| 390 | [画像](screenshots/collection-score-brand/brand-390-before.png) | [画像](screenshots/collection-score-brand/brand-390-after.png) |
| 430 | [画像](screenshots/collection-score-brand/brand-430-before.png) | [画像](screenshots/collection-score-brand/brand-430-after.png) |

[測定JSON](screenshots/collection-score-brand/measurements.json)。スクリーンショットは画面上部240pxを切り出した比較資料。

## 変更ファイル

- `index.html`：上記UIのみ。
- `tests/search_live_ui.py`、`tests/mla_update.py`：Collectionの旧文言期待値を新仕様へ更新。
- `tests/browser_smoke.py`：テストの待機短縮が通信タイムアウトまで15msにしてしまう問題を修正（アプリ無変更）。
- `tests/collection_score_brand.py`：新規検証。
- `docs/collection-score-brand-report.md`：本報告。
- `docs/screenshots/collection-score-brand/`：8枚の前後画像＋測定JSON。

## 自動テスト

合成データ、隔離Chromium。外部通信はモック／遮断。正式環境の実データは使用していない。

| 区分 | コマンド | 結果 |
| --- | --- | --- |
| 既存 | `node tests/search.test.cjs` | 34/34 PASS |
| 既存 | `python -u tests/ui_v0322.py` | 6検証群 PASS |
| 既存 | `python -u tests/ui_v0322_followup.py` | 5検証群 PASS |
| 既存・テスト用タイマー修正 | `python -u tests/browser_smoke.py` | 8検証群 PASS |
| 既存・期待値更新 | `python -u tests/search_live_ui.py` | 4検証群 PASS |
| 既存 | `python -u tests/data_preservation.py` | 14シナリオ＋エラー確認 PASS |
| 既存 | `python -u tests/integration_pr6_pr7.py` | 日英×4検証群 PASS |
| 既存 | `python -u tests/live_artists_colors.py` | 日英×2検証群 PASS |
| 既存・期待値更新 | `python -u tests/mla_update.py` | 9検証群 PASS |
| 新規 | `python -u tests/collection_score_brand.py` | レイアウト比較1群＋日英各1群 PASS |
| 静的 | `git diff --check` | PASS |

新規テスト：Collectionの日英・登録／編集／詳細／グリッド／リスト／両方向ソート・星操作説明／読み上げ・入力検証エラー、数値順／未評価末尾、4.2／4.3の既存色と部分塗り、タッチ／ドラッグ／キーボード0.1・未評価、登録後5.0／編集後0.0／未評価の保存再読込、元の全レコードの数値を含む一致、3領域のタブと言語切替。上記画面幅比較も自動化。

初回の検索スモークは並行実行中にHard Life検索のモック通信でNetwork error / timeout、JSエラーなし。単独でもNumber Girlで再現。調査で、テストが全ての長いsetTimeoutを15msに短縮し、実アプリの20秒のリクエスト中断タイマーまで短縮していることを確認。テスト側の短縮範囲を20秒未満の再試行・間隔待機に限定し、通信タイムアウトは元の20秒を維持して再実行。アプリの検索コードには変更なし。新規テスト作成中にもPlaywrightのルートハンドラがRequestをHTML引数として受け取るテスト実装ミスがあり、ハンドラのクロージャを修正して最終版成功。アプリ側の修正範囲は拡張していない。

## 保存形式・互換性

DB version 3、現行／旧localStorageキー、JSON／CSV形式、rating名・既存値、Live artists配列、記録IDを変更していない。起動・移行・読み込み失敗ガード・共通保存・編集保存・JSON/CSV/復元・日付処理・スコア換算と色・並べ替え処理はmainとのコード比較で一致。search.js・Search Labも無変更。DP-01・02・06を弱体化せず、DP-03・04・07などは範囲外。

mainへのマージ、正式環境・GitHub Pages・公開バージョン・既存レビューSiteの変更なし。新規レビューPR作成後に停止。

## 残存リスクとSafari最小確認

ChromiumとiPhone SafariではAvenir等の実フォントや文字幅が異なる可能性がある。実機Safari／VoiceOver／OS実容量不足は未検証。自動テストの成功をSafari合格とはしない。

1. 320／375／390／430px相当の端末でブランド名の拡大・文字切れ・ロゴとの重なり・横スクロールがないことを確認。太さ・文字間隔は現行のまま。
2. 日英・3領域の切替後もスコア／Score。Collectionの新規／編集／詳細／一覧／ソートとVoiceOverの星操作名を確認。
3. Collectionの星をタップ／ドラッグし保存・再読込。未評価へ戻せること、Listeningの星・Liveのハートと特別色が従来どおりであることを確認。
