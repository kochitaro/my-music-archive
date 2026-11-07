# MLA 検索方式ボタン 下線位置・C案 最終調整報告

作業日: 2026年11月7日

基準: 作業開始時の最新main `313c48af2c08438ca4d95537d1265300c597adf1`。PR #31のマージ済み状態をGitHubで確認。

専用ブランチ: `fix/search-mode-underline-placement`

## 実装・変更ファイル

- `index.html`: 選択中のborder-bottomを透明にし、CSSの文字下線（text-decoration）へ変更。色`#9fcfdc`・太さ1px、skip-inkを無効化して細い連続線を表示。文字サイズ13px・太さ400・文字色・背景・ボタン幅・高さ・padding・フォーカスはそのまま。
- CSSの文字下線を使うことで、疑似要素や固定幅の線を追加せず、表示文字の自然な幅へ追従させた。HTMLのspan追加やJavaScriptの変更も不要。
- 通常のunderline offsetは4px、日本語はフォントの描画差を補うため5px。これはCSSプロパティ値であり、実際の文字の描画端との空きとは異なる。後述のピクセル測定で、空きは日本語3px、英語4pxを確認。
- ボタン下端の透明1px borderは残し、既存のボックス寸法・文字位置を維持。非選択では下線なし。アニメーション追加なし。
- `tests/search_underline.py`: 日英×5幅×両画面×両選択状態の変更前後証跡、文字と線の描画ピクセル、線幅、文字幅、ボタン・文字の座標不変、44px、placeholder・aria・DB/APIゼロを測定。
- `tests/direct_search_modes.py`: 旧border-bottomの表示を期待していた検証を、新しいtext-decorationの太さ・offsetへ更新。他の操作検証は維持。
- `docs/search-underline-evidence/`と本文書: 画面・測定・回帰ログ・提出資料。

**実装変更は下線CSSのみ。JavaScript・検索処理・HTML構造は変更なし。** [静的確認結果](search-underline-evidence/scope.txt)には、全script要素、最初のstyle要素以降のドキュメント全体、search.js、insights.js/cssの基準mainとのバイト一致を記録。

## 測定方法と結果

Chromium、device scale factor=1で、ボタンをスクリーンショット化して描画ピクセルを解析。文字のアンチエイリアスは前景色と背景色の混色として識別し、下線色とは分離。文字の最下端と線の上端の間の空白ピクセル数、線の左右端・太さ、文字の左右端を計測した。

DOM RangeとgetBoundingClientRectで文字・ボタンのx/y/width/heightも記録し、変更前後および選択切り替えで差がないことを確認。CSSのoffset設定値だけを、実際の文字との距離として扱っていない。

| 対象 | 文字と線の実測の空き | 下線の太さ | 線幅と文字描画幅 | ボタン・文字の位置変化 |
|---|---|---|---|---|
| 日本語・両方式・全5幅・両画面 | 3px（改修前14px） | 1px | 差2px | 0 |
| 英語・両方式・全5幅・両画面 | 4px（改修前17px） | 1px | 差0〜2px | 0 |

操作領域は既存の各幅44px以上、高さ44pxを維持。線は文字幅に追従し、操作領域全体の幅には伸ばしていない。

[全40条件の変更前後測定・操作領域](search-underline-evidence/measurements.json)

調整時の試作では共通offset 4pxで日本語の空きが2px・英語が4pxとなった。日本語だけoffsetを補正し、最終試験で全幅・両画面を測定した。実機Safariのフォントで同じピクセル値になると実証したものではない。

## 必須検証

| 指示書項目 | 結果・ログ |
|---|---|
| 1–3 距離・文字に近い線幅・非選択なし | PASS: `search_underline.log`, `measurements.json` |
| 4 13px・400・指定色 | PASS。選択文字`#c6e7ef`、非選択`#a1adbc`、背景透明を算出スタイルで確認 |
| 5 位置・幅が動かない | PASS。同じ言語・幅・画面・方式の改修前後と、選択切り替えでボタン・文字の座標／寸法を比較 |
| 6 日英・指定5幅 | PASS。320/375/390/430/1280px、Listening／Collectionの両方 |
| 7–8 44px・フォーカス | PASS。2pxフォーカス、キーボード操作、画面外配置・重なりなし |
| 9–14 方式・aria・入力保持・placeholder・API/DBゼロ | PASS: `search_underline.log`, `direct_search_modes.log` |
| 15 検索回帰 | PASS: `browser_smoke.log`, `search_live_ui.log`, `node.log`。両方式・同名候補・完全一致/別名等・整列・追加読み込み・再試行・古い応答排除・結果保持 |
| 16 手動追加・Insights・Live・保存保護 | PASS: `ui_v0322.log`, `insights_browser.log`, `save_failure_safety.log`, `compact_live_ui.log` |
| Node既存試験 | 137件すべてPASS |
| 差分空白チェック | `git diff --check` PASS |

ブラウザ試験は追加測定1本と操作・検索・保存・Insights・Liveの回帰7本、計8本がすべてPASS。今回の自動試験に失敗・タイムアウトはなかった。

[実行結果一覧](search-underline-evidence/results.json)

検索・保存保護の回帰ではJSONバックアップ・復元、CSV、登録編集削除、Live写真の変更削除と保存失敗時の保持・再保存も確認。UI操作のDB計測は、同じ値のsetItemも書込みと数えて0を確認。

DB version 3・保存キー・構造・artists配列・写真形式・Web Locks・競合検出・元データ回収・Insights集計の変更なし。

## 変更前後・選択状態・フォーカス証跡

| 条件 | アーティスト選択 前→後 | アルバム名選択 前→後 |
|---|---|---|
| 日本語390px | [前](search-underline-evidence/before-listening-artist-ja-390.png) → [後](search-underline-evidence/after-listening-artist-ja-390.png) | [前](search-underline-evidence/before-listening-title-ja-390.png) → [後](search-underline-evidence/after-listening-title-ja-390.png) |
| 日本語320px | [前](search-underline-evidence/before-listening-artist-ja-320.png) → [後](search-underline-evidence/after-listening-artist-ja-320.png) | [前](search-underline-evidence/before-listening-title-ja-320.png) → [後](search-underline-evidence/after-listening-title-ja-320.png) |
| 英語320px | [前](search-underline-evidence/before-listening-artist-en-320.png) → [後](search-underline-evidence/after-listening-artist-en-320.png) | [前](search-underline-evidence/before-listening-title-en-320.png) → [後](search-underline-evidence/after-listening-title-en-320.png) |

フォーカス: [日本語320px](search-underline-evidence/focus-ja-320.png) / [英語320px](search-underline-evidence/focus-en-320.png)

証跡ディレクトリには日英・全5幅・Listening／Collection・両選択状態の前後と、日英各幅のフォーカス画像を収録。合成レコードを使用し、変更前は基準mainのHTMLを配信して取得。

## 未検証・制約

- **実機iPhone Safari・iOSキーボード・VoiceOverは未検証。** ピクセル値・フォーカス・配置の成功はChromiumでの結果。Safariのフォントと下線描画の実測は別途実機確認が必要。
- MusicBrainz本番API疎通は未実行。fixture／Node回帰で検索品質を確認。
- 実端末の容量枯渇は未実行。保存例外注入で保護を確認。
- 過去の旧UI専用スクリプトは全件実行していない。実行対象は結果一覧に記載。

新規レビュー用PRで提出。今回の承認前にマージしない。手動デプロイは実施しない。
