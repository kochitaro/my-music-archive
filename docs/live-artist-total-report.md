# Live出演アーティスト「すべて」の総数修正

基準: PR #19統合後main `2f0a90071cb5d5664dc09105a1ebe8b6dfb35004`。新規レビュー用PRのみ。マージ・デプロイなし。

## 変更箇所と影響範囲

`index.html` の `countedArchiveFilter()` で、Liveの `artist` フィルターだけ「すべて」の表示数に既存集計Mapのキー数を使用。他の全フィルターは従来どおり `db[section].length` を使用する。

このMapはPR #19の共通フィルター定義から値を読み、前後空白を除去し、大小文字を同一視し、同一記録内でも重複排除する。旧記録のartists欠落・空配列・空白のみは出演者名として数えない。タイトルからの補完はしない。代表表記・保存値を変更しない。

総数は選択中の `(0)` 候補をMapに追加する**前**に取得するため、削除済みの選択肢が残っていても総数には混入しない。

フィルターの値・照合・候補別公演数・未設定件数・候補順・タブ状態・他フィルターには変更なし。「すべて」のvalueは引き続き空文字なので、未設定公演を含む全Live記録を表示する。

変更ファイル:

- `index.html`: 表示用総数の例外のみ（2行追加、表示式1箇所変更）。
- `tests/unified_filters.py`: 既存の合成データ（5公演・異なる出演者2組）に対するLive出演者「すべて」の期待値のみ更新。
- `tests/live_artist_total.py`: 今回の13検証項目をカバーする日英の実UI試験。
- `docs/live-artist-total-evidence/`: 日英画面（390×844、合成データ）。
- このレポートと `docs/live-artist-total-results.txt`: 比較・影響・検証結果。

## 修正前後の比較

3公演、異なる出演者8組（うち1公演はartistsのない旧記録）の合成データ。

| 表示箇所 | 修正前 | 修正後 |
| --- | --- | --- |
| 日本語・出演者すべて | すべての出演アーティスト (3) | すべての出演アーティスト (8) |
| 英語・出演者すべて | All Performing Artists (3) | All Performing Artists (8) |
| Live一覧見出し | (3) | (3) |
| 2公演に出演するArtist A | Artist A (2) | Artist A (2) |
| 出演者未設定 | (1) | (1) |
| 公演年・会場のすべて | (3) | (3) |

[日本語画面](live-artist-total-evidence/all-ja.png) / [英語画面](live-artist-total-evidence/all-en.png)。言語の往復切り替えでも表示・結果を確認。

## 自動検証結果

Python Playwright + ChromiumとNode組込みtest runnerで実施。[実行ログ](live-artist-total-results.txt)。実利用者の保存データは参照せず、合成データを使用。

| 検証項目 | 結果・根拠 |
| --- | --- |
| 1–4 8組、複数公演、個別件数、大小文字・空白 | 日英とも出演者総数8、Artist Aは2公演。公演内・公演間の重複、空文字・空白を検証 |
| 5–6 未設定を総数から除外／すべてで表示 | artists欠落、空配列、空白配列。すべてで全公演を表示、未設定でも該当公演を表示 |
| 7–8 他の総件数を維持 | Live年・会場・一覧は公演数、Listening／Collection全フィルターは記録数 |
| 9 登録編集削除後 | 8→9→9→8。編集前・削除後の選択候補 `(0)` は出演者総数から除外 |
| 10 JSON復元後 | 実インポートハンドラーで8→10、出演者が全て未設定の復元で0。すべてで未設定公演も表示 |
| 11 日本語・英語 | 指定文字列の完全一致、言語往復切り替え、画面保存 |
| 12 保存データの非変更 | フィルター・言語操作前後でlocalStorage生文字列とJSONオブジェクトの完全一致 |
| 13 保存保護・回帰 | 下記の既存検証を実行 |

既存回帰の実行対象:

- `node --test tests/*.test.cjs`: 126件。
- `python tests/unified_filters.py`: 日英、全アーカイブ、AND、タブ状態、モバイル幅、JSON、Live CRUD。
- `python tests/ui_v0322.py`: 既存UI、件数、登録編集削除、詳細、検索UI、並べ替え、グリッド／リスト、JSON。
- `python tests/save_failure_safety.py`: 保存失敗、内部draft、原本回収、非同期破棄保護、日英。
- `python tests/data_preservation.py`: 失敗時の保存値・写真・プロパティ保持、読み取り障害、原本回収。
- `python tests/pr_b_browser.py`: Web Locks・別タブ競合・内部draft・非同期保存／移行競合、70シナリオ。

## 既存仕様への影響・未検証

DB version 3、保存キー、Liveのレコード構造、artists配列、JSONバックアップ／復元、保存保護コードに変更なし。個別出演者の公演件数も同じ集計結果をそのまま使用。保存処理は追加していない。登録・編集・削除・復元後の既存render経路で総数を更新する。

実機iPhone Safariは未検証。今回の日英画面確認はChromiumのモバイル相当設定。PR #19で記録した旧 `live_artists_colors.py` の既存不整合は今回の修正対象外であり、合格扱いにしていない。

①のレビュー承認待ち。mainへの直接変更、マージ、デプロイは行わない。
