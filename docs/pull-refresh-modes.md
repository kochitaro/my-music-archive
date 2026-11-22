# PR #44 モード別の更新仕様・検証結果

> 本書はPR #44時点の仕様。後続の[更新距離・先頭ボタン改善](pull-distance-top-idle.md)で、standaloneの更新距離を180pxへ変更した。通常モードとstandaloneの分離方針は維持している。

この仕様は、PR #44の初回実装（`9cf2be9`）の方針を置き換える。ブランチは引き続き `fix/pull-refresh-stability`。

## 最終仕様

起動時に `navigator.standalone === true` **または** `matchMedia('(display-mode: standalone)').matches` でホーム画面モードを判定する。どちらもfalseなら通常モード。通常Safariだけでなく、通常モードの他のブラウザでも独自Pullを有効にしない。

| 操作 | 通常モード | standaloneモード |
| --- | --- | --- |
| 下に引いて更新 | ブラウザ標準に委ねる | MLA独自Pull |
| 独自Pullのdocumentタッチリスナー | 登録しない（0件） | 4件、すべてpassive |
| 独自マーク・Pullのstatus更新 | なし | 更新可能な状態で96px以上引いた間のみ |
| Pull用のpreventDefault / contain切替 | なし | なし、弾性スクロールを観測する |
| フッター「ページ操作 → 更新」 | 保存保護付き | 保存保護付き |
| 左右スワイプ・アルバム操作・先頭ボタン | 維持 | 維持 |

通常モードでは、Pullの状態・判定・タッチハンドラー・スクロール監視を初期化しない。CSSの`html.pull-tracking`も撤去した。既存の左右スワイプはアーカイブ領域で引き続きタッチを扱うが、これはPull更新とは別機能であり、縦方向では既定動作をキャンセルしない。

**通常Safariの標準更新は、MLAの保存・復元・未保存入力・編集中の共通ガードを通らないため、アプリ独自の保存保護を保証できない。** 既存beforeunloadを変更/強化したものでもない。アプリの保護を使いたい場合は、両モードで維持する「ページ操作 → 更新」を利用する。

standaloneモードでは次を維持する。

- 先頭4px以内または弾性スクロールの負の位置から始まった1本指の下方向操作。途中で先頭に到達した通常スクロールは更新操作に昇格しない。
- 96pxの成立閾値とマーク表示条件を共通化。戻し・複数指・キャンセルは更新しない。
- キャンセル不能なmoveも観測し、スクロールを抑止しない。方向が横の場合はPullを破棄し、既存アーカイブ切替へ委ねる。
- 通常のボタンやカード、端からの縦Pullは許可。入力・選択・星評価・内側スクロール領域は除外。
- リリース時に保存/復元/原本回収/編集/未保存状態を再確認し、不可なら理由を案内。更新可能なときだけ1回リロードし、多重実行を拒否。

IndexedDB・保存サービス・移行/復元処理・JSON形式に変更なし。共通の保存ガードやbeforeunloadにも追加変更なし。

## 自動検証

Chromium（システム版）とPlaywright WebKit 26.5。390×844、隔離プロファイルと合成データ/写真のみ。外部通信は遮断。

`tests/pull_refresh_modes.py`で各エンジンの次の4パターンを確認した。

| navigator.standalone | display-mode: standalone | document Pullリスナー | Pullによる独自更新 |
| --- | --- | --- | --- |
| false | false | 0 | 0回 |
| true | false | 4（passive） | 1回 |
| false | true | 4（passive） | 1回 |
| true | true | 4（passive） | 1回 |

通常モードは、キャンセル可能/不可能な下方向イベントを注入しても、既定動作のキャンセルなし・マーク属性/statusの変更なし・独自リロード0回。standaloneは同じシーケンスで更新1回。両モードで左右スワイプ、先頭ボタン、フッターのキーボード更新、フッターからの編集中更新拒否もPASS。

追加/既存試験の結果:

- `tests/pull_refresh.py`: standaloneでの実更新・写真と全フィールドの再読込一致、編集中・実保存/JSON復元/原本回収/分岐復旧中の拒否、キャンセル/閾値/多重防止が両エンジンでPASS。通常モードのフッター更新もPASS。
- `tests/pull_refresh_stability.py`: standaloneでの小数座標、微小変動、端/ボタン開始、キャンセル不能move、閾値とマークの一致、入力保護が両エンジンでPASS。
- `tests/mobile_navigation.py`: 両エンジンPASS。
- `tests/mobile_navigation_cards.py`: 両エンジンPASS。通常モードで45件×3領域、グリッド/リストのタップ・横スワイプ・縦スクロール・評価を確認。
- `tests/mobile_navigation_native.py`: 通常モードのネイティブタッチ/スクロール・先頭ボタンを確認。
- Node回帰: **164/164 PASS**。ページエラー0。JS構文/diffチェックPASS。

Pull処理の登録数はdocumentへのイベント登録を計測、表示無変更はMutationObserverで確認した。モードテストのreload回数はテスト専用に計測し、実際のナビゲーション・IndexedDB/写真は別のE2E試験で確認している。Chromiumの実Pull試験はCDPタッチも使用。WebKitのPullはTouchEvent相当シーケンス、通常スクロールのwheelは390px幅の通常コンテキストで検証した。起動環境は以前と同じ作業領域内のWebKitランタイムを使用。

ログ: [pull-refresh-modes-evidence](pull-refresh-modes-evidence/)。

## 実機未検証

- iPhone通常Safariの標準Pull・標準更新UIと実際のナビゲーション。
- iPhoneのホーム画面へインストールした実アプリでの弾性/慣性、繰り返しPullの操作感。
- Safariのツールバー位置、OS画面端ジェスチャー、実セーフエリア、ソフトウェアキーボード、VoiceOver実操作。

standaloneはフラグ/メディアクエリのエミュレーションであり、実インストールや実機症状の解消確認とは区別する。通常Safariが標準更新へ任せられる構成は自動検証したが、Safari UI自身の動作をLinux WebKitで確認したとは扱わない。

mainへのマージ・正式環境への反映は行わずレビュー待ちとする。
