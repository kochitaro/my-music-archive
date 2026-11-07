# MLA 検索方式を直接選択ボタンへ変更する実装・検証報告

作業日: 2026年11月7日

基準: 作業開始時最新main `c0592ee5c0fa31376be019bf8ac19a26f5ddb249`。GitHubでPR #30のマージ済み状態を確認してから、専用ブランチ`fix/direct-search-mode-buttons`を作成。

## 実装と変更ファイル

- `index.html`: 検索方式のselectを、ネイティブbutton 2つを含むrole=groupへ変更。内部値は既存のartist／titleを維持し、type=buttonで検索送信を防ぐ。
- 選択中は水色文字と1px下線、非選択は落ち着いたグレー。背景・外枠・角丸・選択メニュー・アニメーションなし。文字13px、各44px以上、フォーカス枠2px。
- 2行構成を維持。上段左は横並び2ボタン、右は既存の手動追加。ボタンの左右paddingを4px・間隔2pxとし、縮小を禁止するflex指定を使用。320pxでも文字や44px領域を犠牲にせず収めた。検索パネルの余白・背景、下段入力・検索ボタン、中分類等は変更なし。
- 既存のモード変更ハンドラーの接続先をselectからbuttonへ変更。既存`searchMode`を唯一の内部状態として、既存`clearSearch(true)`・`updateSearchMode()`を再利用。別の検索状態管理は追加していない。
- `updateSearchMode()`でactiveクラスとaria-pressedを同期し、言語表示処理の方式判定を選択ボタンに合わせた。選択中の方式を再度押した場合は、結果クリア等の処理より前にreturnする。
- `tests/browser_smoke.py`, `tests/search_live_ui.py`, `tests/compact_live_ui.py`, `tests/top_hierarchy.py`: 旧select操作をbutton操作へ更新。検索回帰では、読み込み済み105件の結果が選択中ボタンの再押下で消えず、APIも増えないことを追加。
- `tests/direct_search_modes.py`: 日英5幅・両アーカイブ、1タップ、連続操作、操作領域・文字実測・重なり、キーボード・状態・言語・入力保持、DB/APIゼロと証跡取得を追加。
- `docs/direct-search-modes-evidence/`と本文書: 変更前後、両選択状態、フォーカス、測定、試験ログ。

## 検索・保存の維持

[差分範囲の静的確認](direct-search-modes-evidence/scope.txt)により、以下の基準mainとのバイト単位の一致を確認。

- `search.js`、`insights.js`、`insights.css`。
- mainスクリプトのモード表示関数より前の範囲（DB・保存保護、検索状態、searchContext、resetSearchView、clearSearch等）。
- アーティスト候補描画からmainスクリプト末尾（候補選択、検索取得、結果表示、追加読み込み、アーカイブ、全登録編集、Live写真、JSON/CSV等）。

したがってAPI問い合わせ、完全一致・別名・表記ゆれ、候補選択、作品取得、Album/EP/Single・発売日整列、重複排除、追加読み込み、再試行、古い応答無効化を変更していない。DB version 3・キー・構造・artists配列・保存形式・Web Locks・競合検出・元データ回収も変更なし。

## 操作仕様

- artist⇔titleは1回のbuttonクリックで同期的に変更。
- 選択時は既存結果をクリア、入力語は維持、placeholderと入力aria-labelを更新。
- 選択中のボタンの再押下は何もしない。
- 言語・アーカイブ／統計の切替でも選択状態と入力を保持。Listening／Collection間は既存の検索状態管理に従う。
- 方式切替のみでAPIリクエスト・レコードDB書込みは発生しない。
- 入力16px・別のアクセシブル名、既存の4種placeholderを維持。

## 必須検証の結果

Chromium + Playwrightの独立プロファイル、合成データ、検索fixtureを使用。

| 指示書項目 | 結果・証拠 |
|---|---|
| A1–3 表示・選択差・5幅 | PASS: `direct_search_modes.log`, `measurements.json`。背景透明、13px、選択下線、文字の実描画範囲、各コントロール境界を確認 |
| A4–6 1タップ・メニューなし・再押下 | PASS。selectはDOMから撤去、type=button。各幅・日英・2アーカイブで200回連続クリックを実行し、毎回選択が1つであることを確認 |
| A7–10 44px・キーボード・focus・aria | PASS。Enter／Spaceで選択、2pxのフォーカス枠、aria-pressedを確認。操作領域の重なり・画面外配置なし |
| B11–16 検索品質・候補・整列・ページング・再試行 | PASS: `node.log`, `browser_smoke.log`, `search_live_ui.log`。完全一致・別名・表記ゆれは既存Node／fixture回帰で確認 |
| B17 検索中方式切替・古い応答 | PASS: `browser_smoke.log`。保留したartist応答をtitle検索後に解放しても新結果へ混入しない |
| B18–20 API通信0・入力保持・日英連動 | PASS: `direct_search_modes.log`, `browser_smoke.log` |
| C21–24 DB0・手動追加・Listening/Collection登録編集・画面切替 | PASS: `direct_search_modes.log`, `top_hierarchy.log`, `ui_v0322.log` |
| C25 Insights | PASS: `insights_browser.log`, `top_hierarchy.log`。作成編集削除後の更新も確認 |
| C26 Live・写真 | PASS: `compact_live_ui.log`, `ui_v0322.log` |
| C27–28 JSON復元・保存失敗保護 | PASS: `save_failure_safety.log`, `ui_v0322.log`, `search_live_ui.log` |
| Node既存試験 | 137件すべてPASS |
| 差分空白チェック | `git diff --check` PASS |

[最終結果一覧](direct-search-modes-evidence/results.json) / [操作領域測定](direct-search-modes-evidence/measurements.json)

追加試験は日英×5幅×2画面それぞれで、方式を交互に切り替え、同じ方式も再押下する200クリックを実行。合計4,000クリック。DB/API計測は値が同じsetItemも書込みとして数えて0。実際に105件取得した検索結果で、選択中ボタンの再押下・統計画面の往復後も全件保持、追加通信なしを確認。

## 初回検証の失敗と再確認

初回の文字幅試験で、Canvasによる推定77.22pxとボタン内容幅76pxの差を検出して失敗した。[初回ログ](direct-search-modes-evidence/direct_search_modes-initial.log)

文字欠けの判定を実際のDOM Rangeの描画幅へ変更し、ボタンがflexで縮まない指定も明示した。その後、全対象幅・日英で文字範囲と44px領域、重なり・画面外配置、連続操作を再検証してPASS。初回失敗を未解決のまま扱っていない。最終UI試験ログは再実行結果である。

## 日英・変更前後の証跡

以下はListeningの代表比較。証跡ディレクトリには、両アーカイブ・日英・全5幅の変更前後を収録。

| 条件 | 変更前 | 変更後 |
|---|---|---|
| 日本語390px | [前](direct-search-modes-evidence/before-listening-ja-390.png) | [後](direct-search-modes-evidence/after-listening-ja-390.png) |
| 日本語320px | [前](direct-search-modes-evidence/before-listening-ja-320.png) | [後](direct-search-modes-evidence/after-listening-ja-320.png) |
| 英語320px | [前](direct-search-modes-evidence/before-listening-en-320.png) | [後](direct-search-modes-evidence/after-listening-en-320.png) |
| Collection・日本語320px | [前](direct-search-modes-evidence/before-collection-ja-320.png) | [後](direct-search-modes-evidence/after-collection-ja-320.png) |
| Collection・英語320px | [前](direct-search-modes-evidence/before-collection-en-320.png) | [後](direct-search-modes-evidence/after-collection-en-320.png) |

選択状態比較（日本語320px）: [アーティスト](direct-search-modes-evidence/selected-artist-ja-320.png) / [アルバム名](direct-search-modes-evidence/selected-title-ja-320.png)

選択状態比較（英語320px）: [Artist](direct-search-modes-evidence/selected-artist-en-320.png) / [Album Title](direct-search-modes-evidence/selected-title-en-320.png)

フォーカス: [日本語320px](direct-search-modes-evidence/focus-ja-320.png) / [英語320px](direct-search-modes-evidence/focus-en-320.png)

全5幅の各選択状態とフォーカスの証跡も収録。320pxでも上段左右を維持できたため、補助操作の配置変更や文字サイズ・操作領域の削減は不要だった。

## 未検証事項

- **実機iPhone Safari・iOSキーボード・VoiceOverは未検証。** Chromiumのモバイルエミュレーションによる成功と区別する。selectをなくしたことはDOMで確認できるが、実機の描画・読み上げを確認済みとは扱わない。
- MusicBrainz本番API疎通は未実行。既存fixture／Node試験で検索品質・リクエスト仕様を回帰確認。
- 実端末の容量枯渇は未実行。保存例外注入とJSON復元で保護を検証。
- selectを対象にした過去の`search_mode_light.py`等は旧UI専用のため未実行。今回実行した試験は結果一覧に記載。

新規レビュー用PRで提出。今回の承認前にマージしない。手動デプロイは行わない。
