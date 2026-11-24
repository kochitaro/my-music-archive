# iPhone入力フォーカス時の自動ズーム対策

調査基点: `main` の `cd55fcb51ac9edbf5f7d9be3545f36a40e9cc274`。

## 原因と実効font-sizeの棚卸し

`index.html` の `:root` は15px、`button,input,select,textarea` は `font:inherit`。
`.field` 自体にはfont-size指定がないため、通常の入力欄は15pxになる。
下表はChromium/WebKitの実行時 `getComputedStyle` と静的なCSS調査の結果。
動的生成、非表示、disabledの要素も監査JSONに含める。

| 対象 | main | 修正後（タッチ端末） | 継承・上書き |
| --- | --- | --- | --- |
| `live-title`, `e-live-title`（公演名） | 15px | 16px | rootから継承 |
| `manual-artist`, `manual-title` | 15px | 16px | rootから継承 |
| `genre`, `tags`, `store`, `price` | 15px | 16px | rootから継承 |
| `memo`, `live-notes`（textarea） | 15px | 16px | rootから継承。Live編集時はmemoを再配置 |
| `sort`, `group` | 15px | 16px | rootから継承 |
| `artist/genre/label/tag/year/release-year/store/venue-filter` | 15px | 16px | rootから継承 |
| `format`, `condition` | 15px | 16px | rootから継承 |
| 生成される日付の年input、月・日select | 15px | 16px | `.date-parts .field` が15pxを直接指定。専用ルールで上書き |
| `ui-language` | 12px | 16px | `.langbar` の12pxを継承 |
| `query` | 16px | 16px | `#search-form #query` の直接指定 |
| `label`, `live-venue`, `e-live-venue` | 16px | 16px | IDによる直接指定 |
| 動的な `live-artists`, `e-live-artists` 内のinput | 16px | 16px | `.live-artist-row input` の直接指定 |
| `date`, `live-date`, `e-live-date`（非表示の元date input） | 16px | 16px | `.field[type=date]` の直接指定 |
| `release-edit`, `rating`, `live-rating`, `e-live-rating`（hidden） | 15px | 16px | フォーカス不可。描画・操作への影響なし |
| 表示項目設定のcheckbox | 13px | 16px | `.display-choice` から継承。ボックス寸法は維持 |
| `import-json`, `album-photo`, `live-photo`, `e-live-photo`（file） | 15px | 15px | 例外。文字編集やソフトキーボードの対象ではなく、既存寸法を維持 |

16px未満の文字入力欄は、iPhone Safariでフォーカス時の自動ズームを誘発する既知の条件と一致する。
実機での再現・修正効果の確認は未実施のため、録画の倍率残留まで直接検証できたという意味ではない。

## 変更

`@media (hover:none) and (pointer:coarse)` 内で入力要素の文字を16pxにする。
画面幅やstandalone判定に依存しないため、横向き・Safari通常表示・ホーム画面Webアプリを同じルールで扱う。
一覧、見出し、ラベル、ボタンの文字サイズは変更しない。デスクトップのマウス操作環境には適用しない。

元の15pxの行高を `1rlh` で参照し、入力の高さを維持する。
selectは日本語フォントとネイティブ描画の差をpaddingで補正する。
固定heightによって2列グリッド内のstretchを失わないようmin-heightを使う。
言語selectは既存のコンパクトな外寸を維持し、WebKitのネイティブ寸法差をfeature queryで扱う。

viewportメタタグとJavaScriptは変更しない。ピンチズームの制限は追加しない。
保存・IndexedDB・JSON復元処理の変更はない。

## 自動試験

実行: `python -u tests/ios_input_zoom.py`。Playwright Python、Chromium (`/usr/bin/chromium`)、対応するWebKitが必要。
`PLAYWRIGHT_BROWSERS_PATH` は環境に応じて指定する。
比較元は上記コミットで固定（`MLA_BASE` で変更可能）。ブラウザは独立した新規コンテキストと合成データを使用し、外部通信を遮断する。

- ChromiumとWebKitで320 / 375 / 390 / 430 / 844pxのタッチ表示、1030pxのデスクトップ表示。
- 英語・日本語、通常表示と `navigator.standalone=true` のホーム画面相当設定。後者はOSのホーム画面起動そのものではない。
- Listening / Collection / Liveの一覧、並べ替え、フィルター、表示項目設定、新規作成、既存編集、出演アーティスト追加。
- 可視かつ操作可能なinput / textarea / selectのフォーカス、文字入力・復元、編集を閉じた後のscale。file / checkbox / hiddenは文字入力試験から除外。
- 修正前後の入力欄の幅・高さを比較（1 CSS pxまでの丸め差を許容）。モーダル・文書の横溢れなし。
- 一覧文字・見出し・ラベルの実効font-sizeの一致、デスクトップの全入力寸法・スタイルの一致。
- 各区分でメモ編集→保存→再編集により入力操作の回帰を確認。

`audit-all.json` は全試験構成の実効font-size・可視性・寸法比較。
PNGは390px幅でのフォーカス状態（OSキーボードは含まない）。

結果: Chromium 156.0.8078.79 / Playwright WebKit 26.5（Linux）の全12構成が成功。既存の `node --test tests/display_preferences.test.cjs` も成功。実行結果は `validation.txt` を参照。

## iPhone実機確認: 未検証

自動試験のWebKitはLinux上のPlaywright WebKitであり、iOS Safariではない。
キーボードの表示、iPhone固有の自動ズーム、閉じた後の倍率残留、実機でのピンチズームは未検証。

実機確認時は、Safari通常表示とホーム画面起動の両方で次を実施する。

1. 表示倍率を通常状態に戻して開始し、フォーカス前の画面を記録する。
2. Liveの公演名・会場・出演アーティスト（追加・既存編集の両方）を順にタップし、キーボード表示中の拡大・文字の欠け・横溢れを確認する。
3. Listening / Collectionのアルバム名・アーティスト・ジャンル・タグ・メモ、店舗・金額・日付、各selectも確認する。
4. キーボードを閉じ、編集画面を閉じた後に元の表示倍率が維持されていることを確認する。
5. 言語・フィルター・並べ替えselect、複数アーティスト追加、横向き、手動ピンチズームも確認する。

実機確認完了までは「iPhoneで自動ズーム解消済み」としない。
mainへのマージ・正式環境への反映はこの作業に含めない。
