# MusicBrainz通信制御の実装・検証

## 対象

- 開始時remote main: `8aa8cfc7a4537ec5c3fd9218b5faf52f98eddcbe`（提示SHA、PR #56と一致）。
- ブランチ: `fix/musicbrainz-shared-throttle`。mainのマージ、Production/DNS/Access設定変更なし。
- コミットのauthor/committerは既存履歴のGitHub noreplyと照合。個人メールは記載しない。

## 実装

`search.js`のrequest()が全検索経路を引き続き集約する。キャッシュとpending重複排除はゲートの手前。
通信ロック`mla:musicbrainz:request:v1`とlocalStorageキー`mla:musicbrainz:traffic:v1`を追加。
共有値はversion、lastStartAt、cooldownUntilだけ。語・結果・記録は含まない。
保存ロック`mla:my-music-archive-pilot-v03:write`、記録DB、バックアップ形式、CAAに変更はない。
User-Agentは標準、MusicBrainzへのブラウザ直接通信のまま。

- exclusive + ifAvailableで取得。待機はロック外、最大100msごとに取消・共有時刻を再判定。
  送信前に状態の書込・再読取を検証。Fetch呼出し直後にも開始時刻を更新し、整数msの丸めに1msの保守的余裕を置く。
- ヘッダーと失敗クールダウンの保存までロック保持。本文JSON解析はロック外。
  本文読込失敗のバックオフも再取得した同じロックで共有する。
- 開始間隔1250ms、最大4試行、バックオフ2/4/6秒、各試行のFetch・本文タイムアウト20秒を維持。
  最終失敗にも6秒以上のバックオフまたはサーバー指定期限を保存。
- Retry-Afterは整数/従来の小数秒、IMF-fixdate、RFC850、asctime。小数msは切上げ。
  HTTP旧形式の2桁年は50年ルールで解釈。IMFの不正な暦日、非HTTP文字列、負数はバックオフ。
  asctimeは端末タイムゾーンに依存させずGMTで解釈。
- ロック/タブ内キュー/各ゲートの操作待機は30秒。残りが上限超過なら処理終了、期限は消さない。
  数値範囲超過の有効な指定はcooldownUntil:nullで期限なし停止。短い値へ丸めない。
- Web Locks非対応、共有状態破損・消去検知、読書込失敗は検索停止。無排他送信なし。
  エラー時、可能なら通信ロック内で永続停止マーカーを保存する。
- 活動中の壁時計とperformanceの進みが250msを超えて乖離した場合は検索を停止。
  共有開始時刻が不自然に未来の場合も停止する。
- visibilitychange(hidden)/pagehideで世代を無効化し通信をabort。BFCache復帰でも旧世代を無効化。
  新しい明示的検索だけが再開する。検索語や取得済み結果をライフサイクル処理から消去しない。
- index.html変更は既存statusの日英通知に限定。保存処理へ検索エラーを伝播しない。

30秒は各通信の操作待機上限で、複数試行を含む検索全体の実時間上限ではない。
タイマーが凍結している間の正確な終了時刻は保証しない。復帰後、送信前に再判定する。

## 検証結果

すべてローカル模擬API/合成データ/新規コンテキスト。実MusicBrainzへの通信は0回。
タイミング試験の時計、1250ms、20秒、30秒を短縮していない。

| 検証 | 結果 |
| --- | --- |
| node --test tests/*.test.cjs | 187件成功（既存166＋追加21） |
| python tests/browser_smoke.py | Chromium 14グループ成功、JSエラーなし |
| node tests/transport_browser.cjs chromium | 完走、Chromium 156.0.8078.79 |
| PLAYWRIGHT_BROWSERS_PATH=/tmp/mla-audit-browsers node tests/transport_browser.cjs firefox | 完走、Firefox 153.0 |
| 同WebKit | 起動環境不足。テスト本体未実行、合格扱いしない |
| python tests/static_build.py | 5件成功 |
| node scripts/build-static.cjs | 成功、公開17ファイル |
| python tests/static_distribution.py | source/dist・ルート/サブパス・日英・CRUD/写真/JSON・法的文書/404確認成功 |

| 実測シナリオ | Chromium Fetch開始最小ms | Firefox Fetch開始最小ms |
| --- | ---: | ---: |
| 5タブ、リトライ込み11要求 | 1251.900 | 1252 |
| 2タブ同時 | 1253.300 | 1260 |
| HTTP-dateリトライ | 3206.800 | 3813 |
| CORS非公開Retry-After | 2008.600 | 2022 |
| 20秒timeout＋バックオフ | 22003.800 | 22038 |

全グループのFetch開始・模擬API受信時刻は*-timing.jsonに保存した。
5タブの受信間隔最小はChromium 1250.915ms、Firefox 1242.920ms。
受信間隔は要求ごとの転送・ブラウザ/OSスケジューリングの揺れで開始間隔と異なる。
開始間隔1250ms以上を合格条件としてassertし、受信間隔がすべて1250ms以上だったとは主張しない。
他グループにも1250ms未満の受信間隔がある。ネットワーク到着時刻そのものの厳密保証ではない。

秒数/HTTP-date/不正/過去/小数/なし/非公開/表現範囲超過、最終失敗後の別URL・別タブ・再読込、
30秒を超える指定、実30秒ロック待機打切り、実20秒abort、待機中取消と有効な重複リスナー、
通信中の実タブ終了、合成hidden/復帰、共有状態破損・書込拒否・通信ロック利用不可を確認。
検索停止/待機中に、手動登録・編集・削除・写真・Insights・JSON書出し/復元/再読込・日英切替を確認。
キャッシュ、アーティスト/アルバム/エイリアス/補完/ページング/方式切替/古い結果排除/再検索は既存Node/スモークでも確認。

スモークの旧タイマー短縮を削除。実際の2/4/6秒待機と最終クールダウンに合わせ、失敗・回復のassert期限だけを延長。
期待結果の削除・スキップや、アプリの間隔短縮はない。
WebKitは既知のGTK4/graphene/harfbuzz-icu/manette/hyphen/GLES不足が継続。追加整備は繰り返していない。

## 残存制約

- iPhone実機のOS凍結、画面ロック、復帰は未検証。手順はiphone-check.md。
- 既存保存自体がWeb Locks必須。APIが端末全体で欠ける環境で編集・削除を新たに可能にはしていない。
  通信専用ロック/共有状態の異常からアーカイブ操作への波及がないことを確認した。
- CORS非公開のRetry-Afterは取得不能。通常バックオフで抑制するが未知の指定時間の厳密遵守は保証できない。
- 応答前にタブが終了した場合、その応答のRetry-Afterは取得できない。
- 全タブが閉じている間や新規文書の基準時計取得前の時計変更は検出できない。端末時計の正しさが前提。
  活動中でも250ms以下の時計差を完全識別するものではない。
- 応答後の状態書込が拒否された場合、その文書は停止し、可能なら停止マーカーを共有する。
  そのマーカーの永続化自体が拒否される場合、他文書への未知のサーバー指定時間の伝達は保証できない。
- 共有状態の破損・範囲超過による停止は自動的に短縮/初期化しない。復旧時にアーカイブ全消去を案内しない。
- 旧版タブ、異なるオリジン/プロファイル/ブラウザ/端末、同一IPの他アプリは協調対象外。
- ロック取得の公平性は保証しない。30秒で処理を終了し、強制取得や無排他送信はしない。
- 標準UA許容はレート制限免除やStealth Start-Up承認を意味しない。

Previewは既存deploy/previewの履歴を維持し、PRソースと同一treeのコミットを用いる。
Access保護は無認証302で確認。デプロイSHAと確認結果はPR/完了報告に記載する。
