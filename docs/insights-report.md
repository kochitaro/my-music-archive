# PR② Insights 本体実装・検証レポート

## 実装前の影響調査

2026-11-06、取得した最新mainは指定の `8cd944b5209f75c4e90175042a31f5391805a1ca`（PR #21統合）。専用ブランチ `feat/archive-insights` で作業した。

単一HTMLの `setScreen` が共通切り替え、`setSection` が3アーカイブ、`tabFilters` が各一覧の選択を管理する。統計の準備中領域は3つとも独立して存在していた。保存済みの作品は `artist`、`genre`（カンマ／全角カンマ区切り）、`tags`（配列または既存文字列）、`label`、Collectionは `store`／`format`、Liveは `artists` 配列と `venue` を使う。日時は共通 `date`、リリースは `release`。年月日だけでなく年のみ・年月のみの保存値があり、日付の欠落も許容される。

既存フィルターは前後空白を除去し、大文字小文字を区別せず記録ごとに重複排除する。Liveでは旧データの公演タイトルから出演者を推測しない。`commitDB` は検証後の新しいDBをメモリへ反映し、追加・編集・削除・JSON復元後に `render` が呼ばれる。この経路に読取専用の統計再描画を接続する。保存・移行・競合処理の変更は不要。

## 変更ファイル

- `index.html`: 既存の統計領域へ描画を接続、準備中表示を撤去。外部CSS/JSを同一オリジンから読み込む。
- `insights.js`: 純粋集計関数、グラフ描画、独立したメモリ上の表示状態。
- `insights.css`: ダークテーマ、水色の棒、凡例、モバイル対応。
- `tests/insights.test.cjs`: 集計・日付境界の11自動試験。
- `tests/insights_browser.py`: 日英・5幅・3アーカイブ、タッチ、追加表示、復元・実フォームの更新、DB非書き込み。
- `tests/archive_insights.py`: PR①の準備中表示の期待値を実統計へ追従。証跡出力先の環境変数を追加し、過去証跡を上書きせず回帰試験できるようにした。
- 本レポート、`insights-evidence/`（画面12枚）、`insights-results/`（検証ログ）。

## 共通集計関数・集計ルール

`counts(records, values)` は空欄を除外、trim＋`toLocaleLowerCase()` で記録内と記録間の分類を同一視する。表示名は既存フィルターと同様に先に出現した名称を保持し、保存値を変更しない。件数降順、名称順、最後に文字列比較で順序を安定させる。順位は同件数でも表示順の連番と画面に明示する。

`aggregate(records, area)` は渡された1アーカイブだけを集計する。総数は配列長。作品アーティストは登録クレジット全体を1名称とし、Liveは `artists` 配列の各名称を1公演に1回まで数える。ジャンル／タグも各分類に1記録1回。文字列タグは既存のカンマ区切り規則を継承する。単一値のレーベル・店舗・フォーマット・会場はその値別の記録数。未設定を除外するため、分類合計と記録総数が一致しない場合がある。

`pie(entries)` は上位10項目と11位以下の合計（その他）を返す。割合は全分類の延べ件数を分母とする。複数値のジャンル／タグにはその説明を常時表示する。ランキングは全分類を保持し、15件ずつ展開・初期件数へ折りたたみできる。

`dateParts(value)` は4桁年、年月、年月日のみを受理し、年0000、範囲外の月日、存在しない日、うるう年の違いを検証する。未設定や不正値を現在日に補完しない。年だけなら年別にのみ含め、年月以上の精度があれば月別にも含める。

`timeline(stats, mode, limit, now)` は端末のローカル年月を基準に、現在月を含む12か月／現在年を含む5年から新しい順に表示する。0件の期間も残す。さらに12か月／5年ずつ最古の有効データまで展開でき、モード変更で初期件数に戻る。未来の期間は表示しない（保存値自体は保持）。日付不明は除外する。

`releaseRows(stats, decades)` は有効なリリース年のみを集計。年別は新しい順・記録がある10年から10項目ずつ展開。年代は `floor(year/10)*10` で集約し、古い順に全項目を表示する。

画面状態はアーカイブ／分類ブロックごとのMapで管理し、localStorageへ保存しない。描画時の集計結果を配列キーのWeakMapで再利用する。既存の保存／復元が検証済みDB・配列を置き換えるため、新しい配列は新規集計される。古いスナップショットはGC対象となる。時期の現在年月は毎回新しく評価する。

## 各アーカイブの項目

| アーカイブ | 数値 | ランキング | 分類分析 | 時期 | リリース |
|---|---|---|---|---|---|
| Listening | 鑑賞作品数、アーティスト数 | 作品数・上位30組 | ジャンル、タグ、レーベル | 鑑賞日・月／年 | 年／年代 |
| Collection | 所有作品数、アーティスト数 | 作品数・上位30組 | ジャンル、タグ、レーベル、購入店舗、既存フォーマット | 購入日・月／年 | 年／年代 |
| Live | 公演数、観たアーティスト数 | 出演公演数・上位30組 | 会場 | 公演日・月／年 | 対象外 |

全登録記録を集計し、アーカイブ側の絞り込みによって統計総数は変わらない。スコア・満足度・横断統計は追加しない。

## グラフ描画方式と理由

ドーナツはCSS `conic-gradient` と中央の円、横棒はCSS幅、年代別縦棒はCSS高さで描画する。追加ライブラリ・外部サービス・Canvas・ホバー操作は不要。現行Safariが対応する標準CSSで、少数項目・1分類・0件も扱える。表示名はtextContentで挿入する。

ドーナツは装飾扱いにし、全スライスの名称・件数・割合をHTML凡例で常時確認できる。横棒にも件数を数値表示する。長い名称は折り返し、年代別は分類ごとに最低幅を確保した内部横スクロールとする。色だけに依存しない。各ボタンは44px以上、`aria-pressed`、グループ名を持つ。

## 画面証跡（390px・Chromium）

全画面スクリーンショット。架空データ、隔離プロファイル、外部HTTPS通信を遮断。実機iPhone Safariの証跡ではない。

| 画面 | 日本語・円／月別 | English・Pie／Monthly | 日本語・ランキング／年／年代 | English・Ranking／Year／Decade |
|---|---|---|---|---|
| Listening | [画面](insights-evidence/listening-ja-pie-monthly.png) | [Screen](insights-evidence/listening-en-pie-monthly.png) | [画面](insights-evidence/listening-ja-ranking-yearly-decade.png) | [Screen](insights-evidence/listening-en-ranking-yearly-decade.png) |
| Collection | [画面](insights-evidence/collection-ja-pie-monthly.png) | [Screen](insights-evidence/collection-en-pie-monthly.png) | [画面](insights-evidence/collection-ja-ranking-yearly-decade.png) | [Screen](insights-evidence/collection-en-ranking-yearly-decade.png) |
| Live | [画面](insights-evidence/live-ja-pie-monthly.png) | [Screen](insights-evidence/live-en-pie-monthly.png) | [画面](insights-evidence/live-ja-ranking-yearly-decade.png) | [Screen](insights-evidence/live-en-ranking-yearly-decade.png) |

分類はジャンル（Liveは会場）をランキングへ変更し、他の分類を円表示に残した証跡。リリース年の年別横棒は初期画面、年代別縦棒は切り替え画面に含まれる。

## 自動検証結果

| コマンド | 結果 |
|---|---|
| `node --test tests/*.test.cjs` | 137件成功、失敗0（新規集計11件を含む） |
| `python -u tests/insights_browser.py` | 日英×320/375/390/430/1280px×3アーカイブ、全シナリオ成功 |
| `MLA_EVIDENCE=/tmp/mla-foundation-evidence python -u tests/archive_insights.py` | 日英×320/390/430/1280px、既存UI・Liveフォーム回帰成功 |
| `python -u tests/pr_b_browser.py` | 保存保護・非同期競合・再試行等70シナリオ成功 |
| `python -u tests/data_preservation.py` | 3領域の削除／編集／写真保存失敗・欠落フィールド・読取失敗・復元保護の全Group 1試験成功 |
| `git diff --check` | 成功 |

初回の制限付き環境ではNodeの子プロセスがEPERM、ブラウザ用ローカルHTTPサーバーがPermissionErrorとなった。許可されたネットワーク付きサンドボックスで再実行した上記結果を採用している。新規ブラウザ試験の初期版には非表示フォームへの入力とLive submitのセレクター誤りがあり、タイムアウトを検出して試験を修正した。これらの失敗を成功件数へ含めていない。

### 必須項目への対応

| 指示の検証番号 | 自動検証 |
|---|---|
| 1〜5 | 純粋集計：独立総数、case/trim、空欄、記録内重複、Live複数出演者 |
| 6〜9 | 順序、30組、0組、Live公演数の単体試験＋ブラウザの30/26組 |
| 10〜16 | 上位10＋その他、分類全件、15件ずつ最終件まで・折りたたみ、独立モード、単一／複数分類の単体・UI試験 |
| 17〜22 | 月12／年5、12／5追加、切り替えリセット、ローカル年月、年のみ、無効日、うるう年・年境界 |
| 23〜27 | リリース年の件数／順序、1999/2000境界、unknown/0000除外、UIの10→20項目、年代別全件 |
| 28〜30 | 日英・3タブ・検索入力と全select値・一覧形式の保持、PR①回帰 |
| 31 | すべての統計操作でStorageのsetItem/removeItem/clearを監視、DB書込0、保存文字列の完全一致 |
| 32 | 実File入力でJSON復元後、表示中の統計件数更新。追加・編集・削除も3領域の実フォームで確認 |
| 33 | Node既存保存保護＋ブラウザ70シナリオ＋データ保全Group 1 |
| 34〜35 | 5幅で文書横溢れなし。モバイル4幅はis_mobile/has_touchでtapによる切り替え・展開 |

## データ保護

DB version 3、保存キー、レコード構造、移行、ジャンル／タグ保存形式、Live artists、JSON仕様、保存失敗保護、Web Locks、競合判定、写真処理を変更していない。集計は入力配列・レコードを変更せず、統計モジュールはStorage・IndexedDB・fetchを参照しない。保存後の表示更新を既存renderへ追加しただけで、統計操作から保存関数へ至る経路はない。mainへの変更、マージ、デプロイは行っていない。

## 未検証事項・制約

実機iPhone SafariおよびWebKitでの実行は未検証。Chromiumのモバイルエミュレーションとタッチ入力検証を実機検証と区別する。実デバイスの保存容量枯渇も未検証（既存の例外注入で検証）。全ての過去PRのブラウザスクリプトを網羅的には再実行せず、本変更に関連する上記回帰群を実行した。

月別は年月が明確な記録だけ、年別は年のみも対象。未来期間は表示しない。名称表記は最初の保存表記に従うため、登録順が変わると同じ分類の表示表記が変わる場合がある。キャッシュは現行の配列置換方式を前提とし、保存方式を将来変える場合は無効化戦略も見直す必要がある。
