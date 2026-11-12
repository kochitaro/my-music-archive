# 提出JSONの自動照合結果：cbce1e1

2026-11-12 UTC。利用者から提出された `migration-final.json` と `restore-final.json` を `tools/compare_safari_json.py` で期待値と比較した。両方とも成功、差分0。

- Listening・Collection・Liveは各1件、全フィールド・型が期待値と一致。
- 3枚の写真data URLと画像バイト列のSHA-256が期待値と一致。
- Listeningのメモは指定した `Safari編集1・再読み込み後保存` と一致。他の内容は合成原本のまま。
- 別環境で復元して書き出されたJSONも、同じ最終期待値と一致。

[比較結果・ファイル指紋](iphone-submitted-comparison.json)。提出された生JSONは重複保管せず、比較結果だけを記録した。

JSONとしての最終データ保持・写真保持・復元後の往復は確認済み。旧キー削除の完了表示、再読み込み時の画面表示、利用機種・iOSバージョンはファイルだけからは判定できず、利用者の追加報告待ち。Safariの全操作が確認済み、または本番反映可能とは判定していない。main変更・マージ・デプロイは行っていない。
