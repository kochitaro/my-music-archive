# Pull距離180px・先頭ボタンの自動非表示

基準main: `87705273001f2fe0ed721419cb479844ce49127c`。専用ブランチ: `feat/pull-distance-top-autohide`。

## Pull to Refresh

ホーム画面モードの成立距離を96pxから180pxへ変更した。距離はタッチ開始時と現在/リリース時の`clientY`の差（CSS px）であり、`scrollY`の弾性変位を距離の代用にしない。

- 180px未満は更新しない。成立距離まで引いた後でも、180px未満まで戻して離せば更新しない。
- 更新可能マークとリリース時の条件は同じ関数を利用する。先頭判定の4px許容、保存/編集保護、二重実行防止は維持する。
- 通常Safariでは独自Pullを登録せず、標準更新へ委ねる。標準更新にはアプリ独自の保存保護を保証できない。フッターの保護付き更新は両モードで維持する。

## 先頭ボタン

既存の右下・セーフエリア対応を維持する。400px以上でスクロールイベントを受けると表示し、最新のスクロールから3,000ms後に180msでフェードアウトする。再度スクロールすれば直ちに再表示し、タイマーを再開する。

- 400px未満やモーダル表示中は即時非表示。
- フェード開始と同時に`inert`、`tabIndex=-1`、`aria-hidden=true`、`pointer-events:none`を適用。フェード完了後は`hidden`とする。透明なタップ対象やTab対象を残さない。
- DOM変更は表示可能かどうかだけを同期し、アイコン自身の属性変更や無関係な更新でタイマーを延長しない。
- Tabキーによるキーボード操作で再表示。ボタンにフォーカスがある間はタイマーを停止し、フォーカスを外すと3秒から再開する。操作中のフォーカスを自動消失させないための例外。
- フッターの「ページ操作」内に「先頭へ戻るボタンを表示 / Show back-to-top button」を追加。スクロール位置が条件を満たすときだけ利用可能。キーボード/支援技術から明示的に再表示してボタンへフォーカスできる。
- reduced-motionではフェードを省略し、3秒後の処理内で非表示にする。先頭への移動も既存の即時移動を維持する。
- スクリーンショット撮影の検出・撮影イベント依存の処理は実装しない。

IndexedDB・保存・移行・復元・JSON処理には変更なし。左右スワイプとカード選択も維持。

## 検証

Chromium（システム版）・Playwright WebKit 26.5、390×844。隔離プロファイルと合成データ・写真のみ。外部通信を遮断。

| 項目 | Chromium | WebKit |
| --- | --- | --- |
| 指の96/179px移動では更新なし、180/220pxで1回更新 | PASS | PASS |
| 弾性変位-250pxでも指179pxなら更新なし | PASS | PASS |
| 指220pxから179pxまで戻して離すと更新なし | PASS | PASS |
| 重複終了イベントでも更新1回、実更新後の全データ・写真一致 | PASS | PASS |
| 保存/JSON復元/原本回収/分岐復旧/編集中の更新拒否 | PASS | PASS |
| 通常モードは独自Pullリスナー0件、両standalone判定を維持 | PASS | PASS |
| 399px非表示・400px表示、3秒待機後のフェード/非表示 | PASS | PASS |
| スクロール再開で再表示・タイマーの再開始 | PASS | PASS |
| フェード中/非表示時のヒットテスト・フォーカス除外 | PASS | PASS |
| Tab・フッターからの再表示、フォーカス中の表示保持 | PASS | PASS |
| 先頭・モーダル中の非表示、reduced-motion時の即時非表示 | PASS | PASS |
| カード45件×3領域・グリッド/リストのタップ/横スワイプ/縦スクロール/評価 | PASS | PASS |

`tests/pull_distance_top_idle.py`では指移動と弾性座標を別々に注入してreload要求を計測する。ボタンの時間経過は実際のタイマーで待機し、MutationObserverでフェード開始時のinert/tabIndex/ポインター状態とCSSの180msを確認。実ナビゲーションと写真一致は`pull_refresh.py`で別に確認している。

実行した試験（両エンジンPASS）:

- `python -u tests/pull_distance_top_idle.py`
- `python -u tests/pull_refresh.py`
- `python -u tests/pull_refresh_stability.py`
- `python -u tests/pull_refresh_modes.py`
- `python -u tests/mobile_navigation.py`
- `python -u tests/mobile_navigation_cards.py`
- `python -u tests/mobile_navigation_native.py`
- `node --test tests/*.test.cjs`: **164/164 PASS**
- JS構文・diffチェックPASS、ページエラー0。

検証環境は以前と同じ作業領域内のWebKitランタイムを使用した。ChromiumのPull/スクロールはCDPタッチも使用。WebKitのPullはイベントシーケンス、wheelは390px幅の通常コンテキストで実施。standaloneはフラグ/メディアクエリのエミュレーションであり実インストールではない。

ログ: [pull-distance-top-idle-evidence](pull-distance-top-idle-evidence/)。

## 実機未検証

iPhone実機で180pxが適切かという操作感、実際の弾性/慣性と指座標の対応、Safari標準更新、ホーム画面Webアプリへの実インストール、VoiceOver操作、実セーフエリア/OS端ジェスチャーは未検証。座標注入やLinux WebKitの結果を実機確認済みとは扱わない。

mainへのマージ・正式環境への反映は行わず、レビューを待つ。
