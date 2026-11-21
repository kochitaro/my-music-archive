# Pull to Refresh 安定性調査・改善

> 本書は方針変更前の調査記録。PR #44の最終仕様と検証結果は[モード別の更新仕様](pull-refresh-modes.md)を参照。通常Safariでも独自Pullを使う記述は、新しい方針で置き換えられた。

調査基準main: `1dc757a`（PR #43統合後）。専用ブランチ: `fix/pull-refresh-stability`。
録画ファイル・iPhone接続は提供されていない。以下のコード/座標注入での再現と、ユーザー報告の実機症状との因果関係は区別する。

## 調査した5点

1. **先頭判定**: 旧コードは開始・途中・終了で`scrollY > 0`を拒否する。`0.5`での開始や、操作途中だけ`1.25`になるケースを両エンジンで注入すると、更新0回となった。負の値のみのケースは旧版でも更新した。Safariの弾性スクロールは負の値を返すため「負だから失敗する」という説明は誤り。小数と途中の正方向変動が拒否条件に当たる。
2. **開始位置**: 旧版はボタン・左右端32pxからのPullを除外していた。タブ上や端からの縦Pullで更新0回を再現。入力・評価・内側スクロール領域の除外は競合防止に必要だが、通常ボタン上の縦Pullまで除外する必要はない。
3. **標準Pullとの競合**: 通常表示とホーム画面表示で同じcontain/preventDefaultを使っていた。containは境界の既定動作を制御するもので、実際に制御できたことを`CSS.supports`だけでは保証できない。動的containと実機Safariの標準Pullの競合は実機未確認であり、今回の失敗原因と断定しない。
4. **途中解除**: `scrollY > 0`、複数指、識別子不一致、方向判定、`cancelable === false`、touchcancel、blur、pagehideで解除する。ホーム画面フラグを有効にした旧版も、キャンセル不能な下方向イベントを注入すると判定を失うことを確認した。複数指やキャンセルの解除は維持すべきだが、ホーム画面での自然な弾性スクロールまで破棄する必要はない。
5. **Safari標準優先の可否**: 通常Safariを標準Pull、ホーム画面を独自Pullへ分ける案は操作感の点では候補になる。ただしブラウザ標準更新はアプリの共通ガードを通らず、beforeunloadもモバイルで保証できない。保存・復元・編集中の保護を維持する要件のため、今回の変更では通常Safariを無条件の標準更新へ切り替えない。

参考: [MDN scrollY](https://developer.mozilla.org/en-US/docs/Web/API/Window/scrollY)、[MDN cancelable](https://developer.mozilla.org/en-US/docs/Web/API/Event/cancelable)、[MDN beforeunload](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event)、[CSS Overscroll Behavior](https://www.w3.org/TR/css-overscroll/)。古いWebKit不具合報告だけを根拠に現在の実機バグとは断定していない。

## 改善内容

- 先頭は`Math.max(0, scrollY) <= 4`で判定。4pxは端の微小誤差に対する実装上の許容量で、iOSの保証値ではない。先頭から始まった候補を途中の正の値だけで捨てず、戻れば再成立可能とする。通常スクロールから途中で先頭に到達しても新規Pullには昇格しない。
- Pull専用の操作対象判定を左右スワイプから分離。通常ボタン・端からの縦Pullを許可し、入力・選択・評価・編集可能領域・内側スクロールは除外する。左右スワイプの端32pxガード・ボタン除外は変更しない。
- `navigator.standalone` / `display-mode: standalone`ではcontainとpreventDefaultを使わず、自然な弾性スクロールを追跡する。キャンセル不能なmoveも継続して観測する。モードは操作開始時に確定する。
- 通常ブラウザでは既存のcontainとキャンセル可能なmoveでの抑制を維持。ブラウザが操作を引き受け、キャンセル不能になった場合は独自のreloadを追加せず、ページ操作からの更新をstatus領域で案内する。
- 36pxでの早期アイコン表示を廃止。96px以上・先頭・保存保護を通過できる場合だけ「離して更新」のアイコンを表示する。表示と指を離した時点の条件を同じ関数に集約。戻した場合・保存不可・端から離れた場合は成立表示を消す。
- 更新直前のガード、多重実行防止、キーボード/VoiceOver用のフッター更新、先頭ボタンは維持。

変更は`mobile-navigation.js`と試験・記録のみ。IndexedDB・保存・移行・復元処理、beforeunloadには変更しない。

## 再現と検証

`tests/pull_refresh_stability.py`は`scrollY`とイベントのcancelableを注入し、reload要求数を計測する。実際の弾性スクロールやSafari UIの再現ではない。旧版と新版で同一の列を測定した。

| 条件 | 旧版 | 改善版 |
| --- | --- | --- |
| scrollY=0.5からPull | 更新しない | 更新1回 |
| 途中でscrollY=1.25 | 判定を破棄 | 更新1回 |
| 負のscrollYのみ | 更新1回 | 更新1回 |
| 通常ボタン上から縦Pull | 更新しない | 更新1回 |
| 左右端から縦Pull | 更新しない | 更新1回 |
| ホーム画面モード・キャンセル不能move | 判定を破棄 | 更新1回 |
| 通常ブラウザ・キャンセル不能move | 独自更新しない | 独自更新しない・代替手段を案内 |

Chromium/WebKit、通常/ホーム画面フラグの各組み合わせで上記が一致。95pxではマークなし/更新なし、96pxではマークあり/更新1回、途中で正方向へ6px逸れて戻った場合の再成立、複数指・キャンセル・二重終了・入力/評価の除外、ホーム画面での未保存編集拒否もPASS。

実行結果:

- `tests/pull_refresh_stability.py --characterize`: 旧版の再現ログを保存
- `tests/pull_refresh_stability.py`: 両エンジンPASS（座標・イベント注入、reload要求を計測）
- `tests/pull_refresh.py`: 両エンジンPASS（実際の更新、全データと写真一致、保存/JSON復元/原本回収/分岐復旧/編集中の拒否、キーボード更新）
- `tests/mobile_navigation.py`: 両エンジンPASS
- `tests/mobile_navigation_cards.py`: 両エンジンPASS（45件×3領域、グリッド/リストのタップ・横スワイプ・縦スクロール・評価）
- `tests/mobile_navigation_native.py`: 両エンジンPASS
- Node回帰: **164/164 PASS**。JS構文・diffチェックPASS。

合成データ・隔離プロファイルのみ。外部通信は遮断。ChromiumはネイティブCDPタッチも使用。WebKitのPullはイベントシーケンス、wheelは390px幅の通常コンテキスト。ホーム画面はフラグのエミュレーションであり実インストールではない。検証ランタイムは前回同様`MLA_WEBKIT=/workspace/webkit-runtime/pw_run.sh`を使用した。

ログ・画像: [pull-refresh-stability-evidence](pull-refresh-stability-evidence/)。

## 残る制約・実機確認が必要なこと

**今回の修正でiPhoneの実症状が解消したとはまだ判断しない。** 通常Safariのキャンセル不能な操作では、引き続き独自更新を成立させない。Safariの標準更新自体をアプリから完全に保護できる保証も追加していない。

実機Safari/ホーム画面で同じ場所から複数回引き、弾性・慣性・ツールバー位置・標準Pullとの共存・OSの端ジェスチャーを確認する必要がある。VoiceOver実操作も未確認。録画だけからscrollYやcancelableの実値は判定できない。

mainへのマージ・正式環境への反映は行わず、レビューと実機再確認を待つ。
