# ジャンルとタグの完全分離 — レビュー提出

基準: `cde80e2d8bb840b89e6542398b329ca411707b00`（main、PR #17統合後）。専用ブランチ `codex/separate-genres-tags`。mainへの直接変更、マージ、デプロイは行わない。

## 実装前の影響調査

- DB v3の検証は `genre` を文字列/null/欠落として受理。配列genreは従来から拒否される。`parseGenres()` は文字列を半角・全角カンマで分割するため、文字列での複数登録が可能。
- `tags` は文字列・文字列配列・null・欠落を受理。`parseTags()` は配列の各要素をtrim、文字列は半角カンマで分割。これらの読み取り処理・DB検証は維持。
- `mergedTags()` はgenreとtagsを大文字小文字を無視して統合し、編集初期値、サジェスト、詳細、リスト表示、タグフィルター候補と判定に使用されていた。編集保存ではgenreを空にしていた。
- genreフィルターは存在するが非表示。タグ・レーベル等にある件数・未設定・タブ間保持の仕組みをジャンルにも適用できる。
- JSON書き出しはDBの直列化、復元は既存の `migrate()`→検証→保護付き保存。v3は値を変換せず、旧配列形式は従来のID・スコア等の移行規則を適用する。ジャンル・タグへの変換追加は不要。
- `formState()` がフォーム内のinputを列挙するため、新しいgenre入力も既存のdraft・非同期変更検出の対象になる。保存保護の再設計は不要。

## 変更ファイル

| ファイル | 内容 |
| --- | --- |
| `index.html` | 独立入力・保存・サジェスト・詳細/リスト表示・件数付きフィルター・日英表記 |
| `tests/genres_tags.py` | 今回の要件を実フォームで検証、日英の画面証跡生成 |
| `tests/ui_v0322.py` | 旧ジャンル混在仕様の期待値を更新。スコアだけ編集時にも元のgenre/tagsの厳密一致を要求 |
| `docs/genres-tags-report.md` | 本報告 |
| `docs/genres-tags-evidence/*.png` | 日英×Listening/Collectionの入力・候補・詳細・フィルター、計16枚 |
| `docs/genres-tags-evidence/*.log` | 自動検証ログ |

## 保存形式と既存値の保護

DBバージョン3、保存キー、検証、JSON形式は変更しない。新しい候補管理DB・全件移行はない。新規入力／明示編集時のgenreはカンマ区切り文字列、tagsは従来同様の文字列配列。半角・全角カンマで入力し、trimして大文字小文字を無視した重複を除去し、最初の表記を採用する。両項目に同じ文字列を登録できる。

編集を開いた時点の表示値を項目ごとに記録し、その入力値と同じなら更新オブジェクトに項目を含めない。元の配列・文字列、重複、空白、null、欠落を保持する。genreだけ変更した場合もtagsは元の値のまま。既存値の再分類・移動・自動削除は行わない。ユーザーが入力内容を変更した項目のみ通常の入力正規化を適用する。

保存候補は従来と同じ `saveDB()` 経路を通す。候補検証、書き込み後確定、Web Locks、raw競合検出、draft、写真参照、簡潔な保存失敗UI、原本回収、JSON復元処理は変更していない。

## サジェスト・表示・絞り込み

`mergedTags()` を削除。genreは `parseGenres(r.genre)`、tagsは `parseTags(r.tags)` のみを使用。候補はListeningとCollectionの保存済み記録から項目別に生成し、記録ごとの使用頻度順、同頻度は名称順。大文字小文字だけ異なる候補はまとめる。新規値も自由入力可能。選択は該当入力のみを更新し、inputイベントで既存draft検出に連携する。

IME composition中は候補を再描画せず、確定後に更新する。入力に新たなEnter/keydown処理は追加しない。詳細は未設定を「—」として独立表示し、リストでも項目を分ける。フィルター候補・件数・未設定判定はそれぞれの保存値のみを用い、大文字小文字を無視して照合する。未設定値と同名の実データがある場合の衝突回避、選択保持の既存処理を再利用する。

## 自動検証

- `node --test tests/*.test.cjs`: 126件成功。
- `python -u tests/genres_tags.py`: 日英×Listening/Collectionで複数入力、片方だけ／両方未設定、同一文字列、編集・削除、独立候補と候補選択、複数入力中の追加、自由入力、大文字小文字の重複、genre/tag別の未設定フィルター、詳細、320/375/390/430px幅、compositionイベントを検証。未変更項目は文字列／配列・空白・重複・null・欠落を保持。ジャンル追加後も旧タグが厳密一致。保存失敗時に両入力と保存済みDBを保持し、再保存で両方を確定。
- 同試験で実際のJSONダウンロード内容と保存済みDBが一致。再読み込みを伴う旧v3バックアップ、旧配列バックアップの復元でgenre/tagsを保持。v3往復は全データ一致。Liveの既存値も保持。
- `python -u tests/pr_b_browser.py`: 保存保護70シナリオ成功。
- `python -u tests/pr_b_draft_review.py`: 写真/draft境界36件成功。
- `python -u tests/pr_a_browser.py`: 必須項目144ケース、不正データ32ケース、互換性・移行・保存境界等57シナリオ成功。
- `python -u tests/save_failure_safety.py`: 日英×3領域の写真失敗・内部draft/File保持・非同期中の破棄拒否・復元失敗・読めない/未対応DB原本回収が成功。
- `python -u tests/ui_v0322.py`: 既存UI、スコア、件数/未設定フィルター、登録編集削除、Live、JSON/CSV、再読み込みが成功。
- `python -u tests/data_preservation.py`: 書き込み例外・読み取り例外・原本回収・再読み込みの既存データ保全試験成功。
- `python -u tests/search_live_ui.py`: 日英のLive/検索/スコア回帰、JSON往復成功。

ログは [証跡ディレクトリ](genres-tags-evidence/) に同梱。ブラウザーは隔離Chromiumプロファイル、合成データ、外部APIを遮断して実行。過去テストの旧期待値を除き、保護検証を弱める変更はない。

## 日本語・英語の画面証跡

| 領域 | 候補と入力 | 詳細 | フィルター |
| --- | --- | --- | --- |
| Listening 日本語 | [候補](genres-tags-evidence/listening-suggestions-ja.png)・[入力](genres-tags-evidence/listening-input-ja.png) | [詳細](genres-tags-evidence/listening-detail-ja.png) | [フィルター](genres-tags-evidence/listening-filters-ja.png) |
| Listening 英語 | [候補](genres-tags-evidence/listening-suggestions-en.png)・[入力](genres-tags-evidence/listening-input-en.png) | [詳細](genres-tags-evidence/listening-detail-en.png) | [フィルター](genres-tags-evidence/listening-filters-en.png) |
| Collection 日本語 | [候補](genres-tags-evidence/collection-suggestions-ja.png)・[入力](genres-tags-evidence/collection-input-ja.png) | [詳細](genres-tags-evidence/collection-detail-ja.png) | [フィルター](genres-tags-evidence/collection-filters-ja.png) |
| Collection 英語 | [候補](genres-tags-evidence/collection-suggestions-en.png)・[入力](genres-tags-evidence/collection-input-en.png) | [詳細](genres-tags-evidence/collection-detail-en.png) | [フィルター](genres-tags-evidence/collection-filters-en.png) |

候補画面のAmbient/Droneがタグにもあるのは元のタグに保存済みのためで、ジャンルからの流用ではない。詳細画面はジャンルを手動追加しても旧タグが残る例。

## 未対応・未検証

実装保留の要件はない。Safari/iPhone実機、実際の日本語キーボード変換候補の操作、実容量不足は未検証。自動検証はモバイル幅のChromium、compositionイベント、書き込み例外注入による。ユーザーの実DBは取得・変更せず、合成データとリポジトリ内の旧形式fixtureで検証した。

Insights、自動判定/APIジャンル取得、自動移行・一括変換・固定マスタ、保存保護や保存失敗UIの再設計は対象外。①のレビュー承認を待つ。
