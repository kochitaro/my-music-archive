# MLA トップ画面・中分類タブ／検索エリア 改修報告

作業日: 2026年11月7日

作業開始時最新main・基準: `1c70fb8d1838b322a71aeab901ad1ad8d6b77bab`（PR #28統合後）

専用ブランチ: `fix/archive-text-tabs-search-hierarchy`

## 変更ファイルと実装

- `index.html`: アーカイブ／統計を背景・外枠なしのテキストタブに変更。非選択は落ち着いたグレー、選択は水色文字と下線。中央寄せ・44px以上の操作領域・aria-pressed等は維持。文字14px（大分類15px）と上下余白の縮小で階層差を付けた。
- 同ファイル: 検索h2をDOMから削除し、それに対する表示更新のみ削除。検索領域には別途日英のアクセシブル名を設定。検索方式に連動した短いプレースホルダーを追加し、入力欄の既存aria-labelと16pxを維持。
- 同ファイル: 検索領域をページ背景に近い`#151a21`、外枠なし、上下8pxへ変更。PCでは3検索コントロールと手動追加を横並び。540px以下では方式選択・右端の手動追加を1行目、入力・検索ボタンを2行目に配置。手動追加はフォーム外のbuttonのまま維持し、検索送信との分離を保つ。
- `tests/browser_smoke.py`: 「placeholderなし」という旧仕様の期待値を変更。
- `tests/search_live_ui.py`: 105件の検索結果を保持したままアーカイブ／統計を往復し、追加API通信がないことを確認。
- `tests/ui_v0322.py`: 削除した検索見出しを参照する配置検証を方式選択の位置へ更新。
- `tests/top_hierarchy.py`: 下線・透明背景・文字サイズ差、日英placeholder、全対象幅での操作領域・重なり・横溢れ、状態保持・DB書込み／APIリクエスト0、画面証跡を追加。
- `docs/top-hierarchy-evidence/`と本文書: 検証結果・変更前後の証跡。

ヘッダー、大分類、グリッド／リスト、並べ替え・絞り込み、登録・編集画面、Live写真操作、検索コア、集計・グラフ・ランキング、保存経路は変更なし。

## 検索欄の案内

| 方式 | 日本語 | 英語 |
|---|---|---|
| アーティスト | アーティストを検索 | Search artists |
| アルバム名 | アルバムを検索 | Search albums |

方式変更と表示言語変更の双方で更新。文字入力後は通常のplaceholderとして見えなくなる。アクセシブル名は既存のアーティスト名／アルバム名を維持。入力文字16px、プレースホルダーはグレーの明示色と不透明表示で視認性を確保。ユーザーズームを禁止するviewport変更なし。

## 画面証跡

合成レコードを使用。変更前は基準コミットのHTMLをローカルブラウザへ配信し、変更後と同じデータで取得。

| 画面（390px） | 日本語 | 英語 |
|---|---|---|
| Listening | [前](top-hierarchy-evidence/before-listening-ja-390.png) → [後](top-hierarchy-evidence/after-listening-ja-390.png) | [前](top-hierarchy-evidence/before-listening-en-390.png) → [後](top-hierarchy-evidence/after-listening-en-390.png) |
| Collection | [前](top-hierarchy-evidence/before-collection-ja-390.png) → [後](top-hierarchy-evidence/after-collection-ja-390.png) | [前](top-hierarchy-evidence/before-collection-en-390.png) → [後](top-hierarchy-evidence/after-collection-en-390.png) |
| Live | [前](top-hierarchy-evidence/before-live-ja-390.png) → [後](top-hierarchy-evidence/after-live-ja-390.png) | [前](top-hierarchy-evidence/before-live-en-390.png) → [後](top-hierarchy-evidence/after-live-en-390.png) |
| Insights（Listening） | [後](top-hierarchy-evidence/after-insights-listening-ja.png) | [後](top-hierarchy-evidence/after-insights-listening-en.png) |
| アーティストplaceholder | [画面](top-hierarchy-evidence/placeholder-listening-artist-ja.png) | [画面](top-hierarchy-evidence/placeholder-listening-artist-en.png) |
| アルバム名placeholder | [画面](top-hierarchy-evidence/placeholder-listening-title-ja.png) | [画面](top-hierarchy-evidence/placeholder-listening-title-en.png) |

[証跡ディレクトリ](top-hierarchy-evidence/)には全5幅×日英×3アーカイブ、Collectionのplaceholder、3種類のInsightsの証跡も収録。

## 自動検証と指示書への対応

Chromium + Playwrightの独立プロファイル。外部通信は遮断し、検索試験はMusicBrainzのfixture応答を使用。

| 必須項目 | 結果・ログ |
|---|---|
| 1–6 大分類維持、中分類の表現・選択・44px、日英 | PASS: `top_hierarchy.log`, `matrix.json` |
| 7–10 見出し削除、方式・placeholder・16px | PASS: `top_hierarchy.log`。独立h2なし、日英各方式のplaceholderと別のaria-labelを確認 |
| 11–15 両方式、整列・追加読み込み、手動追加、エラー・再試行 | PASS: `browser_smoke.log`, `search_live_ui.log`, `ui_v0322.log`。候補選択、失敗ページ再試行、重複なし、検索応答競合も確認 |
| 16–20 画面切替、表示・フィルタ状態、Insights、DB非書込み | PASS: `top_hierarchy.log`, `archive_insights.log`, `insights_browser.log`, `ui_v0322.log` |
| 21 JSON復元・保存保護 | PASS: `save_failure_safety.log`, `search_live_ui.log`, `ui_v0322.log` |
| 22 Live新規・編集への影響 | PASS: `compact_live_ui.log`, `search_live_ui.log`, `ui_v0322.log`。写真操作と失敗時保持・再保存も回帰確認 |
| Node既存試験 | 137件すべてPASS: `node.log` |
| 差分空白チェック | `git diff --check` PASS |

UI試験は、アーカイブ／統計の往復と日英変更後に、検索文字・方式・フィルタ・ソート・グリッド／リスト状態が保持されることを検証。方式変更のみでAPIリクエストが発生しないことも検証した。

| CSS幅 | 日本語／英語 | 対象操作 | コントロールの重なり・画面外配置 | UI操作のDB書込み |
|---|---|---|---|---|
| 320 | PASS | 44px以上 | なし | 0 |
| 375 | PASS | 44px以上 | なし | 0 |
| 390 | PASS | 44px以上 | なし | 0 |
| 430 | PASS | 44px以上 | なし | 0 |
| 1280 | PASS | 44px以上 | なし | 0 |

[実行結果一覧](top-hierarchy-evidence/results.json) / [幅別測定](top-hierarchy-evidence/matrix.json)

DB version 3・保存キー・レコード構造・artists配列・写真形式・保存保護・Web Locks・別タブ競合検出・元データ回収のコード変更なし。UI操作に関するDB書込みの計測は、値が同じ書込みも含めて0であることを確認した。

## 未検証・制約

- **実機iPhone Safari・iOS標準キーボード・VoiceOverは未検証。** Chromiumのモバイルエミュレーションと区別する。検索16pxは算出スタイルで確認し、実機での自動拡大抑制を新たに実証したとは扱わない。
- MusicBrainz本番APIへの疎通は未実行。fixtureで検索・整列・ページング・失敗・再試行を検証。
- 実端末のストレージ容量枯渇は未実行。保存保護は注入例外と既存の復元・競合関連試験で検証。
- 今回対象外の他の過去UIスクリプトは全件実行していない。実行した試験は上記ログ一覧のとおり。

新規レビュー用PRで提出。今回の承認前にマージしない。手動デプロイは実施しない。
