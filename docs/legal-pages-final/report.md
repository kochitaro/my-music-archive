# MLA 一般公開準備：法的文書確定版 実装・検証報告

## A. 対象SHA・PR情報

- リポジトリ：kochitaro/my-music-archive
- 対象：[Draft PR #52](https://github.com/kochitaro/my-music-archive/pull/52)、ブランチ `feat/legal-pages`
- 開始時の最新main：`186a8a02df6b0fcdf2c1767fcaebfa79bf88ab9a`（提示されたSHAと一致）
- 開始時のPR HEAD：`0f396dd115cc0bbd2105a30647ad8dcc86d5cd3e`
- author・committerの実効メールは両方とも指定の `343321005+kochitaro@users.noreply.github.com` であることをコミット前に検証。リポジトリlocal設定を使用。個人メールの出力なし。

## B. 実装内容

| 変更ファイル（最新mainとの差分） | 内容 |
| --- | --- |
| `terms.html` | 日英13条。第3条を承認済み8項へ更新。施行日、問い合わせ窓口を確定 |
| `privacy.html` | 日英14条。Cloudflare配信・解析、保存技術、問い合わせ情報、国外処理、請求等を承認済み構成に更新 |
| `legal.css` / `legal.js` | PR初版から変更なし。言語切替・法的文書専用UIを維持 |
| `index.html` | PR初版のフッター導線・公開向け文言を維持し、mainの復元保護UIと統合 |
| `tests/legal_pages.py` | 14条の期待値、両方向の文書間リンク、現在の復元確認ダイアログ、証跡保存先に対応 |
| `tests/static_build.py` | 法的文書なしのビルドfixtureから法的リンクnavを除外。実サイトの依存検査は変更せず維持 |
| `tests/static_distribution.py` | プライバシーポリシーの期待値を14条へ更新 |
| `docs/legal-pages/report.md` | 初版報告が履歴であることと、本報告への参照を追記 |
| `docs/legal-pages-final/` | 本報告、検証ログ、24枚のスクリーンショット |

利用規約第3条：端末・ブラウザ・プロファイル・オリジン間の非共有、保存制限等による消失、定期バックアップ、復元時の置換と事前バックアップ推奨、書き出しファイルの管理を反映。その他の第1〜12条（第3条を除く）はPR初版とのバイト一致を検証。

プライバシーポリシー：第1条7項追加、第2条維持、第3条の目的・外部画像URL通信追加、第4〜14条を指定文面・順序で実装。MusicBrainz / Cover Art Archiveの既存説明・識別情報・公式リンクを維持。第2条は初版とバイト一致。

施行日は両文書・日英とも2026年12月1日。問い合わせ窓口は運営名・メール・Xのみで、メールとXのリンクを維持。暫定表記および正式／補助窓口の区別は削除。日本語本文を指定どおり反映し、英語は構成・項目数・意味・責任範囲を対応させた。原文にない義務や免責を追加していない。第2条・第8条の参照先は第3・4条、第11条の問い合わせ参照先は第14条。

文書構造・条数・各リスト項目数・施行日・連絡先・暫定表記除去・変更しない条文の一致は[content.txt](content.txt)参照。日本語指定文面と英語訳の目視照合も実施。

## C. 最新mainとの統合結果

履歴を書き換えず、mainをPRブランチにmerge。競合は `index.html` のバックアップ案内1か所。PRの公開向け文言とmainの `restore-recovery` / `restore-result` を両方保持した。

PR #53のビルドスクリプト、およびPR #54を含む `archive-store.js`、`photo-store.js`、`photo-lifecycle.js`、`recovery-export.js` は最新mainとバイト一致。IndexedDB・写真・JSON復元のコード変更なし。本体のUI再設計なし。

## D. 自動テスト結果

| 検証 | 結果・証跡 |
| --- | --- |
| `node --test --test-reporter=tap tests/*.test.cjs` | 166成功、0失敗：[node.txt](node.txt) |
| `python tests/static_build.py` | 5成功：[build-tests.txt](build-tests.txt) |
| `python tests/restore_failure_navigation.py` | 日英各5項目成功。復元拒否後のタブ移動、保存済み記録・写真・復元前コピー、編集draft保護：[restore-navigation.txt](restore-navigation.txt) |
| `python tests/static_distribution.py` | source／dist／clean URL × ルート／サブパス × 日英の12構成、JS無効の法的文書表示成功。3アーカイブのCRUD・写真・IndexedDB・JSON・404を確認：[distribution.txt](distribution.txt) |
| `python tests/legal_pages.py` | Chromium / WebKitの全指定組合せ成功：[browser.txt](browser.txt) |

初回実行時のsandbox制限で子プロセスやHTTPサーバーが使用できなかったため、同じテストをsandbox外で実行して成功。ビルド／配信テストの初回失敗はfixtureの法的リンクと旧11条の期待値に起因し、上記の試験調整で解消した。製品コードのテスト用緩和なし。

合成データと使い捨てブラウザコンテキストを使用し、テスト内の外部通信は遮断。個人のMLA記録にはアクセスしていない。大規模容量・長時間耐久検証は保存処理への変更がないため再実施していない。

## E. 公開用ビルドの検証結果

`node scripts/build-static.cjs` 成功。[build.txt](build.txt)

公開成果物は次の17ファイル（従来13 + 法的文書4）。各ファイルの元ソースとのバイト一致と、固定allowlistへの完全一致を確認。開発資料、テスト、検証証跡、個人の記録、バックアップ等の混入なし。ビルドスクリプトに変更なし。

```text
.nojekyll
404.html
archive-store.js
archive-toolbar.css
archive-toolbar.js
index.html
insights.css
insights.js
legal.css
legal.js
mobile-navigation.js
photo-lifecycle.js
photo-store.js
privacy.html
recovery-export.js
search.js
terms.html
```

## F. ブラウザ検証結果・スクリーンショット

Chromium・WebKit 26.5 × 390px・1280px × 日英で成功。

- 直接URL、日英切替と履歴、本体フッター、MLAへの復帰、規約とポリシーの相互リンクを確認。
- 横スクロールなし、JavaScriptエラーなし、フッターと下部バーの重なりなし。
- 本文16px・既存読み幅と行間を維持。24枚のキャプチャを保存し表示も目視確認。
- 文書のIndexedDB / localStorage / sessionStorage参照を例外にする検証でアクセス試行0。文書往復前後の全ストアと旧localStorageが完全一致。
- 写真付きListening / Collection / Liveの表示とJSON実ファイルの書き出し・再取込・再読込の一致を確認。
- JavaScript無効でも両言語の全条文と戻るリンクを確認。

| 代表画面 | スクリーンショット |
| --- | --- |
| Chromium 390px 日本語利用規約 | [画像](chromium-390-terms-ja.png) |
| Chromium 390px 日本語フッター | [画像](chromium-390-footer-ja.png) |
| WebKit 390px 日本語ポリシー | [画像](webkit-390-privacy-ja.png) |
| WebKit 1280px 英語利用規約 | [画像](webkit-1280-terms-en.png) |
| WebKit 1280px 英語ポリシー | [画像](webkit-1280-privacy-en.png) |

WebKitの不足共有ライブラリは作業領域に公式Debianパッケージを展開し、検証専用ランチャーから参照。リポジトリ・公開成果物・システム設定には含めていない。WebKit自動試験はiPhone Safari実機の代替ではない。

## G. 未確認事項・残存課題

- iPhone Safari実機検証と最終承認が残る。
- 一般公開時に、正式公開オリジンでのCloudflare計測通信・Cookie・送信payload・計測結果を確認する。必要なページビューが計測され、記録・メモ・写真・スコア等の内容が送られず、二重計測がないことを確認する。
- 今回は計測スクリプト追加、Cloudflare設定変更、本番デプロイ、GitHub Pages設定変更、mainマージを行っていない。
- 公式資料を読み、承認文面との不整合は検出していない。Cloudflareはブラウザ保存データを読まないRUM仕様を説明している：[Web Analytics](https://developers.cloudflare.com/web-analytics/)、[RUM beacon](https://developers.cloudflare.com/speed/observatory/rum-beacon/)、[Privacy Policy](https://www.cloudflare.com/privacypolicy/)。これは正式公開環境での実測完了を意味しない。
- MusicBrainz・MetaBrainz privacy・Cover Art Archive・MusicBrainzのCAA説明は公式URLでHTTP 200を確認。Cloudflare公式ページはシェルで403となったが検索コネクタで本文を確認できた。文書内リンク先を変更する必要なし。

## H. iPhone Safari実機検証手順

1. 検証用オリジンでこのPRの `dist` をSafariで開く。個人の記録がある本番オリジンやブラウザ保存データを消さない。端末／iOSバージョン、URL、PR HEADを記録する。
2. 縦向きで本体の言語を日本語にし、最下部の「利用規約」「プライバシーポリシー」から移動する。下部バーとの重なりがないことを確認する。
3. 規約13条、ポリシー14条、施行日2026年12月1日、運営名・メール・Xを確認する。末尾まで読み、横スクロールや文字欠けがないことを確認する。
4. Englishへ切り替え、条番号・施行日・本文・第14条への参照を確認する。規約↔ポリシー、本体への戻るリンク、Safariの戻る／進むを試す。
5. メールリンクで宛先、Xリンクで `@MLArchive_`、外部サービスとCloudflareの各公式リンクの遷移先を確認する。メールやXのメッセージは送信しない。
6. 横向き、ページ拡大、アドレスバー展開／収納でも読みやすさとタップ可能範囲を確認する。
7. 必要なら検証用の合成記録を3種のアーカイブに写真付きで用意し、文書往復後の記録・写真と言語設定維持を確認する。JSONを保存し、検証用データのみで復元を確認する。
8. 結果とスクリーンショットを添えて最終承認する。mainへのマージはその後に行う。

## I. PR・最新HEAD・マージ可能状態

[PR #52](https://github.com/kochitaro/my-music-archive/pull/52)を更新しDraftを維持。提出時の最新HEADとGitHubのmergeable状態は、PR本文と今回のチャット最終報告に記載する（この報告自身を含むコミットのSHAを本文に自己参照させないため）。本体機能・文面の検証対象はこの報告を含む更新コミットの作業ツリー。iPhone Safari実機検証と最終承認後までマージしない。
