# cbce1e1｜iPhone Safari実機確認の準備・配信報告

2026-11-12 UTC。検証用配信のみ。普段のMLA、GitHub Pages、本番mainは変更していない。Sitesで新規の本人限定サイトを2つ作成し、両方ともバージョン1の配信成功を確認した。iPhone Safariはまだ実施していない。

## iPhoneで使う入口

**[手順・URL・合成JSONをまとめた1ページ](https://mla-safari-cbce1e1.wigglyfrost4096.chatgpt.site/)**

Safariアプリの通常タブで開く。ChatGPTと同じアカウントでサインインする。手順ページは旧版／試作版の実際の画面ラベルに合わせた8ステップで、操作順・期待表示・最終提出ファイル名を記載した。OSのFilesの選択／保存画面はiOSバージョンにより異なる。

| 用途 | URL | アプリのコミット |
| --- | --- | --- |
| 旧版 | https://mla-safari-cbce1e1.wigglyfrost4096.chatgpt.site/old/index.html | `c2c719dd1bd25583402e0a2db948e168018ce34e` |
| 試作版 | https://mla-safari-cbce1e1.wigglyfrost4096.chatgpt.site/new/index.html | `cbce1e1fefd5017e8c9efa84e43a08c4c1c5041f` |
| 別環境の復元先 | https://mla-safari-restore-cbce1e1.wigglyfrost4096.chatgpt.site/new/index.html | `cbce1e1fefd5017e8c9efa84e43a08c4c1c5041f` |

旧版／試作版のscheme・host・portは同じで、localStorageとIndexedDBを引き継ぐ。復元先は別ホストなので別オリジン。既存の普段用MLAとは別に作ったホストであり、既存サイトの配信設定・権限を変更していない。サイトは本人限定のまま公開範囲を広げていない。

## 合成データ

[旧形式JSON](https://mla-safari-cbce1e1.wigglyfrost4096.chatgpt.site/fixtures/mla-safari-legacy.json) は、写真を各記録の`photo`に埋め込んだversion 3形式。Listening／Collection／Liveに各1件。160×160のPNGはそれぞれ青い丸と1、オレンジの四角と2、緑の三角と3。写真のバイト列とSHA-256はすべて異なる。人物・実利用者データ・外部のカバー画像は含めていない。

旧版でJSONを復元し、試作版へ移行する。Listeningのメモだけを `Safari編集1` に変更、再読み込み後に新旧JSONを保存・読み戻し照合し、旧キーを整理する。再読み込み後に同じ記録のメモを `Safari編集1・再読み込み後保存` に変更して保存する。その最終JSONを別オリジンへ復元して再度書き出す。

## コミット確認と配信証跡

`tools/prepare_safari_cbce1e1.py` でGitオブジェクトから直接ファイルを取り出した。アプリ本体は一切書き換えていない。旧版4ファイル＋試作版6ファイル＋復元先試作版6ファイルの16ファイルを元コミットの内容とバイト単位で照合し、SHA-256も記録した。手順ページ・JSON・PNGは別の準備資材として追加した。

- 移行ホストの配信用コミット：`bddfa60b489f0e1b2c85f5b66938ac21634f2eee`
- 復元ホストの配信用コミット：`b84f1eb7876c8152515947a5a7c8eba2b8f3d342`
- 両方ともSitesの保存済みバージョンAPIから上記の配信用コミットを確認し、配信結果APIで`succeeded`とURLを確認した。アプリのコミットと、手順・配信設定を含む配信用コミットは異なる。
- [各アプリファイルのSHA-256](source-manifest.json)、[送信アーカイブ内の照合結果](distribution-verification.json)、[配信結果・保存済みバージョン](deployment-verification.json)。各ホストの`/build.json`にもアプリの完全なコミットIDとファイル指紋を配信している。

この環境にはSitesスキルのローカル補助スクリプト／管理プレビューがなく、通常Gitによる配信用リポジトリの同期とGitコミットからのアーカイブ作成を行い、公式のSites保存・配信APIを使用した。配信後のブラウザDOM操作確認は未実施。非ブラウザのHTTP取得は2ホストとも403（`envoy`, `error code: 1010`）で応答本体を取得できず、公開URLからのファイル再取得による照合はできていない。元Git→送信アーカイブの照合と、保存済みバージョン→配信成功までを確認済み。実機での表示・保存・整理の確認はこれから行う。

## 最後に提出いただくものとCodexの自動比較

実機から次の2ファイルをこの会話へ添付する。

1. 整理・再読み込み・再保存後の `migration-final.json`
2. 別オリジンに復元し、再読み込み後に書き出した `restore-final.json`

Codexがアップロードファイルを取得して実行する：

```sh
python tools/compare_safari_json.py /path/to/migration-final.json /path/to/restore-final.json --report /path/to/iphone-comparison.json
```

期待値は `fixtures/expected-final.json`。全記録・全フィールド・型・件数・写真data URLを比較し、画像本体のSHA-256も出す。Listeningの指定されたメモ変更以外は原本と同じであることを要求する。異なる場合は値や写真本体を大量に出さず、差分の場所を報告する。ブラウザから出力されない旧キーの有無・画面表示・操作成功まではJSON単独で証明できないので、手順5の完了表示と、機種／iOSバージョン／通過した手順も短く報告いただく。

比較器の一致・写真欠落・写真取り違え・再読み込み後保存漏れ・記録欠落・追加フィールドの10ケースを自動検証した。[結果](comparator-tests.log)。旧形式JSONが旧版・試作版の両方の`migrate`検証に通り、内容が変わらないこともNodeで確認した。[自己照合結果](comparator-self-check.json)は合成の期待値を使った比較器の動作確認であり、iPhoneの検証結果ではない。

準備は配信まで完了。実機JSONが提出されるまでiPhone Safariの成否は未判定。
