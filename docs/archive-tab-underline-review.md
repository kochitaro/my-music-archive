# MLA アーカイブ／統計タブ 下線位置・デザイン統一報告

作業日: 2026年11月7日

基準: 最新main `5ff94ebbde90fcf263931c851879fcb742bb3ba4`。着手時にGitHubでPR #32のマージ済み状態を確認し、専用ブランチ`fix/archive-tab-underline-placement`を作成。

## 変更ファイル・実装

- `index.html`: 中分類タブの選択色付きborder-bottomを透明化し、CSSのtext-decorationによる2pxの文字下線へ変更。文字幅へ自然に追従し、skip-inkを無効化した連続線とする。
- ボタン下端の透明border自体は2pxのまま残し、ボックス寸法・文字位置を維持。14px・太さ400・色・44px操作領域・中央配置・12px間隔・フォーカスを変更しない。
- 通常のunderline offsetは4px、日本語は5px、英語のInsightsはgの下への伸びを補うため6px。CSS設定値を文字との実際の空きと見なさず、字形との実描画距離を測定して補正した。
- 非選択は従来のグレー・下線なし。背景・外枠を追加せず、アニメーションも追加していない。
- `tests/top_hierarchy.py`: 旧border-bottom表示を期待した検証を2px text-decorationへ更新。
- `tests/archive_tab_underline.py`: 日英×5幅×3大分類×両状態の60条件を、変更前後でピクセル・DOM座標測定。中央配置・間隔・44px・aria・状態・入力保持・フォーカス・DB非書込みも検証。
- `docs/archive-tab-underline-evidence/`と本文書: 全条件の画面、測定値、回帰ログ、提出資料。

実装差分は中分類の下線CSSのみ。[差分範囲確認](archive-tab-underline-evidence/scope.txt)により、全script要素・最初のstyle以降のHTML・search.js・insights.js/cssが基準mainとバイト同一であることを確認した。PR #32の検索方式CSSブロックもバイト同一。

## 下線の測定

Chromium、device scale factor=1で撮影したボタン画像を解析。背景と文字の混色で文字描画を識別し、下線色と分離する。文字の最下端と線の上端の間の空白行数、線の太さ・左右端、文字の左右端を計測した。DOM RangeとgetBoundingClientRectでは文字／ボタンの座標・寸法を比較する。

| 表記 | 実描画の空き（改修前→後） | 下線の太さ |
|---|---|---|
| 日本語：アーカイブ／統計 | 13px → 3px | 2px |
| 英語：Archive | 16px → 4px | 2px |
| 英語：Insights | 13px → 3px | 2px |

全5幅・3大分類・両選択状態、60条件で確認。線幅と文字の描画幅の差は0〜2px。非選択の下線なし。中央座標は画面中央、タブ間隔は12pxを維持。変更前後と切り替え前後で、文字・ボタンの位置／寸法の変化0。

[変更前後の実測・操作領域・配置の全データ](archive-tab-underline-evidence/measurements.json)

試作時の共通offset 4pxでは、日本語の空き2px、Archive 4px、Insights 1pxだった。言語とInsightsの字形差に必要な補正だけを加え、最終コードで全条件を再計測した。設定値が5px／6pxでも、実描画での空きは3pxである。

検索方式側は13px・1pxの下線、中分類は14px・2pxの下線という階層差を維持した。検索方式側の下線位置・文字色・フォーカス等は変更していない。

## 必須検証

| 指示書項目 | 結果・ログ |
|---|---|
| A1–5 文字直下・実測3〜4px・2px・文字に近い線幅・非選択なし | PASS: `archive_tab_underline.log`, `measurements.json` |
| A6 14px・現行の文字色・太さ | PASS。選択`#c6e7ef`、非選択`#a1adbc`、太さ400、透明背景を確認 |
| A7–10 寸法・位置不変、中央・間隔、44px、focus | PASS。2pxフォーカス、Space操作、中央座標・12px間隔を測定 |
| B 日英×320/375/390/430/1280px、3大分類、両画面 | PASS。重なり・画面外配置・横溢れなし |
| C11–13 画面切替・3大分類・Insights | PASS: `archive_tab_underline.log`, `top_hierarchy.log`, `insights_browser.log` |
| C14–15 検索結果・入力保持・直接切替 | PASS: `browser_smoke.log`, `search_live_ui.log`, `top_hierarchy.log`。105件の結果保持・追加通信なし・検索中の方式変更後の古い応答排除も確認 |
| C16 DB非書込み | PASS。UI切替・入力保持の操作でレコードDBへのsetItem 0。値が同じ書込みもカウント対象 |
| C17 手動追加・登録編集 | PASS: `ui_v0322.log`, `browser_smoke.log` |
| C18 JSON復元・保存保護 | PASS: `save_failure_safety.log`, `ui_v0322.log`, `search_live_ui.log` |
| C19 Live登録編集・写真 | PASS: `compact_live_ui.log`, `ui_v0322.log` |
| Node既存試験 | 137件すべてPASS |
| 差分空白チェック | `git diff --check` PASS |

Node137件とブラウザ試験8本はすべてPASS。今回の自動試験に失敗・タイムアウトはなかった。

[実行結果一覧](archive-tab-underline-evidence/results.json)

検索のfixture回帰では両方式・同名候補・整列・追加読み込み・再試行を確認。JSON/CSV・保存失敗時保護を含む既存試験、Live写真保存失敗後の入力保持と再保存、Insightsの作成編集削除後更新も確認。

DB version 3・キー・構造・保存処理・Web Locks・競合検出・元データ回収・集計・検索コアの変更なし。

## 変更前後の画面証跡

以下はListeningの代表例。証跡ディレクトリに全5幅・日英・Listening／Collection／Live・両選択状態の前後を収録。

| 条件 | アーカイブ選択 前→後 | 統計選択 前→後 |
|---|---|---|
| 日本語390px | [前](archive-tab-underline-evidence/before-listening-archive-ja-390.png) → [後](archive-tab-underline-evidence/after-listening-archive-ja-390.png) | [前](archive-tab-underline-evidence/before-listening-insights-ja-390.png) → [後](archive-tab-underline-evidence/after-listening-insights-ja-390.png) |
| 日本語320px | [前](archive-tab-underline-evidence/before-listening-archive-ja-320.png) → [後](archive-tab-underline-evidence/after-listening-archive-ja-320.png) | [前](archive-tab-underline-evidence/before-listening-insights-ja-320.png) → [後](archive-tab-underline-evidence/after-listening-insights-ja-320.png) |
| 英語320px | [前](archive-tab-underline-evidence/before-listening-archive-en-320.png) → [後](archive-tab-underline-evidence/after-listening-archive-en-320.png) | [前](archive-tab-underline-evidence/before-listening-insights-en-320.png) → [後](archive-tab-underline-evidence/after-listening-insights-en-320.png) |

フォーカス: [日本語320px](archive-tab-underline-evidence/focus-ja-320.png) / [英語320px](archive-tab-underline-evidence/focus-en-320.png)

合成データを使用し、変更前は基準mainのHTMLを配信して取得。新旧で同じデータと表示条件を使用した。

## 未検証事項

- **実機iPhone Safari・iOSキーボード・VoiceOverは未検証。** 上記の字形・ピクセル値・配置・フォーカスはChromiumでの測定であり、Safari実機での確認とは区別する。Safariのフォント・描画で同じピクセル値になると実証したものではない。
- MusicBrainz本番API疎通は未実行。fixture・Nodeによる回帰で検索品質を確認。
- 実端末の容量枯渇は未実行。保存例外注入で保護を確認。
- 過去の全ブラウザスクリプトは実行していない。今回の実行対象は結果一覧のとおり。

新規レビュー用PRで提出。今回の承認前にマージしない。手動デプロイは行わない。
