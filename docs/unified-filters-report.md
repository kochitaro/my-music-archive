# 絞り込み統一・全項目件数表示 レビューレポート

作業基準: `0b3505a`（最新main、PR #18統合後）。mainへの直接変更・マージ・デプロイなし。
実利用者のブラウザ保存データは参照せず、既存コードと合成データで調査・検証。

## 変更前の影響調査

- フィルター、候補集計、タブ状態、描画は `index.html` 内。ジャンル・タグ・レーベル・購入店舗には `countedArchiveFilter()` があったが、「すべて」やアーティストには件数がなかった。
- 年はテキスト入力で `startsWith` により照合され、Liveでは無効。Liveのレーベル・タグは無効でも表示された。
- タブ状態はDOMの値から退避する方式。一部だけが未設定用Symbolを扱っていた。今回、全フィルターに同じ値の読み取り・復元を適用。同じタブを再度押す場合にも現在値を退避する。
- `render()` は登録・編集・削除・JSON復元成功後にも呼ばれるため、保存処理を変更せず候補・件数を更新できる。
- Liveの `liveArtists(record)` は文字列配列 `artists` の空白以外のみを返す。タイトルは公演名として別に表示・編集され、旧記録を開く／保存するだけで出演者に変換する規則はない。
- 保存の検証・DB移行・保存キー・Web Locks・競合判定・draft・原本回収は変更対象外。

## 変更ファイル

| ファイル | 変更 |
| --- | --- |
| `index.html` | 共通の定義・候補集計・AND照合、全項目select化、Liveの表示／操作制御、タブ状態保持 |
| `tests/unified_filters.py` | 日英、全項目件数、年、Live旧記録、AND、タブ独立、幅、DB非変更、JSON復元、Live登録編集削除 |
| `tests/ui_v0322.py` | 年入力をselect操作へ変更、新しい件数／未設定表記を期待 |
| `tests/ui_v0322_followup.py` | 同上、購入店舗の「すべて」に総件数を期待 |
| `tests/draft_visibility.py` | 年select操作へ変更。内部draft比較基準をPR #18後のmainへ更新し、その基準では既に撤去済みのJSON回収UIを使わず内部draftを比較 |
| `docs/unified-filters-evidence/*` | 合成データによる日英の全体画面・AND条件画面・全候補一覧JSON |
| `docs/unified-filters-results.txt` | 実行結果 |
| このレポート | 影響調査・仕様・検証・制約 |

## 最終フィルター

| アーカイブ | 順序 |
| --- | --- |
| Listening | アーティスト、ジャンル、レーベル、タグ、鑑賞年、発売年 |
| Collection | アーティスト、ジャンル、レーベル、タグ、購入年、発売年、購入店舗 |
| Live | 出演アーティスト、公演年、会場 |

Liveの出演アーティストは共通の `artist-filter` selectを用途に応じて使い、表示名・アクセシブル名・候補生成元を切り替える。通常の作品アーティストには照合しない。指定外の項目はhidden属性・hiddenクラス・disabledで制御し、照合対象の定義からも除外。他タブの値はLiveに適用されない。既存の並べ替え／グループ分けは維持し、月・日フィルターは追加しない。

## 件数計算と年

- `archiveFilterDefinitions()` が各タブで使う項目と値の読み出しを定義し、集計と照合の双方で共用する。
- `countedArchiveFilter()` は常に `db[section]` 全体を集計。他フィルターの選択には依存しない。
- 前後空白を表示・照合時に取り除き、大文字小文字を同一視。保存データを書き換えず、最初に現れる表記を代表にする。候補は名前順、アーティストは既存同様localeCompare・sensitivity:base。複数値は記録内で重複排除し、候補ごとに1記録1件。
- 全項目で「すべて (総登録件数)」、各候補 `(件数)`、項目別の「未設定 (件数)」を表示。空白・null・欠落・空配列を適切に未設定へ含める。
- 実データと衝突しない未設定option値を生成し、状態ではSymbolとして保持。未設定と同名の保存値も通常候補として扱う。
- 複数フィルターはAND。既存仕様同様、選択中の候補が編集・削除で消えた場合だけ `(0)` として保持し、勝手に「すべて」へ戻さない。未登録の年を通常の候補には追加しない。
- 年は保存値が `YYYY` / `YYYY-MM` / `YYYY-MM-DD` の場合に先頭4桁を使用し、数値の降順。年のみ・年月のみでも年は利用可能。空値・4桁の年を識別できない旧日付文字列は未設定。保存時の日付検証には手を加えず、日付を推測・変換しない。
- 登録・編集・削除・JSON復元後の既存render経路で再集計。

## 旧形式Live

`artists` 配列があれば各出演者を個別に集計・照合する。同一公演の同名・大小文字違い・前後空白違いは1件。

`artists: []`、空白だけの配列、`artists` のない旧記録は出演アーティスト未設定。旧記録は「すべて」「未設定」、公演年、会場から参照可能。公演名・タイトルや旧 `artist` フィールドから出演者を推測しない。Liveのレーベル・タグ・未知の追加フィールドはそのまま保持する。

## 画面証跡

すべて390×844のモバイル相当、合成データ。`*-options-*.json` にnative selectの全候補の値と表示文字列を保存。

| アーカイブ | 日本語 | 英語 | AND条件（日／英） |
| --- | --- | --- | --- |
| Listening | [画面](unified-filters-evidence/listening-ja.png) | [画面](unified-filters-evidence/listening-en.png) | [日](unified-filters-evidence/listening-and-ja.png) / [英](unified-filters-evidence/listening-and-en.png) |
| Collection | [画面](unified-filters-evidence/collection-ja.png) | [画面](unified-filters-evidence/collection-en.png) | [日](unified-filters-evidence/collection-and-ja.png) / [英](unified-filters-evidence/collection-and-en.png) |
| Live | [画面](unified-filters-evidence/live-ja.png) | [画面](unified-filters-evidence/live-en.png) | [日](unified-filters-evidence/live-and-ja.png) / [英](unified-filters-evidence/live-and-en.png) |

## 自動検証

実行環境: Python Playwright + Chromium、Node組込みtest runner。外部APIはfixtureまたは通信遮断を使用。検証結果の詳細は [実行ログ](unified-filters-results.txt)。

| 要件 | 主な検証 |
| --- | --- |
| 1–8 全項目・複数値・重複・すべて・未設定の件数 | `unified_filters.py`、`ui_v0322.py`、`ui_v0322_followup.py`、`genres_tags.py` |
| 9–14 年select、降順、年／年月精度、未設定 | `unified_filters.py`（日英・3タブ） |
| 15–20 Live3項目、不要項目非表示／無効、独立、旧記録保持 | `unified_filters.py`、`genre_filter_tabs.py` |
| 21–23 ANDと件数不変、通常／未設定のタブ状態保持 | `unified_filters.py`、既存UI／genreタブ試験 |
| 24–25 登録編集削除・JSON復元後の更新 | `unified_filters.py`（Live出演者・年・会場）、既存UI試験（作品分類・店舗）、JSON実ハンドラー |
| 26–27 日英・モバイル操作 | 新規試験で320/375/390/430px、既存UI試験の30レイアウト |
| 28 検索・並べ替え・グリッド／リスト・詳細・登録編集 | Node検索fixture、`search_live_ui.py`、`ui_v0322.py`、followup |
| 29 フィルター操作でDB非変更 | 新規試験で全タブ操作前後のlocalStorage生文字列一致、旧記録を含むオブジェクト一致 |
| 30 保存保護 | Node 126件、`save_failure_safety.py`、`data_preservation.py`、`draft_visibility.py`、`compact_recovery.py`、`pr_a_browser.py`、`pr_b_browser.py`、`pr_b_draft_review.py` |

## データ・保存保護への影響

DB version 3、保存キー、レコード構造、移行・JSONエクスポート／インポート、ジャンルとタグの分離、Live複数出演者の保存、Web Locks、別タブ競合、内部draft、保存失敗UI、原本回収の実装は変更なし。フィルター操作はDOMとメモリ上のフィルター状態のみを更新し、saveDBを呼ばない。未知のフィールド、レーベル・タグ、空配列とプロパティ欠落の違いも保持。

## 未対応・未検証

- 実機iPhone Safari／OSによる破棄／実容量不足は未検証。モバイル幅・タッチ設定でのChromium検証であり、Safari実機試験の代替とはしない。
- 古い `live_artists_colors.py` は保存完了前に保存値を読む非同期タイミング問題があり、変更前mainの独立コピーでも `KeyError: artists` を再現した。また、失敗後の編集画面を閉じて他アーカイブへ移れることを前提とし、現在の未保存入力保護と整合しない。新規試験・現行UI試験・保存保護試験で関連機能を検証し、この旧試験は合格扱いにしていない。
- 新しい外部ライブラリ、Insights、複数候補同時選択、日／月フィルター、データ変換、サイト名調整、保存保護の再設計は対象外として未実装。

レビュー用PRのみ提出。①のレビュー承認待ちとし、マージ・デプロイは実施しない。
