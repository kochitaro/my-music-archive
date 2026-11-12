# IndexedDB写真移行 統合PR検証

2026-11-12 UTC。基準main: `c2c719dd1bd25583402e0a2db948e168018ce34e`（PR #35・#36を含む）。提出前にもorigin/mainをfetchし、同じSHAであることを確認。統合元: `cbce1e1fefd5017e8c9efa84e43a08c4c1c5041f`。

## 統合差分と試作からの変更

試作は基準mainの直系であり、`8b205c3`（写真移行）、`92dd604`（旧キー整理・分岐復旧）、`cbce1e1`（移行元指紋）の3コミットを作業ブランチへ統合した。アプリ本体 `index.html`・`photo-store.js`・`photo-lifecycle.js` はcbce1e1と同一。PR #35・#36の表示設定、最初のグループに置く設定操作、Live表示項目を保持する。mainへのマージ・本番反映は行わない。

mainとの差分の中心:

- 写真をSHA-256で識別する変更不可のIndexedDBコピーとして保存。全写真の読み戻しと全記録の照合後にlocalStorageの参照スナップショットを公開する。既存キーは移行だけでは削除しない。
- 持ち運びJSONは写真本体を含む従来のversion 3形式。内部の写真ID・世代・移行元記録は除外する。写真欠落時は書き出し・通常保存を停止する。
- 取り込んだ旧キーの保存文字列の指紋を保持し、新版だけで編集した後も確認条件を満たせば整理できる。別内容の旧キーは保持する。
- 新旧の分岐時は保存と整理を停止。双方のJSONを退避・ファイルから照合し、採用内容を明示選択して復旧する。削除ジャーナルと既存mainと共通のWeb Lockで中断・競合を保護する。

cbce1e1から追加・変更した箇所:

- `tests/indexeddb_integration_ui.py`: 3領域の実フォームCRUD・写真操作・実ダウンロードJSON復元。
- `tests/indexeddb_integration_display.py`: 基準mainとの日英×5幅×3領域比較、表示設定の順序・再読み込み・独立保存。
- `tests/indexeddb_provenance.py`: `MLA_PROVENANCE_EVIDENCE`による証跡出力先指定だけを追加。試作の証跡と今回の証跡を分離。
- 本報告と `indexeddb-integration-evidence/` に今回の実行結果を追加。過去試作の報告は当時の結果として保持。

## 自動検証

隔離した使い捨てChromiumプロファイル、ローカルHTTP、合成記録・生成画像のみ使用。外部HTTPS要求を遮断。本番データにはアクセスしていない。テスト用クロージャ参照・例外注入はインターセプトしたテスト文書だけに追加。初回のサンドボックス内実行はソケット生成が拒否されたため、ローカルサーバー／Chromiumを起動できる実行権限で再実行した。

|検証|結果・証跡|
|---|---|
|写真の移行・読み戻し・参照公開、写真不一致、写真書き込み／参照保存失敗・再試行、中断、別タブ更新、旧mainへのJSON復元、写真欠落時停止|成功。[photos.log](indexeddb-integration-evidence/photos.log)|
|JSON照合・再読み込み条件、整理ジャーナル失敗、削除直後／2キー途中の中断と再開、旧版分岐、復旧中の更新、復旧失敗と再試行、容量不足の例外注入|成功。[recovery.log](indexeddb-integration-evidence/recovery.log)|
|新版だけの追加・編集・写真変更後の整理、未取り込みキー保持、古いJSON拒否、実際の旧mainタブ更新後の保存・整理停止、新旧写真JSONの一致、復旧後の移行履歴再構築、不正な指紋の拒否|成功。[provenance.log](indexeddb-integration-evidence/provenance.log)、[cases.json](indexeddb-integration-evidence/cases.json)|
|Listening／Collection／Liveの画面から登録・編集・写真追加／差し替え／削除・記録削除、元記録の保持、実ダウンロードJSONの復元と再読み込み|成功。[ui.log](indexeddb-integration-evidence/ui.log)|
|基準mainとの日英×320/375/390/430/1280px×3領域のカード・写真・リスト・Insights DOM比較。グループ先頭位置差1px以内。Live設定の変更・順序変更・再読み込み保持、他領域設定保持、記録保存文字列の非変更|成功。[display-final.log](indexeddb-integration-evidence/display-final.log)、[main-comparison.json](indexeddb-integration-evidence/main-comparison.json)|
|Node全回帰（検索・統計・複数レーベル・表示設定・入力検証・下書き等）|158/158成功。[node.log](indexeddb-integration-evidence/node.log)|
|全inline JSと写真モジュールの構文、git diff --check|成功|

再実行（リポジトリルート、Python Playwrightと `/usr/bin/chromium` が必要）:

```sh
python -u tests/indexeddb_photos.py
MLA_RECOVERY_EVIDENCE=docs/indexeddb-integration-evidence python -u tests/indexeddb_recovery.py
MLA_PROVENANCE_EVIDENCE=docs/indexeddb-integration-evidence python -u tests/indexeddb_provenance.py
python -u tests/indexeddb_integration_ui.py
python -u tests/indexeddb_integration_display.py
node --test tests/*.test.cjs
git diff --check
```

整理条件は、最新保存後の再読み込み、現在存在する新旧すべての写真付きJSONの保存とファイル照合、旧キーの移行時指紋一致、保存元の再照合。新版だけを編集したケースは各3件の記録と写真を保持して旧v03キーを削除できた。旧mainタブも更新したケースは、再読み込みしても保存・整理停止が続き、新旧両方の全フィールド・写真をJSONで退避できた。異なる内容を自動統合しない。

## 未完了・未検証

- **DP-08（実容量不足）は未完了。** 今回は例外注入・合成容量上限で保存停止と退避を検証した。実機のディスク枯渇やOS／ブラウザ固有の上限は再現していない。[usage.json](indexeddb-integration-evidence/usage.json) のUTF-16バイト数はlocalStorage文字列の計算値であり、端末の物理使用量ではない。
- **大量写真での性能は未完了。** 少数の合成記録で正しさを検証した。起動・保存・書き出しの待ち時間、ピークメモリ、写真の大量プレビューは未測定。
- **不要写真の容量回収は未完了。** GCは実装していない。写真を差し替え／削除してもIndexedDBの古い写真や失敗試行のコピーは残る。旧キー整理によるlocalStorage削減とは別事項。
- OS強制終了／電源断、ストレージの自動消去、iPhone実機の今回の統合版操作、VoiceOver・実タッチは未検証。Chromeでのページ終了・例外注入をそれらの代替合格とは扱わない。
- Web Lockを共有する基準mainの旧タブを競合検証に使用。ロックを無視する旧版との同時操作を完全には保証しない。整理前に旧タブを閉じる。
- 指紋を持たず、すでに新旧が異なる過去試作データの取り込み履歴は推測しない。旧キーを保持し、双方退避後の明示復旧が必要。

## Safariの扱い・必要な最小追加確認

依頼どおりSafari代表ケースは今回再実施していない。過去の[review-03実機報告](https://github.com/kochitaro/my-music-archive/blob/8313b0df43bc0f6c12b8982a21e199257ebfbc57/docs/safari-cbce1e1/review-03-iphone-safari-report.md)では、提出された移行後・復元後JSONの全フィールドと3写真は期待値との差分0。ただし、実機での旧キー削除成功、アプリ内ファイル照合、再読み込み後の写真表示を確定する証拠は不足している。その結果を本統合版の実機合格と読み替えない。

追加確認が必要な理由はSafari固有のIndexedDB／Web Lock／ファイル入出力の挙動と、旧キー削除の実機証拠が未取得であるため。本体はcbce1e1と同一なので、現時点で全代表ケースの再実施は求めない。①の再レビュー後、必要と判断した場合の最小手順:

1. 既存Safari検証環境が残るなら、まず状態を変えずに旧キー有無と新版記録・3写真の表示を確認する。完了証拠を得るためだけに整理を押し直さない。
2. 新規に確認するなら隔離した検証オリジンと合成3記録を使用。移行→新版だけでメモ編集→再読み込みして記録・写真確認→最新の新旧JSONをファイル保存・アプリで読み戻し照合→旧タブを閉じて整理を1回実行。
3. 整理直後の「旧データの整理が完了しました」を記録し、旧v03キー不在・新版キー存在を確認。再読み込み後の3記録・3写真を確認し、JSONを期待値と比較する。成功表示は現仕様ではパネル最下部にあり、再読み込みで消える。

本PRは①の再レビュー用。mainへのマージ、本番反映、DP-08や性能・GCの完了判定は含まない。
