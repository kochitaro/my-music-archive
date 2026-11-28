# フッター文言整理（2026-11-28）

一般公開前最終ブラッシュアップ03。実装・自動検証・新規Draft PR・認証付きPreviewのみ。mainマージは行わない。iPhone Safari実機確認と①開発・検証ルームの品質判定を待つ。

## 基準と変更

開始時のGitHub APIとcloneしたmainが一致：SHA `59ba527445533f56919f5a569b9796f5970c0e58`、tree `38f0751b732d20ab73dee68974c990a7ba2d3b40`。ブランチ `fix/footer-copy-cleanup`。PR #60は再開していない。

実行時の変更は `index.html` のフッターHTML、旧フッター専用辞書項目の削除、既存 `refreshCustomControls()` 内の3ラベル更新のみ。規約リンクと同じ更新方式を利用し、新しい翻訳機構は追加していない。MusicBrainzリンクに末尾 `/` を付け、CAAは指定の公式説明ページをリンク化。同一タブ遷移・targetなしという既存フッターリンクの扱いを維持。CSS変更なし。

旧辞書キーはindexの旧フッターだけに使用され、他の実行時ファイルでは未使用。過去の報告書・ログは履歴として維持。

追加ファイルは `tests/footer_copy.py` および本ディレクトリの報告、ログ、検証結果JSON、画像。実際の変更一覧はPRのFiles changedで確認可能。

## 文言

改修前の英語：

> Free to use, with no ads. Album search by MusicBrainz; available artwork from Cover Art Archive. Metadata can be missing or inaccurate. Keep backups; this version does not provide accounts or cloud sync. Search requests are throttled.

改修前の日本語：

> 無料・広告なし。アルバム検索： MusicBrainz; available artwork from Cover Art Archive. Metadata can be missing or inaccurate. Keep backups; this version does not provide accounts or cloud sync. Search requests are throttled.

改修後の日本語（3行）：

```text
アルバム情報：MusicBrainz
ジャケット画像：Cover Art Archive
情報には欠落や誤りが含まれる場合があります。
```

改修後の英語（3行）：

```text
Album metadata: MusicBrainz
Cover artwork: Cover Art Archive
Metadata may be incomplete or inaccurate.
```

指定どおりの文言・2リンク・改行を維持。320pxや200%文字設定では自然な折り返しを許容。

## 比較画像

左が改修前、右が改修後。固定ナビがフッターを隠さないページ末尾で撮影。

- [日本語393px比較](comparison-393-ja.png)
- [英語393px比較](comparison-393-en.png)
- `before-{320,393,1280}-{ja,en}.png`
- `after-{320,393,1280}-{ja,en}-{1,2}x.png`

## 出典・外部サービス条件

2026-11-28に公式公開資料を確認した。

- [MusicBrainz Data License](https://musicbrainz.org/doc/About/Data_License)：coreはCC0、supplementaryはCC BY-NC-SA 3.0。MusicBrainzへのクレジットを削除しない。今回のフッター整理に伴う追加の必須フッター文言は確認されなかった。全取得データのライセンス分類を改めて網羅監査したものではない。
- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API)：非商用利用・User-Agentなどの通信条件は文言の有無とは独立した要件。サービス提供条件を変更しない。
- [Rate Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)：通信制限の説明をフッターから削除しても、既存の制御実装はそのまま維持する。
- [CAA公式説明](https://musicbrainz.org/doc/Cover_Art_Archive)：MusicBrainzとInternet Archiveの共同事業、画像の権利尊重について確認。CAAへのクレジットとリンクを維持。[CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API)の取得経路も変更なし。
- 関連開発資料 `docs/musicbrainz-traffic/report.md` と `docs/legal-pages-final/report.md` を確認。リポジトリ内のMetaBrainz/合意/agreement検索および接続GitHubの関連Issue検索では個別合意原文は見つからなかった。**MetaBrainzとの個別合意内容・非公開の必須表記は未確認**。存在しないと断定していない。原文に追加必須表記がある場合は運営者が根拠を確認し、別途対応を判断する。独断で文言を追加していない。

## 自動検証

- `node --test tests/*.test.cjs`：197件成功。検索通信制御の既存試験を含む。
- `python tests/static_build.py`：6件成功。
- `python tests/footer_copy.py`：source/dist × 320/393/1280 × 日英 × 100/200%の24条件。文言、リンク先、横はみ出しなし、反復切替、既存設定保存後の再読込、T-6正式ブランド寸法・アクセシビリティ見出しを確認。周辺UIのDOM、フッター文字サイズ/色/配置/余白、リンク色を開始mainと比較。
- `python tests/static_distribution.py`：source/dist/clean URL、ルート/サブパス、日英の12条件とJS無効の規約表示。3領域CRUD、写真、IDB、JSON往復、法的リンクと404を確認。
- `preservation.json`：開始mainのindex以外の既存追跡ファイルを全件バイト照合。indexもフッター・専用辞書削除・3ラベル更新を除けば同一であることを確認。バックアップ説明欄、規約、検索・保存処理、T-6/B-4関連、favicon等は不変。

初回の制限環境ではNodeの子git実行がEPERM、Chromium起動も環境制限で失敗した。実装不具合ではなく、実行権限を適用した再実行結果をログとして採用。旧Python5試験の既存失敗（旧データ比較・旧記録検索・旧注入点・旧Grid・非表示旧List）は [既存main照合資料](../brand-logo-02/report.md) とlegacyログを活用し、再実行・無関係な修正をしていない。

## データ保全

隔離Chromiumと合成データのみ。Listening/Collection/Live各2件と写真を開始mainへJSONインポートし、同一originで改修後distへ更新。日英切替・再読込後もarchive/photosストア、その他localStorage、JSON書き出しバイト列が一致。言語設定とそれに付随するsettings/metaの世代・ダイジェスト更新は既存仕様として許容。個人記録・写真は操作していない。実機の個人データに対する比較は行っていない。

## 静的配布

20ファイルを維持。SHA-256一覧は [dist-sha256.json](dist-sha256.json)。docsや検証コードは配布されない。

```text
.nojekyll
404.html
JosefinSans-OFL.txt
archive-store.js
archive-toolbar.css
archive-toolbar.js
brand.css
index.html
insights.css
insights.js
josefin-sans.woff2
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

## 配信・未検証

PR番号・最終HEAD/tree・Preview SHA/tree・デプロイ単位固定URL・配信チェック結果はPR本文と完了報告に記載する（自己参照するコミットハッシュを本ファイル内へ固定しない）。Previewには同一treeを `deploy/preview` へ反映し、既存Cloudflare Pages連携を利用する。

main、GitHub Pages、Cloudflare Production、Access、DNS、正式URLの公開状態は変更しない。Production配信ブランチ `deploy/holding-page` の開始SHAは `3cfb40b0a4a52f652b0873b326fcc7cde88d8222`。Access/DNS管理APIへの更新操作なし。管理画面の全設定値を網羅取得した監査ではない。

未検証：運営者のiPhone Safari実機、VoiceOver実音声、認証後のリモートPreviewの実画面、MetaBrainz個別合意原文。Preview未認証時のAccessリダイレクトとデプロイ成功は別途確認し、ローカルdistと同一treeの自動表示試験で補完する。品質判定とmainマージは別途承認待ち。
