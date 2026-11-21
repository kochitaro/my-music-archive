# モバイル操作性改善 検証記録

基準: main `1dcd2fc772f19b2f567587fcfc9813d827e9883c`。専用ブランチ `feat/mobile-navigation`。

## 変更

- 言語選択の左に20pxの更新アイコン（44pxタッチ領域）。通常は `location.reload()`。
- 保存・設定保存・JSON復元・原本回収処理中、編集中モーダル・未保存ドラフトがある場合は更新拒否。起動・移行待ちは既存の `inert` を維持。処理完了を強制しない。
- 400px以上のスクロールで右下に先頭ボタン。セーフエリア用 `env()`、ネイティブbutton、日本語/英語のアクセシブル名、キーボード、移動後のフォーカス、reduced-motionに対応。モーダル中は非表示。
- Archive画面内の左右スワイプで Listening ⇄ Collection ⇄ Live。既存 `setSection()` の状態管理を経由し、端では停止。
- アーカイブのカード/リスト行はスワイプ可能。両端32px、その他の操作部品・評価スライダー・編集可能領域・横スクロール領域を除外。縦・斜め操作、マルチタッチ、キャンセルを除外。横方向確定後のみ既定動作を抑止し、終了時に一度だけ切替。直後のポインタークリックを抑止し、キーボード/支援技術のclickは維持。
- 保存サービス、IndexedDBスキーマ、移行・復旧エンジン、JSON形式の変更なし。原本回収UIにも既存の処理中ガードを適用。

## 自動検証

Linux Chromium（システム版）・Playwright WebKit 26.5。390×844、モバイル・タッチ設定、隔離プロファイル、合成データのみ。外部通信は遮断。

| 項目 | Chromium | WebKit |
| --- | --- | --- |
| 旧データ移行後、通常更新でIndexedDBの全フィールド・写真が一致 | PASS | PASS |
| 日本語・英語の更新ボタン名 | PASS | PASS |
| 未保存編集・保存失敗ドラフトの更新拒否、入力保持 | PASS | PASS |
| 実際の保存・復元・検証済み分岐復旧・原本回収を待機させ更新/切替を拒否 | PASS | PASS |
| 初期化・移行前の待機中は更新UIがinert | PASS | PASS |
| 先頭へのsmooth移動・Enter操作・フォーカス・上部非表示 | PASS | PASS |
| reduced-motion時の即時移動、モーダル中の非表示 | PASS | PASS |
| 左右切替・両端停止・タブごとのソート状態保持 | PASS | PASS |
| 縦/斜め・端・操作部品・評価・横スクロール・モーダル除外 | PASS | PASS |
| マルチタッチ・キャンセル・複数move・直後click抑止 | PASS | PASS |
| 3領域の登録・編集・削除、写真付きJSONの書出/復元/再読込 | PASS | PASS |
| ページ内JavaScriptエラー | 0 | 0 |

スワイプの網羅テストは決定的なTouchEvent相当シーケンスで行う。保存/復旧待機・失敗の注入はテスト専用のサービスプロキシとHTMLレスポンスで実施し、アプリ配布物に含めない。起動待機はinit開始前のゲートで再現する。

- `python -u tests/mobile_navigation.py`（両エンジン、個別指定も可）
- `python -u tests/mobile_navigation_native.py`（ソース差替えなし、ChromiumのCDPタッチ、両エンジンのwheel）

追加検証もPASS: Chromiumネイティブタッチで左右切替・縦スクロール・誤モーダル防止。両エンジンでwheelと先頭移動、390px幅の横はみ出しなし。WebKitのwheelはモバイルエミュレーションAPIが非対応のため、通常コンテキストを390px幅にして検証した。モバイル設定のWebKit検証は上の網羅テストで実施。
- `node --test tests/*.test.cjs`: **164/164 PASS**
- `node --check mobile-navigation.js`、`git diff --check`: PASS

環境のWebKit依存ライブラリ不足は作業領域内のブラウザコピーで補った。`MLA_WEBKIT`でそのランチャーを指定可能。ホストのライブラリ索引に載らないためPlaywrightの事前依存検査だけを省略し、実際のWebKitを起動・操作して検証した。

ログ: [mobile-navigation-evidence](mobile-navigation-evidence/)。

## 実機未検証

- iPhone Safari通常表示とホーム画面Webアプリの実際のタッチ/慣性・再読み込みのライフサイクル。
- Safariの画面端戻る/進むジェスチャーとの実際の共存（実装は両端32pxからの操作に介入しない）。
- ノッチ・ホームインジケータ・回転時の実セーフエリア、ソフトウェアキーボード表示時のレイアウト。
- VoiceOverの読み上げ・ローター・フォーカス遷移の実操作。DOMの名前・button・キーボードの自動検証は実施済み。
- OSによる強制終了やブラウザ自体の更新操作の完全な阻止。追加した更新ボタンは安全を確認して拒否し、既存beforeunloadは維持している。

mainへのマージ・正式環境への反映は実施しない。


## PR #42 追加修正: カード上のスワイプ

対象: `d955f76`への追加修正。保存関連ファイル・更新保護・復元処理に変更なし。

以前はアルバム/Liveカード全体がbuttonとして除外されていたため、一覧の見出しや余白からしかスワイプを開始できなかった。`#library`内のカードボタンとリスト行に限って除外の例外とし、アートワーク・タイトル・通常の表示領域から切替可能にした。入れ子の評価・入力・各種操作部品、横スクロール領域、無効なカードは引き続き除外する。タップ、横方向の判定閾値、直後のクリック抑止、新しいタッチでの通常操作、画面端32pxのガード、setSection()は維持。

追加テスト: `python -u tests/mobile_navigation_cards.py`。Listening/Collection/Liveを各45件、グリッドとリストの両表示で確認。

| 追加確認 | Chromium | WebKit |
| --- | --- | --- |
| 密集したカード/行の通常タップで正しい詳細を開く | PASS | PASS |
| アートワーク/タイトル上の横スワイプで切替、誤詳細表示なし | PASS | PASS |
| 複数move・重複touchendでも1回のみ切替、直後clickを抑止 | PASS | PASS |
| スワイプ直後でも新たなタップは詳細を開く | PASS | PASS |
| カード上から縦スクロール、切替・誤詳細表示なし | PASS | PASS |
| 画面端・斜め・キャンセル・複数指を除外 | PASS | PASS |
| 入れ子の評価/入力・横スクロール・操作ボタンを除外 | PASS | PASS |
| モーダルでの実際の評価タップとフォーム入力を維持 | PASS | PASS |

ChromiumはCDPのネイティブタッチ入力。WebKitは390px幅の通常コンテキストでタッチシーケンス、実際のtapとwheelを組み合わせた。WebKitのwheelはモバイル設定のAPIが非対応。追加テストはアプリのソース差替えなし（合成データと入れ子操作部品の試験用DOMのみ注入）。iPhoneで指を動かした実機確認とは区別する。

既存の `mobile_navigation.py`（Chromium/WebKitモバイル設定）、`mobile_navigation_native.py`（両エンジン）、Node回帰164件を再実行し、すべてPASS。旧「カードも除外」のテストケースは、新しいカード専用テストに置き換えた。JavaScriptページエラー0。新しい結果は `mobile-navigation-evidence/dense-cards.log` と更新済みの既存ログを参照。

iPhone Safari・ホーム画面Webアプリでの自然な指操作、OSの端ジェスチャーとの実際の共存は引き続き未検証。mainマージ・正式環境反映は行わない。
