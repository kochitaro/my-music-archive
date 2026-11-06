# PR① 画面構成・UI整理 検証レポート

## 基準・変更前の調査

2026-11-06、開始時のorigin/mainは `815acb23e2620810f2946c8012e285e9fedcca6c`。直前履歴は #20 (`815acb2`)、#19 (`2f0a900`)、#18 (`0b3505a`)。専用ブランチ `ui/archive-insights-foundation` で作業。

単一HTML内に検索・一覧・Liveフォーム・保存保護・翻訳を実装する既存構成。3タブは `setSection`、一覧形式は `mode`、アーカイブ別の絞り込み・並べ替えは `tabFilters` が管理する。日英切り替えは既存辞書とMutationObserverを利用。検索パネルと一覧パネルが独立し、文字付きのグリッド／リスト切り替えが見出しの次行にあった。Liveアーティストは専用の複数行入力。保存保護は別レイヤーにある。

## 変更ファイル

- `index.html`: 画面領域、切り替え、アイコン、余白、Live表示文言・項目配置、翻訳。
- `tests/archive_insights.py`: 新規の日英・4幅・3アーカイブUI回帰試験と画面証跡生成。
- `tests/live_artist_total.py`: 新しい表示名に追従。#20の異なるアーティスト総数の検証は維持。
- `tests/live_artists_colors.py`: 文言追従。保存失敗後の旧式の閉じる操作を、現行mainの明示的な破棄・再読み込みに追従。非同期登録の完了待ちを追加。
- 本レポート、`archive-insights-evidence/`: 新規証跡と検証ログ。過去PRの証跡は変更しない。

## 画面構造と状態

タイトル・言語 → 既存3タブ → 共通 `#screen-switch` → `#archive-content` または `#insights-content` → 共通バックアップ／復元・ガイド。

統計は `#listening-insights`、`#collection-insights`、`#live-insights` の独立した領域で、案内のみ。集計・グラフ・ランキングは未実装。

`screenMode` はメモリ上の `archive` / `insights`。初期値はarchive、受理された3タブ操作ではarchiveに戻る。画面切り替えでは再描画・DB保存・フォーム初期化を呼ばない。検索・一覧のDOMを保持するため、一覧形式、並べ替え、絞り込み、検索入力・結果がそのまま残る。`hidden` と `inert` により統計側でアーカイブ操作の表示・フォーカス・操作を無効化。切り替えボタンは `aria-pressed` と `aria-controls` を設定。既存のタブ変更ガードを通過した場合だけ表示をリセットする。

一覧形式は既存modeとイベントを利用し、選択状態にaria-pressedを追加。SVGは装飾扱い、日英のaria-label/titleは言語変更に追従。外部ライブラリ追加なし。

## 余白・サイズの変更値

| 箇所 | 変更前 | 変更後 |
|---|---|---|
| 共通画面切り替え | なし | 上下12px、内側3px、間隔3px、ボタン最小高さ44px |
| 検索・一覧パネル | 上下14px、内側17px | 上下12px、内側16px（モバイル13px維持） |
| 検索見出し下 | 13px | 8px |
| 検索方式の下 | 10px | 8px |
| 検索方式ボタン | 最小38px | 最小44px |
| 一覧形式 | 見出し次行、上10px | 見出し右、上0、44×44px×2、SVG22px |
| 見出しとアイコン間 | 別行 | 8px、長い見出しは折り返し可能 |
| 並べ替え・絞り込みの外側 | 上12px・下8px | 上下8px |
| 空の検索ステータス | 最小15px、上下9px | 空の場合のみ0。結果・エラー時は既存表示 |
| 非表示の検索解除・追加読み込みの親行 | 空行を保持 | ボタン非表示・件数空の場合のみ非表示 |
| ページ下 | PC80px／モバイル65px | 元の値 + env(safe-area-inset-bottom,0px) |

検索入力／検索ボタンの44px高さ、検索グリッドの間隔、エラー・結果・追加読み込み処理は維持。Live追加は見出し下の右側に分け、狭い画面でも見出し・件数・形式アイコンの重なりを防ぐ。

## Live文言と入力順

| 対象 | 日本語 | 英語 |
|---|---|---|
| 新規・編集の日付 | 日付 | Date |
| titleのラベル・新規placeholder | 公演名 | Show Name |
| 複数入力の見出し | アーティスト（任意・複数） | Artists (Optional, Multiple) |
| 各入力ラベル | アーティスト名 | Artist Name |
| 会場 | 会場 | Venue |
| スコア項目名 | スコア | Score |
| 詳細・絞り込み | アーティスト | Artists |
| アーティスト操作 | アーティストを追加／削除 | Add Artist / Remove Artist |

基本情報を日付 → 公演名 → アーティスト → 会場 → スコアに配置。写真・メモは維持。titleとartistsを結合しない。既存のアーティスト行追加・削除・順序・重複・保存仕様、0〜5点／0.1刻みの操作は変更しない。Listening／Collectionのスコアラベルは変更しない。#20の先頭候補は「すべてのアーティスト (異なる登録アーティスト数)」／「All Artists (...)」。個別候補は従来どおり公演件数。

## 画面証跡

すべて隔離したChromiumと架空データ。変更前は基準mainのHTMLを同じデータ・390pxで配信して取得。変更後は320／390／430／1280px、日英、3アーカイブを取得した。実機Safariの画像ではない。

| 表示（390px） | 日本語 | English |
|---|---|---|
| Listening変更前 | [before](archive-insights-evidence/before-listening-ja-390.png) | [before](archive-insights-evidence/before-listening-en-390.png) |
| Listening変更後 | [archive](archive-insights-evidence/archive-listening-ja-390.png) | [archive](archive-insights-evidence/archive-listening-en-390.png) |
| Listening統計 | [insights](archive-insights-evidence/insights-listening-ja-390.png) | [insights](archive-insights-evidence/insights-listening-en-390.png) |
| Collection変更前 | [before](archive-insights-evidence/before-collection-ja-390.png) | [before](archive-insights-evidence/before-collection-en-390.png) |
| Collection変更後 | [archive](archive-insights-evidence/archive-collection-ja-390.png) | [archive](archive-insights-evidence/archive-collection-en-390.png) |
| Collection統計 | [insights](archive-insights-evidence/insights-collection-ja-390.png) | [insights](archive-insights-evidence/insights-collection-en-390.png) |
| Live変更前 | [before](archive-insights-evidence/before-live-ja-390.png) | [before](archive-insights-evidence/before-live-en-390.png) |
| Live変更後 | [archive](archive-insights-evidence/archive-live-ja-390.png) | [archive](archive-insights-evidence/archive-live-en-390.png) |
| Live統計 | [insights](archive-insights-evidence/insights-live-ja-390.png) | [insights](archive-insights-evidence/insights-live-en-390.png) |
| Live新規 | [form](archive-insights-evidence/live-form-ja.png) | [form](archive-insights-evidence/live-form-en.png) |
| Live編集 | [form](archive-insights-evidence/e-live-form-ja.png) | [form](archive-insights-evidence/e-live-form-en.png) |

[証跡一覧](archive-insights-evidence/)には各幅の `archive-{area}-{lang}-{width}.png`、絞り込み中の `after-*`、実行ログも格納。

## 自動検証結果

以下すべて成功。ブラウザは `/usr/bin/chromium`、外部リクエストは遮断またはfixture応答。実行コマンドはリポジトリ直下から `node --test tests/*.test.cjs` または `python3 -u tests/<name>.py`。

| 試験 | 確認内容 | ログ |
|---|---|---|
| Node既存126件 | 保存・移行・draft・検索 | [unit](archive-insights-evidence/unit.log) |
| archive_insights | 日英×4幅×3アーカイブ、初期値・準備中・非表示、タブ復帰、状態保持、DB書き込み0、生文字列不変、アイコンARIA・44px・キー操作、横溢れなし、Live文言・項目順・0.1刻み、統計中の言語変更 | [screens](archive-insights-evidence/screens.log) |
| unified_filters | 全絞り込み・件数・AND・タブ独立・復元・Live CRUD | [filters](archive-insights-evidence/filters.log) |
| live_artist_total | 8組／3公演、重複・空白・大小文字、未設定、ゼロ件選択、DB不変、CRUD・JSON | [total](archive-insights-evidence/live-total.log) |
| live_artists_colors | 複数アーティスト登録・編集・削除、旧記録、失敗・再試行・明示破棄、写真以外のLive入力、スコア境界・色・JSON | [artists](archive-insights-evidence/live-artists.log) |
| data_preservation | 読込／保存／写真の例外注入、原本回収、入力・DB保持 | [preservation](archive-insights-evidence/preservation.log) |
| save_failure_safety | 日英3領域の保存失敗・写真保持・復元失敗・再試行 | [save](archive-insights-evidence/save-safety.log) |
| pr_b_browser | Web Locks、競合、遅延処理、draft・写真、移行競合等70シナリオ | [conflicts](archive-insights-evidence/conflicts.log) |
| browser_smoke / search_live_ui | 検索fixture、検索結果・ページング・失敗再試行・登録、スコア・Live表示、JSON復元 | [search](archive-insights-evidence/search.log) / [UI](archive-insights-evidence/search-live.log) |
| genres_tags | 独立保存・補助・絞り込み・バックアップ復元 | [genres](archive-insights-evidence/genres-tags.log) |
| compact_recovery / draft_visibility | 未保存入力、閉じる／タブ変更の保護、破棄確認、実際の別タブ競合 | [discard](archive-insights-evidence/discard.log) / [draft](archive-insights-evidence/draft.log) |
| backup_guide | 日英ガイド、24モバイル配置、DB書き込み0、保存失敗時入力保護 | [backup](archive-insights-evidence/backup.log) |

最初のNode試行はサンドボックスが子プロセスgitを拒否したため、ネットワーク利用可能な検証実行環境で再実行して126件成功。新規試験の初回は、並べ替えを開くと絞り込みが閉じる既存仕様を試験が考慮していなかったため修正。Live既存試験は現行保存保護に追従し、非同期完了待ちを追加して成功。これらのために製品の保存保護を緩めていない。

## データ・保存保護への影響

DB version 3、保存キー、レコード構造、移行、保存処理、artists配列、genre/tags独立、写真、CSV生成、JSON生成／復元、内部draft、Web Locks、競合検出、元データ回収は変更なし。表示切り替えのみではDBを保存せず、試験でも書き込み0と生文字列一致を確認。既存フォームのID・イベント・値を保持し、アーティスト入力のDOM配置のみ移動。

## 未検証事項・提出

iPhone Safari実機、VoiceOver実機の読み上げ・フォーカス、実際の下部ブラウザUI／セーフエリア、実端末の容量上限、実外部APIとの通信は未検証。Chromiumのモバイル設定はSafari確認の代替とはしない。CSV生成コードは非変更で、今回CSV出力内容の新規の専用試験は追加していない。過去すべての歴史的なブラウザ試験を網羅実行したものではなく、上表の関連試験を実行した。

レビュー用PRをmain宛てに提出し、①開発・検証ルームの承認待ち。承認前のマージ、デプロイは実施しない。PR②の統計本体は対象外。
