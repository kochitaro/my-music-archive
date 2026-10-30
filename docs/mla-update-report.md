# ①開発・検証ルーム向け MLA通常アップデート報告

作業日：2026-10-30。対象：kochitaro/my-music-archive。

## 開始時確認

- fetch済み最新main：`e4e51a43a621b8e40c4c3e55d837c0701a3072a5`。
- 独立ブランチ：`feat/mla-branding-score-editing`。
- PR #8：merged（`ec2f39ca642a16ab3fa8eac4ab150759597efa0a`）、PR #9：merged（開始時main）。コード・既存テストも確認。
- 未マージPR：#6・#7。#8経由で反映済みのため操作・重複マージなし。
- DB version 3。現行キー `my-music-archive-pilot-v03`、旧キー `my-music-archive-pilot-v1`、言語キー `mma-ui-language`。
- DP-01・02：保存候補を分離し、localStorage成功後のみ採用。DP-06：読込失敗時に通常保存・復元を停止し、取得できた元文字列のみ回収。
- 既存構成：Node検索単体テスト＋Python Playwright/Chromiumの7ブラウザスイート。package.jsonやGitHub Actionsのテスト設定はなし。

## 5項目の結果

1. **名称**：メイン画面h1・HTML titleを正確な `My Listening Archive` へ変更。READMEとSearch Labの表示・説明・titleをMLAへ変更。CSS・ロゴ・レイアウトは変更なし。旧報告書の名称は当時の仕様を示す履歴として維持。
2. **Listening**：登録・編集・一覧・詳細・並べ替え・検証メッセージ・読み上げ／操作説明をスコア／Scoreへ変更。5個の星、0.1操作、未評価、4.3以上の `#E08AA1` を維持。
3. **Live**：同様にスコア／Scoreへ変更。5個のハート、4.4以下 `#F07870`・4.5以上 `#E9BC64`、複数出演者を維持。Collectionは評価／Ratingのまま。共用アルバム欄はタブと言語に応じて表示を切替。
4. **アルバム名編集**：既存実装が要件を満たすため機能コードは無変更。MusicBrainz IDの有無にかかわらずmanual-titleは表示・編集可能。保存候補でtitleを更新し、同一レコードを置換。4パターンの合成データで確認。
5. **発売日**：既存実装が要件を満たすため機能コードは無変更。共通の4桁年テキスト・月日select、YYYY／YYYY-MM／YYYY-MM-DD／空文字を使用。月別日数で選択肢を制限し、不正年は保存拒否。月変更で存在しなくなる日は空欄へ戻り、架空の日付は補完しない。

## 実際の変更ファイル

- `index.html`
- `README.md`
- `search-test/index.html`
- `search-test/README.md`
- `tests/search_live_ui.py`（文言期待値のみ）
- `tests/integration_pr6_pr7.py`（文言期待値のみ）
- `tests/mla_update.py`（追加）
- `docs/mla-update-report.md`（本報告）

## 保存・互換性

保存形式の変更・移行なし。DB version、全保存キー、rating名と0–10内部値／0–5表示、artists配列、ID、JSON構造とバックアップ名、CSV列を維持。コード比較で読込保護・migrate・saveDB・saveRecord・編集保存・JSON/CSV/復元・日付処理がmainと一致。search.jsと外部API接続方式は無変更。Search Labは保存APIを使用しないまま。

## 自動テスト

合成データ・隔離Chromiumを使用。外部APIはモックまたは遮断。正式環境の実データは未使用。

変更前：既存ブラウザ7スイートが成功。検索は変更前に `node --test tests/search.test.cjs` が終了コード0（この環境ではファイル単位1件の表示）。変更後に `node tests/search.test.cjs` で個別34件の成功を確認し、search.jsと検索テストがmainから無変更であることも確認。
変更後の既存テストと新規テストは次のとおり。

| 区分 | コマンド | 結果 |
| --- | --- | --- |
| 既存 | `node tests/search.test.cjs` | 34/34 PASS |
| 既存 | `python -u tests/ui_v0322.py` | 6検証群 PASS |
| 既存 | `python -u tests/ui_v0322_followup.py` | 5検証群 PASS |
| 既存 | `python -u tests/browser_smoke.py` | 8検証群 PASS |
| 既存・文言更新 | `python -u tests/search_live_ui.py` | 4検証群 PASS |
| 既存 | `python -u tests/data_preservation.py` | 14シナリオ＋エラー確認 PASS |
| 既存・文言更新 | `python -u tests/integration_pr6_pr7.py` | 日英×4検証群 PASS |
| 既存 | `python -u tests/live_artists_colors.py` | 日英×2検証群 PASS |
| 新規 | `python -u tests/mla_update.py` | 9検証群 PASS |
| 静的 | `git diff --check` | PASS |

追加検証：日英の名称・全領域の詳細／編集／並べ替え／読み上げ、言語とタブ切替、320/390/768pxの名称幅、星4.2/4.3、星・ハートのタップ／ドラッグ／未評価、旧保存キー。Listening/Collection×手動/MusicBrainzのタイトル修正、全DB比較・保存失敗／再試行・一覧／詳細・再読込・旧MMA名JSON往復・空欄拒否。両領域の発売日4精度・再編集／保存／再読込、不正年、2月の日数（1900/2000/2023/2024）、31日から2月変更時の空欄化。

初回ブラウザ起動はsandboxのローカルソケット制限で失敗したため、ネットワーク権限付きの同一環境で再実行。新規テスト作成中の失敗は、無効年のdisabled selectを操作するテスト補助処理と、画面外のスライダーを座標操作したテスト手順を修正。アプリの障害として扱っていない。

## 未解決事項・残存リスク

- iPhone Safari実機、VoiceOver、実際の容量不足は未検証。Chromiumタッチ操作／例外注入の成功を実機PASSとはしない。
- 既存編集処理はlegacy genreをtagsへ統合する。今回変更せず、追加のタイトル保持比較はgenreが空・tagsが既に配列の合成レコードで実施。従来のgenre統合は既存UIテストで回帰確認。
- DP-03・04・07等の包括的復元改修、重複ID、複数タブ競合、写真容量の設計には手を加えていない。
- 検索の取得済み全件整列という既存制約を維持。実APIの最新応答は今回の対象外。

## iPhone Safari最小確認（未実施）

レビュー専用環境・合成データで実施。

1. 日英で名称とスコア、Collectionの評価、VoiceOverの星／ハート操作名。Listening新規・編集、Live新規・編集・詳細・並べ替えを確認。
2. 星4.2/4.3、ハート4.4/4.5、0/5/未評価をタップ／ドラッグして保存・再読込。
3. 両領域で手動／検索由来のアルバム名修正、ID・メモ・写真・タグ保持、一覧と詳細、JSON書き出し／復元。
4. 年入力の数字キーボード・ズーム・スクロールと月日選択。年のみ・年月・空欄・2024-02-29、年変更／月変更後の日欄を確認。

mainへのマージ、正式環境／公開バージョン／Pages URLの変更は未実施。レビュー用PR作成後に停止。次の工程にはユーザーの明示承認が必要。
