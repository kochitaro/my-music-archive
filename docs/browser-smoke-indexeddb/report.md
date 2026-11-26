# ブラウザスモーク IndexedDB追従 検証報告

## 対象・変更範囲

- 開始時のremote mainをgit ls-remoteで確認：892abddfcebc76a18218bebf16b97e897a17f576（提示SHAと一致）
- 専用ブランチ：test/browser-smoke-indexeddb
- 実行環境：Linux、Python 3.12、Playwright 1.62.0、Chromium 156.0.8078.79
- 変更：tests/browser_smoke.py と本ディレクトリの検証記録のみ。アプリ本体・公開成果物のソースは変更なし。
- 公開環境の閲覧・デプロイ・mainマージなし。Cloudflare Preview・iPhone実機検証は実施せず。
- コミット時の実効author/committerが履歴と同じGitHub noreplyであることを照合。個人メールは出力せず。

## 旧仕様への依存（変更前の行番号）

| 箇所 | 問題と対応 |
| --- | --- |
| 10行 KEY | 旧localStorageキー。移行元としてのみ保持 |
| 54行 stored() | 通常保存も旧localStorageを参照。IndexedDBスナップショットへ置換 |
| 63–64行 初期投入・比較 | アプリ初回起動後に移行元を変更して再読込。初回DB生成前のローカル空ページで投入し、移行後DBを厳密比較 |
| 94行 Listening追加 | DB保存結果・既存記録を確認 |
| 97行 Collection追加 | DB保存結果のreleaseを確認 |
| 101行 必須項目ガード | 保存前後Collectionの厳密比較に変更（件数だけの比較より強い）。期待される警告が出ているため直接readonlyスナップショットを使用 |
| 102行 手動補正後保存 | DBのartistを確認 |
| 124行 Live保持 | DBのLiveを元seedと厳密比較 |
| 134–135行 API作品保存・元記録保持 | DBのartist/title/release・元Listening/Liveを確認 |
| 保存全般 | 非同期保存完了の確認なし。起動Promise、UI操作完了、meta ready、設定言語の反映とエラーパネルを確認 |

写真・編集・削除・JSON書出し/復元・記録の再読込確認は元スモークには存在しなかったため、小規模の合成データで追加。既存検証は削除・スキップしていない。元の検索間隔短縮と検索の負の検証用50/150ms待機は保持し、保存完了判定には使用しない。

## 保存確認の根拠・方法

archive-store.jsの実装に従い、mla-archive-v1 の archive/meta/settings のcurrentとphotosを同一readonlyトランザクションで取得する。トランザクション完了後にのみ返し、エラー・abort・blockedは失敗とする。未作成DBを検証側で生成しないようupgradeをabortする。

MLAReadyをawaitし、操作中に無効化されるui-languageの有効化、保存停止/失敗通知の非表示を確認する。meta.status=readyとsettings.languageの反映は条件で待機する。保存失敗を固定時間経過で成功扱いにしない。記録追加はモーダル終了も待機し、内容は元の期待値で検証する。必須項目ガードだけは期待される警告を明示的に検証する。

通常保存の判定はDBを直接参照し、photoIdは同じスナップショットのphotos値へ解決する。実際のUIからダウンロードしたJSON version 3は、解決後の全アーカイブと厳密比較する。写真付きJSONを復元し、再読み込み後も全体一致・画像decode・readyを確認する。内部photoIdだけのJSONを合格にしない。これによりDB構造と利用者向けバックアップの両方を検証する。

コンテキスト・ランダムローカルポートは実行ごとに新規生成。MusicBrainzは既存fixture/合成応答、それ以外の外部通信は拒否。個人記録・既存ブラウザ・公開サイトにはアクセスしない。旧localStorage原文が最後まで変更されないことも確認する。

## スモーク全検証グループ

グループは複数assertを含む。assert総数ではなく、出力されるPASSグループで集計する。

| # | 検証項目 | Chromium |
| --- | --- | --- |
| 1 | v3旧データ移行、ready、seed厳密一致 | PASS |
| 2 | 検索モード・短いprefix・候補選択・入力保持・作品fixture・該当なし | PASS |
| 3 | アーティストfixture・同一ID・全作品ソート・390px幅 | PASS |
| 4 | Listening/Collection保存・メタデータ/発売日・日英・既存記録保持 | PASS |
| 5 | artist欠落ガード・手動補正・追加メタデータ検索・作品モード・30件ページング | PASS |
| 6 | 次ページ失敗時の90件/offset保持・再試行120件・重複なし | PASS |
| 7 | 最終API失敗/再検索・古い応答競合・タブリセット・手動入力・JSエラーなし | PASS |
| 8 | Punisher/Hard Lifeのartist/title/release厳密保存・元Listening/Live保持 | PASS |
| 9 | JSON v3実ダウンロード・全体比較・再読込保持 | PASS |
| 10 | 写真作成/表示・photos参照・編集・写真入りJSON比較 | PASS |
| 11 | 削除後の全体が作成前と厳密一致 | PASS |
| 12 | JSON復元・写真/記録の再読込保持・ready・旧原文保持 | PASS |
| 13 | Search Lab共通コア・credit・ページング・作品モード切替 | PASS |
| 14 | 復元confirm/成功alertのみ・最終JSエラーなし | PASS |

Chromium：最初から最後まで完走、14成功・0失敗・0スキップ。従来94行以降で未実行だったグループ4の保存確認以降、5–8および13もすべて成功。

WebKit：--browser webkitを追加し起動を試行。ブラウザ本体取得済みだが、下記共有ライブラリ不足で起動前失敗。テスト本体は未完走、成功0・assert失敗0・起動環境失敗1・14グループ未確認。全ブラウザ合格とは扱わない。

## 新規問題・分類

- A：初期投入がDB作成後に旧移行元を書き換える問題も発見。初回アプリ起動前の投入に修正。
- B：シェルsandboxではローカルsocket/Node子プロセス起動がEPERM。実行権限を付けた再実行でChromium/Nodeは解消。テスト期待値の変更なし。
- B：WebKitにlibgtk-4.so.1、libgraphene-1.0.so.0、libharfbuzz-icu.so.0、libmanette-0.2.so.0、libhyphen.so.0、libGLESv2.so.2が不足。環境用パッケージhelper・sudoなし、APT索引は空。追検証では公式Dockerイメージも試行したが、コンテナ作成時の容量不足で起動不可。WebKit実行環境を用意した上で再実行が必要（詳細は末尾）。影響はWebKitの検証可否、アプリ不具合の証拠ではない。
- C/D：今回の実行範囲ではなし。アプリ本体の修正なし。

## 回帰検証

| コマンド | 結果 |
| --- | --- |
| python -u tests/browser_smoke.py --browser chromium | 完走、14グループ合格 |
| python -u tests/browser_smoke.py --browser webkit | 起動環境不足で未完走 |
| node --test tests/*.test.cjs | 166成功、0失敗、0スキップ |
| python tests/static_build.py | 5成功、0失敗 |
| node scripts/build-static.cjs | 成功、allowlistの17ファイル生成 |
| python -u tests/static_distribution.py | 完走、12条件＋JS無効化1グループ合格 |

static_distribution.pyはローカルsource/dist（HTML URL/clean URL）、ルート/サブパス、ja 390px/en 1280pxで、3領域CRUD・写真・IDB/JSON・規約/プライバシー・nested 404を確認。公開サイトへの通信/デプロイなし。ビルド成果物distはgit対象外。大容量・保存中断・CAA画像比較・iPhone実機の再検証は変更との関連がないため実施せず。

残存事項：WebKitの14グループは未確認。PR番号・最終HEADはPRおよび作業完了報告を参照。マージは別途承認が必要。


## PR #56 WebKit環境の追確認（2026-11-26）

検証対象HEAD：18223d9f60b7ca2a514049394940faddaa812d2f。
本追確認ではアプリ本体・テストコードを変更していない。Chromium、Node、静的ビルド等の合格済み検証は再実行していない。

### 不足ライブラリと対応パッケージ

| 共有ライブラリ | Debian 13 amd64パッケージ |
| --- | --- |
| libgtk-4.so.1 | libgtk-4-1 |
| libgraphene-1.0.so.0 | libgraphene-1.0-0 |
| libharfbuzz-icu.so.0 | libharfbuzz-icu0 |
| libmanette-0.2.so.0 | libmanette-0.2-0 |
| libhyphen.so.0 | libhyphen0 |
| libGLESv2.so.2 | libgles2 |

ctypes.util.find_libraryで6種とも未検出、dpkg-queryで6パッケージとも未導入を確認。Playwright配布物のinstall-dependencies.shにも対応する6パッケージを確認した。配布物のlib/sys/libを加えたlddでもGTK側でGTK/Graphene/HarfBuzz ICU/Manette/Hyphenの欠落、headless WPE側でHarfBuzz ICU/Hyphenの欠落を確認した。GTK/WPEで使用する依存関係は異なるが、現行PlaywrightのWebKit起動前検査は6種の不足を報告する。

### 導入可否・安全な代替手段の確認

1. ホストはDebian 13、作業ユーザーはuid=1000。管理用の /usr/local/bin/cloud-agent-packages とsudoは存在しない。APTパッケージ索引 /var/lib/apt/lists は空で、管理者所有。通常のシステム依存導入手段を利用できない。
2. 配布物の依存導入スクリプトも非rootではsudo apt-getを使用する。システム領域の直接変更、独自パッケージ配布元の追加、権限設定変更は行わなかった。
3. 管理済みDockerの標準ソケットを利用できたため、ホストOSを変更しない代替として公式 mcr.microsoft.com/playwright/python:v1.62.0-noble を取得した。イメージdigestは sha256:aa81288e738725378becba5b3e06cb0f3a7f012a610e87e8d767a090ea3f740d。
4. リポジトリと既存Playwright Pythonパッケージを読み取り専用mountし、--network none、--cap-drop ALL、--security-opt no-new-privilegesで、同じbrowser_smoke.py --browser webkitの実行を試みた。
5. Dockerのvfsストレージでコンテナ作成時に「no space left on device」となりexit 125。Python/WebKitおよびテスト本体の起動前に停止。約7.9GiBのファイルシステムが100%使用となった。
6. 今回取得したイメージだけを削除し、空き約2.8GiB（使用63%）へ回復したことを確認。Dockerに残るイメージ・コンテナはなし。既存ファイルの削除、ストレージドライバ変更、デーモン再起動、容量拡張は行わず、これ以上の導入は中止した。

### 追確認結果

- WebKitは環境制約により未完走。14グループ未確認、成功0・assert失敗0。今回の追加試行はコンテナ起動環境失敗1件（exit 125）。
- 分類B：ホスト依存導入手段の不足、および代替コンテナの容量不足。再現条件は上記公式イメージを現在のDocker vfs/約7.9GiB環境で起動すること。
- 影響：この環境でWebKitスモークを実行できない。一般公開前のWebKit検証が未完了というテスト基盤上の制約。アプリ本体の不具合を示すものではない。
- 新たなテストassert失敗、C（アプリ不具合）、D（原因未特定）は発見していない。テストは未起動のためWebKitでのアプリ正常性は判断できない。
- 次に必要なのは、WebKit依存が導入済みの環境、または公式Playwrightコンテナの作成に十分な容量を持つ環境。そこで同じ14グループの実行が必要。
- mainマージ、公開環境変更、デプロイなし。追加コミット前に実効author/committerを指定済みGitHub noreplyと照合。
- 追確認ログ：[webkit-environment-followup.log](webkit-environment-followup.log)。初回起動失敗ログは履歴として保持。
