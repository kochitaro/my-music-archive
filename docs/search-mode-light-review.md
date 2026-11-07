# MLA 検索方式プルダウン軽量化 実装・検証報告

作業日: 2026年11月7日

基準: 作業開始時最新main `78dd28ac2f9260a58429247ba19779624c119f7d`（PR #29統合後）

専用ブランチ: `fix/lightweight-search-mode-select`

## 変更ファイル

- `index.html`: 検索方式selectと必要な周辺配置を対象にCSSを7行追加。背景色・枠線・角丸を廃止し、手動追加と同じ水色系の文字色、13pxへ変更。幅はネイティブselectの内容に応じる自動幅、最小44px、高さ44px。右端に12pxの下向き矢印をSVG背景として表示し、文字と矢印の間を確保。キーボード時は2pxのフォーカス枠を表示。
- 同CSS: 上段左select／右手動追加、下段左検索入力／右検索ボタンの2行構成を全対象幅で適用。PR #29時点の1280pxのみ横1行だった配置も、今回の2行指定に統一。手動追加・検索ボタン自体の見た目・機能は変更なし。
- `tests/search_mode_light.py`: 日英・5幅・2検索対象、両選択肢の文字幅と矢印領域、操作領域、色・透明背景・枠線なし、配置、キーボード、フォーカス、言語切替、placeholder連動、手動追加、DB書込み・API通信0の検証と画面証跡。
- `docs/search-mode-light-evidence/`と本文書: 日英5幅の変更前後、フォーカス証跡、測定結果、回帰試験ログ。

**実装差分はCSSのみ。** JavaScriptの全script要素と、最初のstyle要素より後のドキュメント全体が基準mainとバイト単位で同一であることを確認した。[差分範囲の確認](search-mode-light-evidence/scope.txt)

## 操作・互換性

ネイティブselectと既存option・aria-labelをそのまま使用。独自選択メニューは追加していない。矢印の表示だけをCSSで揃えており、選択メニュー・キーボード操作はブラウザ標準に委ねる。

検索入力16px、プレースホルダー、大分類・中分類、検索ボタン、手動追加の処理、検索候補、問い合わせ、整列・ページング・再試行・結果保持、DB・保存保護・バックアップ復元、Insights、Liveのコード変更なし。

## 検証結果

Chromium + Playwrightの独立プロファイルで検証。検索試験はfixture応答を使用し、実ユーザーデータやMusicBrainz本番APIを使用していない。

| 必須項目 | 結果 |
|---|---|
| 1–4 控えめな外観、2行の左右配置、文字・矢印の欠け、重なり | PASS。文字色は手動追加と同一、13px、背景透明・border 0。各optionの描画文字幅が利用可能幅以内。矢印12pxと22pxの右余白を確保 |
| 5 操作領域 | PASS。高さ44px、横幅44px以上。実測は日本語100×44px、英語87×44px（全対象幅）。詳細は`matrix.json` |
| 6 キーボード・フォーカス | PASS。ArrowUpで方式変更、フォーカス枠2px、日英全幅の画像を保存 |
| 7 横スクロール・画面外配置 | PASS。320/375/390/430/1280pxの各コントロール境界とドキュメント幅を確認 |
| 8–12 両検索方式、placeholder、言語、整列・追加読み込み・再試行 | PASS。`browser_smoke.log`, `search_live_ui.log`, `search_mode_light.log` |
| 13 手動追加 | PASS。Listening／Collectionでダイアログを開けること、既存登録編集も`ui_v0322.log`で確認 |
| 14 DB非書込み | PASS。方式変更・言語変更・キーボード操作・手動追加の開閉で、レコードDBのsetItem呼出し0。方式変更の外部API通信も0 |
| 15 Insights・保存保護・Live | PASS。`insights_browser.log`, `save_failure_safety.log`, `compact_live_ui.log`, `ui_v0322.log` |
| Node既存試験 | 137件すべてPASS (`node.log`) |
| 差分空白チェック | `git diff --check` PASS |

ブラウザ試験は今回追加1本と既存回帰6本、計7本を実行。保存例外時の入力・写真保持、再保存、JSON復元、Live登録編集、Insightsの作成編集削除後更新を確認した。検索結果105件のアーカイブ／統計往復後の保持と追加通信なしも既存回帰で確認。

[実行結果一覧](search-mode-light-evidence/results.json) / [測定値](search-mode-light-evidence/matrix.json)

## 日英・幅別の表示証跡

各リンクはListening画面。証跡ディレクトリにはCollectionの同条件比較も収録。

| CSS幅 | 日本語 前→後 | 英語 前→後 | フォーカス（日／英） |
|---|---|---|---|
| 320 | [前](search-mode-light-evidence/before-listening-ja-320.png) → [後](search-mode-light-evidence/after-listening-ja-320.png) | [前](search-mode-light-evidence/before-listening-en-320.png) → [後](search-mode-light-evidence/after-listening-en-320.png) | [日](search-mode-light-evidence/focus-ja-320.png) / [英](search-mode-light-evidence/focus-en-320.png) |
| 375 | [前](search-mode-light-evidence/before-listening-ja-375.png) → [後](search-mode-light-evidence/after-listening-ja-375.png) | [前](search-mode-light-evidence/before-listening-en-375.png) → [後](search-mode-light-evidence/after-listening-en-375.png) | [日](search-mode-light-evidence/focus-ja-375.png) / [英](search-mode-light-evidence/focus-en-375.png) |
| 390 | [前](search-mode-light-evidence/before-listening-ja-390.png) → [後](search-mode-light-evidence/after-listening-ja-390.png) | [前](search-mode-light-evidence/before-listening-en-390.png) → [後](search-mode-light-evidence/after-listening-en-390.png) | [日](search-mode-light-evidence/focus-ja-390.png) / [英](search-mode-light-evidence/focus-en-390.png) |
| 430 | [前](search-mode-light-evidence/before-listening-ja-430.png) → [後](search-mode-light-evidence/after-listening-ja-430.png) | [前](search-mode-light-evidence/before-listening-en-430.png) → [後](search-mode-light-evidence/after-listening-en-430.png) | [日](search-mode-light-evidence/focus-ja-430.png) / [英](search-mode-light-evidence/focus-en-430.png) |
| 1280 | [前](search-mode-light-evidence/before-listening-ja-1280.png) → [後](search-mode-light-evidence/after-listening-ja-1280.png) | [前](search-mode-light-evidence/before-listening-en-1280.png) → [後](search-mode-light-evidence/after-listening-en-1280.png) | [日](search-mode-light-evidence/focus-ja-1280.png) / [英](search-mode-light-evidence/focus-en-1280.png) |

基準mainのHTMLを配信して変更前を取得し、同じ合成データで比較した。

## 未検証事項

- **実機iPhone Safari・iOSのselectメニュー・VoiceOverは未検証。** Chromiumのモバイルエミュレーションと区別する。CSSの`appearance`とSVG矢印で見た目を調整したが、iOS実機での表示確認済みとは扱わない。
- MusicBrainz本番疎通は未実行。fixtureで両検索方式と検索品質の回帰を検証。
- 実端末の容量枯渇は未実行。保存例外注入とJSON復元の既存試験を実施。
- その他の過去の全ブラウザ試験は未実行。実行したものは結果一覧に記載。

新規レビュー用PRで提出。今回の承認前にマージしない。手動デプロイは行わない。
