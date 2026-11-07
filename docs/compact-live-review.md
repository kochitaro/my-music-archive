# MLA トップ画面・Live入力操作 改善レビュー

作業日: 2026-11-07 / 基準: 作業開始時の最新main `059e0f6` / ブランチ: `fix/compact-archive-live-input`

## 変更内容・ファイル

- `index.html`: アーカイブ／統計を中央寄せに縮小。検索方式を既定Artistのselectに変更し、入力・検索ボタンと同じ行へ（380px以下は2行）。検索見出し・手動追加を維持。グリッド／リストは44pxの操作領域を維持し、18pxアイコン・装飾削減。3アーカイブ共通。
- 同ファイルのLive部分: アーティスト削除を44×44pxのグレーの×へ。入力欄と高さを一致させ、削除後のフォーカスと最後の空行を維持。新規モーダルの重複h2を削除しaria-labelledbyを設定。
- Live写真: 新規・編集ともプレビュー、変更、削除。ファイル選択を独立したpickerで受け取り、確定した選択のみ既存フォームのFileListへ渡す。現在のファイルを事前に消さないため、キャンセルで選択を失わず同じ写真も選べる。blob URLはプレビュー更新時に破棄。
- 保存済み写真の削除は既存の`saveRecord`→`saveDB`を使用。成功後だけ未保存ファイルを解除し、古い写真も表示しない。失敗時には保存済み写真・選択ファイル・入力を保持。未保存写真のみの削除はファイル選択だけを解除。
- `tests/browser_smoke.py`, `tests/search_live_ui.py`, `tests/ui_v0322.py`: select操作・コンパクト配置へ期待値を更新。Live追加リンクは既存の見出し下の配置を検証。
- `tests/compact_live_ui.py`: 日英・幅・44px・写真操作・削除／変更保存失敗と再保存・DB書込みゼロの追加回帰試験。
- `docs/compact-live-evidence/`: 画面証跡、実行ログ、幅別結果。本文書は提出レポート。

レビューでは、最初のコミットがトップUI・検索、次のコミットがLive操作と追加検証です。

DB version 3、キー、レコード構造、artists配列、写真JPEG保存形式、JSON/CSV、Web Locks、別タブ競合検出、元データ回収、統計集計・グラフ・ランキングのコードは変更していません。UI状態変更で保存APIを呼びません。

## 画面証跡（日英、390px）

| 画面 | 日本語・変更前→後 | 英語・変更前→後 |
|---|---|---|
| Listening | [前](compact-live-evidence/before-listening-ja.png) → [後](compact-live-evidence/after-listening-ja.png) | [前](compact-live-evidence/before-listening-en.png) → [後](compact-live-evidence/after-listening-en.png) |
| Collection | [前](compact-live-evidence/before-collection-ja.png) → [後](compact-live-evidence/after-collection-ja.png) | [前](compact-live-evidence/before-collection-en.png) → [後](compact-live-evidence/after-collection-en.png) |
| Live | [前](compact-live-evidence/before-live-ja.png) → [後](compact-live-evidence/after-live-ja.png) | [前](compact-live-evidence/before-live-en.png) → [後](compact-live-evidence/after-live-en.png) |
| Live新規 | [前](compact-live-evidence/before-create-ja.png) → [後](compact-live-evidence/after-create-ja.png) | [前](compact-live-evidence/before-create-en.png) → [後](compact-live-evidence/after-create-en.png) |
| Live編集 | [前](compact-live-evidence/before-edit-ja.png) → [後](compact-live-evidence/after-edit-ja.png) | [前](compact-live-evidence/before-edit-en.png) → [後](compact-live-evidence/after-edit-en.png) |
| 写真選択・別写真へ変更後 | [日本語](compact-live-evidence/photo-selected-ja.png) | [英語](compact-live-evidence/photo-selected-en.png) |
| 写真削除後・他の入力保持 | [日本語](compact-live-evidence/photo-deleted-ja.png) | [英語](compact-live-evidence/photo-deleted-en.png) |

合成レコード・テスト画像を使用。モーダルは内部スクロールがあり、フォーム上端と写真操作部を別撮影。変更前は基準コミットのHTMLをブラウザへ配信して取得。

## 必須検証結果

Chromium + Python Playwright。外部ネットワークは遮断し、検索はMusicBrainz APIのfixture応答を使用。

| 指示書の項目 | 結果・証拠 |
|---|---|
| 1–8 トップUI・検索・ページング・整列・ソート・フィルタ・DB書込みゼロ | PASS: `browser_smoke.log`, `search_live_ui.log`, `archive_insights.log`, `compact_live_ui.log`。検索方式変更時のAPIリクエスト増加なしも検証 |
| 9–11 アーティスト操作 | PASS: 指定行のみ削除、追加、最後の1行は空行、日英ラベル、44px、入力中心との位置、フォーカス移動 |
| 12–19 写真・保存・重複見出し | PASS: プレビュー、同じファイル再選択、別ファイルへ変更、取消後の他の入力保持、新規保存、編集、削除、削除失敗時のFile・保存写真・入力保持、変更保存失敗後の再保存、旧写真が復活しないこと、重複h2なし |
| 20–24 日英・幅・操作領域・アクセシビリティ | 自動検証PASS: 下表、aria-label/pressed/labelledby、プレビューalt、44px、グリッド操作のキーボード切替。実機VoiceOverは未実行 |
| 25 Node既存試験 | **137/137 PASS**: `pr_a_required.test.log`（全5ファイルを一括実行したログ） |
| 26–29 保存保護・競合・JSON/CSV・写真・入力途中 | PASS: `save_failure_safety.log`, `data_preservation.log`, `draft_visibility.log`, `compact_recovery.log`, `ui_v0322.log`, `backup_guide.log`。注入した保存／読取例外、別タブ競合、回収、JSON復元、CSV、再読込後の永続化を確認 |
| 30 Insights | PASS: `insights_browser.log`, `archive_insights.log`、Node insights試験。空データ、JSON復元、作成・編集・削除後更新も検証 |

[実行結果一覧](compact-live-evidence/regressions.json) / [幅別測定](compact-live-evidence/matrix.json) / [最終390px再確認](compact-live-evidence/final-390.log)

| CSS幅 | 日本語 | 英語 | トップ横はみ出し | 対象操作領域 | UI切替によるDB書込み |
|---|---|---|---|---|---|
| 320 | PASS | PASS | なし | 44px以上 | 0 |
| 375 | PASS | PASS | なし | 44px以上 | 0 |
| 390 | PASS | PASS | なし | 44px以上 | 0 |
| 430 | PASS | PASS | なし | 44px以上 | 0 |
| 1280 (PC) | PASS | PASS | なし | 44px以上 | 0 |

追加で`ui_v0322.py`は320/375/390/768/1030px×日英×3タブを検証。各幅で新規・編集写真操作を実行。最終390pxでは写真ボタンの44px化・日英altを含む最終コードを再確認。

初回のsandbox内試験はHTTPサーバーのsocket権限で失敗したため、環境が許可する実行経路で再実行。Nodeもその経路で全137件PASS。追加試験で発見した入力欄と×ボタンの高さ差を修正。既存UI試験が想定していたLive見出し横配置を現行の見出し下配置へ更新し、Live追加リンクの44px領域も確保して再検証。

## 未検証・制約

- **実機iPhone Safari、iOS標準写真選択画面の実操作、VoiceOverの読み上げは未実行。** Chromiumのfile chooserによる同一ファイル再選択、別ファイルへの変更、選択未確定時の既存File保持を自動検証。iOS実機確認の代替ではない。
- 実端末のストレージ容量枯渇は未実行。保存例外を注入して保護を確認。
- MusicBrainz本番APIへの疎通・実データによる検索は未実行。両検索方式・整列・ページング・エラー・競合する検索応答はfixtureで確認。
- マージ・手動デプロイは実施しない。レビュー承認待ち。
