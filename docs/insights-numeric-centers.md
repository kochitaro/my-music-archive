# Insights：円グラフ中央を数字のみへ統一

基準main: `eb2917468cd09cd62004344b404033766288d5f6`（PR #23統合後）。

Listening・Collection・Liveの全円グラフで、中央の「作品」「公演」「延べ件数」と英語単位を削除し、総数のみを中央揃えで表示する。例：`12`。凡例の名称・件数・単位・割合は維持する。

変更は中央の単位要素と専用CSSの削除、および既存UI検証の中央全体の文字列チェックへの更新。集計・割合・ランキング・保存データ・保存処理は変更していない。

## 検証

- `node --test --test-isolation=none tests/insights.test.cjs`: 11件成功。
- `python3 -u tests/insights_ui.py`: 成功。日英390px、320/430/1280px、全3領域・全分類で中央が総数の数字だけであること、凡例の単位・割合、中央合計、横溢れなし、ランキング、空／単一／多数分類を確認。
- `git diff --check`: 成功。
- [単体テストログ](insights-numeric-evidence/unit.log) / [UIログ](insights-numeric-evidence/ui.log)

画面は隔離した合成データ・Chromium。実機iPhone Safari／VoiceOverは未検証。保存処理に変更がないため、保存保護の大規模回帰試験は今回は再実行していない（PR #23時点の結果と区別）。

## 画面証跡（390px）

| 画面 | 変更前（PR #23） | 数字のみ |
|---|---|---|
| Listening 日本語 | [前](insights-ui-evidence/after-listening-ja-390.jpg) | [後](insights-numeric-evidence/listening-ja-390.jpg) |
| Listening English | [Before](insights-ui-evidence/after-listening-en-390.jpg) | [After](insights-numeric-evidence/listening-en-390.jpg) |
| Collection 日本語 | [前](insights-ui-evidence/after-collection-ja-390.jpg) | [後](insights-numeric-evidence/collection-ja-390.jpg) |
| Live 日本語 | [前](insights-ui-evidence/after-live-ja-390.jpg) | [後](insights-numeric-evidence/live-ja-390.jpg) |

レビュー用PR。マージ・デプロイは行わない。
