# PR④ Insights 円グラフ凡例の配置改善

## 基準と変更内容

2026-11-06、最新mainは指定どおりPR #25統合済みの `be516d7efdbc771da2db78a0ef373d37b609ef99`。GitHub連携で当該SHAのソースを確認し、同SHAから `fix/insights-legend-alignment` を作成した。

凡例をCSS Gridの3列 `10px minmax(0,1fr) max-content` に変更した。

- 左端に色付きマーカー、その右に左寄せの名称。
- 名称と数値の間に12pxの列間隔を確保。
- 件数（割合）は右端・右寄せとし、改行せず一つのまとまりで表示。
- 長い名称は名称列の中で折り返す。数値は名称の先頭行と上端を合わせ、右端を維持する。
- 320pxでも検証データは横並びを保てたため、強制的な2段表示は追加していない。

空白文字・区切り記号・省略表示は追加していない。全3領域・9カテゴリ・日英へ共通適用する。

## 変更ファイル

| ファイル | 内容 |
|---|---|
| `insights.css` | 凡例行のGrid化、マーカー余白・数値の右寄せ |
| `index.html` | Insights JS/CSSの参照バージョンを `20261106-legend-layout-4` へ更新 |
| `tests/insights_ui.py` | 日英×5幅へ拡張し、各凡例行の座標・余白・折り返し・右端揃えを検証 |
| `tests/insights_asset_cache.py` | 新しいアセットURLの取得を検証 |
| 本レポート・`insights-legend-layout-evidence/`・`insights-legend-layout-results/` | 比較画面・検証ログ |

`insights.js`は変更なし。名称・件数・小数第1位の割合・その他・色対応・上位10＋その他・中央の数字・180pxのドーナツ・アーティスト15組・追加表示・時期／リリースグラフは維持する。

DB version 3、保存キー、構造、artists配列、JSON/CSV、写真、保存保護、Web Locks、競合検出、回収処理は変更していない。`index.html`も参照URL以外の処理は変えていない。

## 自動検証

| 検証 | 結果 |
|---|---|
| `node --test --test-isolation=none --test-skip-pattern='historical v3 direct\|official legacy import' tests/*.test.cjs` | 135件成功・失敗0。履歴依存2件は後述 |
| `MLA_INSIGHTS_EVIDENCE=/tmp/mla-layout-after-evidence python3 -u tests/insights_ui.py` | 日英×320/375/390/430/1280px×3領域、成功 |
| `MLA_BEFORE=/tmp/mla-layout-before MLA_INSIGHTS_EVIDENCE=/tmp/mla-layout-before-evidence python3 -u tests/insights_ui.py` | 同じデータ・日英・5幅で基準mainの変更前画面を採取 |
| `python3 -u tests/insights_browser.py` | 日英×5幅、画面／円・ランキング切替、月・年・年代、DB非書き込み、更新回帰が成功 |
| `python3 -u tests/pr_b_browser.py` | 保存保護・Web Locks・競合・非同期処理・再試行等70シナリオ成功 |
| `python3 -u tests/insights_asset_cache.py` | 旧URLの有効なキャッシュがある状態でも新URLのJS/CSSを取得し、保存データを変えず描画できることを確認 |
| `git diff --check` | 成功 |

変更前ソースは上記基準mainの `insights.js` / `insights.css` を `/tmp/mla-layout-before/` に配置した。Gitのシェル接続が利用できないため、ローカルはGitHub連携から取得したソースによる検証スナップショット。提出コミットは実際のmainを親として作成し、対象ファイルだけを反映する。

過去Gitオブジェクト `a0e35db` / `32946ca` を `git show` する既存Node試験2件は、履歴がローカルにないため最終実行で明示的に除外した。元テストは変更せず、137件全成功とは報告しない。

配置UI試験の初回はモバイル日英8ケース成功後、PC幅へ進む際のローカルページ読み込みが30秒でタイムアウトした。再実行では、PCでも長い名称を必ず折り返すという試験条件の誤りを検出したため、折り返し必須の確認を狭い画面に限定した。PCは1行に収まる場合を許容し、全幅で余白・右寄せ・横溢れ・重なりを検証する。製品側の修正は追加せず、最終ログには試験修正後の全ケース完走結果を採用した。

ログ: [単体](insights-legend-layout-results/unit.log) / [配置・UI](insights-legend-layout-results/ui.log) / [変更前採取](insights-legend-layout-results/before.log) / [Insights回帰](insights-legend-layout-results/browser.log) / [保存保護](insights-legend-layout-results/protection.log) / [キャッシュ](insights-legend-layout-results/cache.log)

## 必須検証への対応

- 各凡例行の要素座標を測定し、マーカーの左端、名称の左寄せ、数値の右寄せ、名称と数値の間隔（丸め誤差を除いて12px）、上端揃えを検証。
- 長いレーベル／購入店舗／会場名の複数行折り返し、名称と数値の重なりなし、数値の非分割、要素内と画面外の横溢れなしを検証。
- 全カテゴリの名称・件数・割合を照合し、色と扇形の対応、中央総数、未設定除外、複数分類、その他合算を検証。JSは基準mainから不変。
- アーティスト15→30→全件→15、円／分類ランキング、月／年／年代、アーカイブ画面の状態保持を回帰検証。
- 統計操作でStorageのDBキーへの `setItem` / `removeItem` / `clear` を監視し、DB書き込み0と保存文字列の一致を確認。
- 3領域の実フォームによる登録・編集・削除、JSON復元後の統計更新を確認。
- 保存保護と競合検出は既存70シナリオを再実行。今回、データ保全Group 1等の全過去ブラウザスイートは網羅的には再実行していない。

## 比較証跡

隔離した合成データとChromium。390pxは全3領域・日英、他の代表幅はListening日本語。Collectionのレーベル・購入店舗、Liveの会場は長い名称を含む。前後は同じデータを使用する。

| 画面 | 変更前 | 変更後 |
|---|---|---|
| Listening 日本語 390px | [前](insights-legend-layout-evidence/before-listening-ja-390.jpg) | [後](insights-legend-layout-evidence/after-listening-ja-390.jpg) |
| Listening English 390px | [Before](insights-legend-layout-evidence/before-listening-en-390.jpg) | [After](insights-legend-layout-evidence/after-listening-en-390.jpg) |
| Collection 日本語 390px | [前](insights-legend-layout-evidence/before-collection-ja-390.jpg) | [後](insights-legend-layout-evidence/after-collection-ja-390.jpg) |
| Collection English 390px | [Before](insights-legend-layout-evidence/before-collection-en-390.jpg) | [After](insights-legend-layout-evidence/after-collection-en-390.jpg) |
| Live 日本語 390px | [前](insights-legend-layout-evidence/before-live-ja-390.jpg) | [後](insights-legend-layout-evidence/after-live-ja-390.jpg) |
| Live English 390px | [Before](insights-legend-layout-evidence/before-live-en-390.jpg) | [After](insights-legend-layout-evidence/after-live-en-390.jpg) |
| Listening 日本語 320px | [前](insights-legend-layout-evidence/before-listening-ja-320.jpg) | [後](insights-legend-layout-evidence/after-listening-ja-320.jpg) |
| Listening 日本語 430px | [前](insights-legend-layout-evidence/before-listening-ja-430.jpg) | [後](insights-legend-layout-evidence/after-listening-ja-430.jpg) |
| Listening 日本語 PC 1280px | [前](insights-legend-layout-evidence/before-listening-ja-1280.jpg) | [後](insights-legend-layout-evidence/after-listening-ja-1280.jpg) |

375pxも日英・全領域で自動検証したが、提出画像は上記18枚へ絞った。

## 未検証事項・提出状態

実機iPhone Safari・WebKit・VoiceOverは未検証。Chromiumのモバイル／タッチエミュレーションと実機確認は区別する。端末での実容量枯渇は未検証で、保存保護は既存の例外注入試験による。

レビュー用PRとして提出。①の承認前にマージしない。mainの直接変更・手動デプロイは行っていない。
