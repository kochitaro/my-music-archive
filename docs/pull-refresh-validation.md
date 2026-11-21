# Pull to Refresh 変更と検証

基準main: `35004d12fb943628649bbf377974fee58f80c6a1`（PR #42マージ後）。ブランチ: `feat/pull-to-refresh`。

## 動作

- 言語選択横の更新ボタンを撤去。ページ先頭から始まった1本指の下方向操作だけを検出する。
- 最初の10pxで方向を判定。横・斜め・上方向への操作、途中から先頭に到達するスクロールでは更新しない。
- 下に36px引くと34pxの控えめな更新アイコンを表示。96px以上引いた状態で指を離すと更新する。戻して閾値未満になった場合やキャンセル時は更新せず、アイコンを消す。
- 処理中・未保存入力・編集モーダルの判定はPR #42の状態取得関数を再利用。更新直前に再確認し、拒否時は日本語/英語で理由を案内する。保存/復元/原本回収を中断しない。
- 再読み込み要求後はフラグで追加の更新を拒否。横スワイプと同じクリック抑止を利用し、新しいタッチは通常操作として受け付ける。
- 評価、入力、操作ボタン、横スクロール領域、縦スクロール可能な内側の領域、両端32px、ピンチ拡大中、複数指、キャンセルを除外する。
- 左右スワイプはPR #42のカード対応を維持。先頭ボタンも維持し、移動後のフォーカス先をページ見出しに変更した。
- キーボード/VoiceOver用の更新手段は、フッターのネイティブdetails「ページ操作 / Page actions」内に小さなbuttonを置く。通常表示では閉じており、保存保護はPullと同一。引っ張り成立時の案内はrole=statusで通知する。

IndexedDB、保存サービス、移行・復旧エンジン、JSON形式に変更なし。既存の操作中クリック遮断では、理由案内を持つ更新要求buttonだけを通し、そのbutton内の共通ガードで更新を拒否する。

## 通常Safariとホーム画面Webアプリの扱い

両モードとも、`overscroll-behavior-y: contain`対応ブラウザでは同じ独自Pull処理を使う。先頭からの操作が更新候補である間だけルートにcontainを適用し、下方向確定後のtouchmoveをpreventDefaultする。これによりブラウザ標準のPull経路と独自経路の並走を避ける設計。候補でなくなった時点・終了・キャンセル・ページ離脱時にはcontainと表示を取り除く。

既存CSSのoverflow指定との組み合わせで、containをbodyに指定するとChromiumの縦スクロールが、ルートに常時指定するとWebKitのwheelが止まることを再現した。そのためbodyには追加せず、ルートも候補操作中だけに限定した。通常のスクロール経路・レイアウトには介入しない。

CSS非対応環境では独自Pullを有効にせず、保護付きの「ページ操作 → 更新」を残す。ブラウザ自身の更新ジェスチャー・ブラウザの更新コマンドはアプリ外の操作であり、旧Safariなどでその保存保護まで保証するものではない。既存beforeunloadは維持している。

実際のSafari UIが持つ標準Pullとの共存と、ホーム画面Webアプリのスクロール感はiPhone実機未確認。対応CSSの有無だけで実機確認済みとは扱わない。

## 自動検証

合成データと写真のみ、隔離プロファイル、外部通信を遮断。Chromium（システム版）・Playwright WebKit 26.5、390×844。

| 項目 | Chromium | WebKit |
| --- | --- | --- |
| 最上部でのPull更新、重複終了イベントでも1回のみ | PASS | PASS |
| 36px表示・96px閾値、戻し/閾値未満で非更新・表示リセット | PASS | PASS |
| 通常スクロール、途中から先頭、方向・端・複数指・cancel・非cancelable除外 | PASS | PASS |
| 編集中、実際の保存・JSON復元中の更新拒否と理由案内 | PASS | PASS |
| 原本回収・検証済み分岐復旧中の拒否と完了後のデータ保持 | PASS | PASS |
| 更新後IndexedDBの全フィールド・写真が一致 | PASS | PASS |
| 45件×3領域のグリッド/リストで左右切替・タップ・縦スクロール | PASS | PASS |
| キーボードでdetailsから更新、先頭ボタンと移動後フォーカス | PASS | PASS |
| CSS非対応時の独自Pull無効化とキーボード更新 | PASS | PASS |
| JavaScriptページエラー | 0 | 0 |

ChromiumではCDPのネイティブタッチによる先頭Pull更新も確認。WebKitのPullはTouchEvent相当シーケンスで方向と閾値を検証し、実際のSafariの指操作ではない。WebKitの通常スクロールは390px幅の通常コンテキストでwheelを検証（モバイル設定のwheel APIが非対応のため）。ホーム画面モードはstandaloneフラグのエミュレーションのみ。OSへのインストール確認ではない。

実行した試験:

- `python -u tests/pull_refresh.py`: 両エンジンPASS
- `python -u tests/mobile_navigation.py`: 両エンジンPASS（更新先をフッターのbuttonへ変更し、先頭移動後のフォーカス期待値を見出しへ変更）
- `python -u tests/mobile_navigation_cards.py`: 両エンジンPASS
- `python -u tests/mobile_navigation_native.py`: 両エンジンPASS
- `node --test tests/*.test.cjs`: 164/164 PASS
- `node --check mobile-navigation.js`、`git diff --check`: PASS

この環境では、前回検証で作業領域に用意したWebKitランタイムを`MLA_WEBKIT=/workspace/webkit-runtime/pw_run.sh`で利用した。ローカルに展開したライブラリを使用するため、Playwrightのホスト索引だけの依存検査を省略した。実際のブラウザは起動して操作している。

ログ・Pull中のスクリーンショット: [pull-refresh-evidence](pull-refresh-evidence/)。

## 未確認

- iPhone Safari・ホーム画面Webアプリでの実際の指操作、弾性/慣性スクロールと標準Pullの抑制。
- 画面端のOSジェスチャー、実セーフエリア、ソフトウェアキーボード、VoiceOver実操作。
- CSS非対応の旧Safariの標準更新動作。

mainへのマージ・正式環境への反映は行わずレビュー待ちとする。
