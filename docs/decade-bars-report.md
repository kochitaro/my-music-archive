# リリース年代別 横棒グラフ統一 検証報告

- 指示日・実施日: 2026-11-18
- 対象: kochitaro/my-music-archive
- 着手時main: `210ccde7d4a94771a0d6953515410128bbe7df3c`
- 専用ブランチ: `fix/insights-decade-horizontal`
- レビュー: ①開発・検証ルーム #3。承認前のマージ禁止。マージ・手動デプロイ未実施。

## 変更

Listening / Collectionの年代別を既存の `bars()` で描画し、年別と同じラベル・件数・背景・7pxの横棒・配色・余白に統一した。全件を縦に並べ、ページ送りは追加していない。年代の数値で降順に並べ、日本語は「年代」、英語は「s」を付加した。

10年単位の集約・件数の加算・不明年の除外・最大件数を分母とする比率は従来どおり。年別の降順・10件単位のページ送りは維持。年代専用の縦棒生成処理と3種類の専用CSSだけを削除した。他での参照がないことを確認した。JS/CSSのクエリを更新し、旧資産キャッシュの回帰試験も更新した。

本体の差分は `insights.js` / `insights.css` と `index.html` の資産バージョンのみ。localStorage・IndexedDB・バックアップ/復元・データ構造・保存保護・検索の処理は変更していない。

## 検証結果

隔離Chromium（/usr/bin/chromium）、外部HTTPリクエスト遮断、合成データのみ。本番記録へのアクセス・変更なし。iPhone相当の幅とタッチ設定であり、実機iPhone Safariでの試験ではない。

| 試験 | 結果 | 証跡 |
|---|---|---|
| Node全件 | 165 / 165成功 | [node-tests.log](decade-bars-evidence/node-tests.log) |
| 新規レイアウト・集計比較 | 6幅 × 日英 × 7ケース × 2領域 = 168条件 | [layout.log](decade-bars-evidence/layout.log)、[各行の実測値](decade-bars-evidence/layout-results.json) |
| 既存Insights回帰 | 5幅×日英、3領域、全項目成功 | [insights-regression.log](decade-bars-evidence/insights-regression.log) |
| 資産キャッシュ | 成功 | [asset-cache.log](decade-bars-evidence/asset-cache.log) |
| 現行保存保護 | バックアップ原本一致、IndexedDB読出障害、localStorage書込失敗、復旧・再読込成功 | [current-save-protection.log](decade-bars-evidence/current-save-protection.log) |

新規試験の画面幅は320 / 375 / 390 / 430 / 768 / 1280px。各幅・日英・両領域で以下を確認した。

- 1年代（最大件数1）、複数年代、12年代、60対1の偏り、同件数、不明年を含む、0件。
- Collectionは原則Listeningの半数のレコードで独立集計を検証。12年代ケースは両領域とも全12年代を表示。
- 着手時mainのJSを別名でロードして集計件数を照合。表示順だけ数値の降順に変更。
- ラベル・数値の非クリップ、各行とパネルの横スクロールなし、ページ外へのはみ出しなし。
- inline幅と実測幅の両方で最大件数に対する比率を検証（実測幅の丸め許容0.5%）。
- 年別、他カテゴリ、LiveのDOM全体が基準mainと一致。
- Archive/Insights、Listening/Collection/Live、日英の切替後も年代選択を維持。
- 試験中の記録保存キーへの書き込み0、保存JSONがバイト単位で一致。

既存Insights回帰で年別/年代別、ランキング/円グラフ、ページ送り、月別/年別、アーティスト・タグ等、空データ、実際のJSON復元、フォーム経由の追加・編集・削除後の再集計を検証。再読み込みでは従来どおり初期表示は年別で、選択を記録データへ永続化する変更はない。新規試験はケースごとの再読み込み後も集計表示を検証した。

320pxの日英・両領域はすべて成功。最大60件のケースは2020年代60、2010年代3、2000年代2、1990年代3、1970年代1で、棒は100%、5%、3.333…%、5%、1.666…%。件数は棒の外に配置され、短い棒でも読める。

## 比較画像

390px・日本語・同じ合成データ・同じ画面幅で変更前後を保存。パネル全体画像に加え、変更後のページ全体画像も保存した。

| 対象・条件 | 変更前 | 変更後 | 390px全画面 |
|---|---|---|---|
| Listening 件数偏り | [before](decade-bars-evidence/before-listening-skewed-ja-390.png) | [after](decade-bars-evidence/after-listening-skewed-ja-390.png) | [full](decade-bars-evidence/full-listening-skewed-ja-390.png) |
| Collection 件数偏り | [before](decade-bars-evidence/before-collection-skewed-ja-390.png) | [after](decade-bars-evidence/after-collection-skewed-ja-390.png) | [full](decade-bars-evidence/full-collection-skewed-ja-390.png) |
| Listening 12年代 | [before](decade-bars-evidence/before-listening-12-decades-ja-390.png) | [after](decade-bars-evidence/after-listening-12-decades-ja-390.png) | [full](decade-bars-evidence/full-listening-12-decades-ja-390.png) |
| Collection 12年代 | [before](decade-bars-evidence/before-collection-12-decades-ja-390.png) | [after](decade-bars-evidence/after-collection-12-decades-ja-390.png) | [full](decade-bars-evidence/full-collection-12-decades-ja-390.png) |

320px日英・両領域、390px英語、1280px日本語のパネル画像も同じ証跡ディレクトリへ保存。

## 追加で確認した旧試験の既存失敗

要求されたNode全件・Insights回帰と、現行の保存保護試験は成功した。一方、追加実行した以下の旧試験は成功していない。今回変更していない基準mainの別チェックアウトでも同一箇所で再現したため、このPRでは保存系や古い試験の修正へ範囲を広げていない。

- `tests/data_preservation.py`: `backup(page) == seed` の比較で失敗。[変更後](decade-bars-evidence/data-preservation.log) / [基準main](decade-bars-evidence/baseline-data-preservation.log)
- `tests/save_failure_safety.py`: 非表示の入力欄の操作でタイムアウト。[変更後](decade-bars-evidence/save-protection.log) / [基準main](decade-bars-evidence/baseline-save-protection.log)

これらは旧保存キー・旧画面を前提とする試験。現行の保護は `tests/remove_photo_maintenance.py` で別途検証した。既存失敗を含めて全試験成功とは扱わない。

## 再実行

リポジトリルートから実行する。

```sh
node --test --test-reporter=tap tests/*.test.cjs
python -u tests/insights_browser.py
python -u tests/insights_asset_cache.py
python -u tests/remove_photo_maintenance.py
git archive 210ccde7d4a94771a0d6953515410128bbe7df3c -o /tmp/mla-before.tar
mkdir -p /tmp/mla-before
tar -xf /tmp/mla-before.tar -C /tmp/mla-before
MLA_BEFORE=/tmp/mla-before python -u tests/insights_decades.py
```

既存ブラウザ試験は既存証跡パスへ画像を出力するため、検証時の生成差分は復元し、このPRでは新規証跡だけを提出している。
