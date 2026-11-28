# ブランドロゴ正式採用・最終整理：T-6

2026-11-28。運営者の第1〜7次の検討・iPhone Safari実機評価と正式採用指示に基づき、アプリヘッダーをT-6に固定した。一時比較機能を完全撤去し、認証付きPreviewで最終確認できる状態にする。mainへのマージ・本番反映は行わない。

## リビジョンと配信範囲

|作業開始時|SHA / tree|
|---|---|
|main SHA|`6fef37adaf6d96a7087ea474aef65546159bdb01`|
|main tree|`fbdc2bcfd8bf06835a4fea74cdba45c3a020cd40`|
|PR HEAD|`1504a21fe5f26f13230dde8b6bd2988e6b377db8`|
|Preview SHA|`45885e9fadac51ef52e6108e8234a2deb2fde7db`|
|共通tree|`222755c2ec9d0ba6df023e759faffc37feb9d2dc`|

リモート・ローカルの最新状態を照合し、既存`feat/brand-logo-c1`・PR #60を継続。[第7次報告](../brand-logo-02-round7/report.md)を基準とした。最新PR HEAD/tree、Preview SHA/tree、デプロイ単位の固定URLと成功チェックはPR本文・最終回答に記載する（報告自体のコミットSHAの自己参照を避ける）。

通常Preview: https://deploy-preview.my-listening-archive.pages.dev/

以前の`?logo-compare=1`も同じT-6のみを表示する。認証前のPreviewがCloudflare Accessへ302となることをデプロイ後に確認する。認証設定を変更しない。

開始時Production配信ブランチ`deploy/holding-page`は`3cfb40b0a4a52f652b0873b326fcc7cde88d8222`。main・同Productionブランチ・GitHub Pages・Access設定・正式URLの公開状態を変更しない。author/committerはCodex、`343321005+kochitaro@users.noreply.github.com`で、個人メールを公開コミットへ含めない。

## 正式仕様と採用理由

|項目|正式仕様|
|---|---|
|表示文字列・見出し名|My Listening Archive|
|書体|Josefin Sans 2.001、Regular 400|
|文字サイズ|`1.466666667rem`（通常ルート15px時22px相当）|
|字間・行高|.02em・1.25（通常0.44px・27.5px）|
|配置|水平・垂直中央|
|文字色・背景色|#f0f1f3・#11151b|
|ブランド領域|通常40px、固定高でなくmin-height|
|上下余白|上5px・下16px|
|シンボル・配置領域|なし、文字とのgapなし|
|配布|ローカルWOFF2、font-display:swap、既存フォールバック|

他のUIのシステムフォントは維持。remにより利用者の文字拡大へ追従し、必要時は折り返して領域を拡張する。文字サイズ・色・上下余白の追加調整を行っていない。

シンボルの魅力と日常利用のヘッダーの適切さを分けて判断した。シンボルなし・控えめな文字サイズ・中央寄せが画面全体と調和し、正式名称に親しみやすさと個性がある。略称のみの寂しさを避け、作品や利用者自身の記録を主役にするためT-6を正式採用する。これをもって今回のヘッダー検討を終了する。

## 第7次T-6との表示一致・各幅の実測

開始HEADから旧21ファイルの静的アプリを一時領域へ再構成し、同じブラウザ・倍率・言語・幅・データ条件で最終版と比較した。source/dist×6幅×日英の24条件すべてで、位置、文字サイズ、幅、行高、書体、ウェイト、字間、色、ブランド領域、上下余白、後続ボタン位置が数値一致。ブランド領域画像のRGB差分は全条件0ピクセルだった。

[同一倍率の第7次／正式版393px比較：日本語](parity-393-ja.png) / [英語](parity-393-en.png)

[全実測値・AX tree](metrics.json)。以下はsourceの文字行ボックス（px）。日英・source/distで同値。ブランドy=24、高40、文字y=30.25、高27.5、後続の大分類ボタンy=80。上下余白5/16px。

|画面幅|文字サイズ|開始x|表示幅|水平中心|
|---|---|---|---|---|
|320|22|51.11|217.78|160.00|
|375|22|78.61|217.78|187.50|
|390|22|86.11|217.78|195.00|
|393|22|87.61|217.78|196.50|
|430|22|106.11|217.78|215.00|
|1280|22|531.11|217.78|640.00|

通常は全幅1行で、文字欠落・横はみ出し・不要なシンボル領域なし。200%の文字設定（ルート30px、実文字44px）では必要に応じて折り返し、ブランド領域が伸びて文字を切り捨てない。フォント取得を遮断した320pxでも、通常／旧比較URL・source/distで正式名称とアクセシブル名を維持する。

|幅|日本語トップ画面|英語トップ画面|
|---|---|---|
|320|[画像](top-320-ja.png)|[画像](top-320-en.png)|
|375|[画像](top-375-ja.png)|[画像](top-375-en.png)|
|390|[画像](top-390-ja.png)|[画像](top-390-en.png)|
|393|[画像](top-393-ja.png)|[画像](top-393-en.png)|
|430|[画像](top-430-ja.png)|[画像](top-430-en.png)|
|1280|[画像](top-1280-ja.png)|[画像](top-1280-en.png)|

[フォント失敗・320px](default/fallback-source-320-normal.png) / [旧比較URLでも同じ表示](default/fallback-source-320-query.png)

## 比較機能・HTML/CSSの完全撤去

- `brand-compare.js`を削除し、HTMLのscript読み込みと静的配布許可リストから除外。
- 比較パネル、候補切り替え、Preview判定、選択状態、スクロール位置補正は同スクリプトとともに撤去。
- brand.cssから候補data属性セレクター、候補用CSS変数、略称の出し分け、パネルCSS・狭幅専用CSSを削除。
- h1の2spanを除去し、`<h1 id="page-heading" tabindex="-1">My Listening Archive</h1>`へ簡潔化。正式名称が自然なアクセシブル名となるため重複したaria-labelも不要となった。
- brand.cssはローカル@font-faceと正式な.brand／h1の設定だけ。HTMLのCSSキャッシュ値を更新。

公開HTML/CSS/JS全体を走査し、旧比較スクリプト名・パネル・候補data属性・略称用class・候補CSS変数・比較クエリー処理の残留0。単なる非表示化ではない。比較用SVGや隠れた候補HTMLも存在しない。

各幅・日英・source/distで旧クエリー2種類の48条件を確認し、通常T-6と画像一致・パネルなし・比較JS取得なし。加えてPreviewブランチ、デプロイ単位、localhost、本番想定、GitHub Pages想定（サブパス）の5ホスト×通常/旧クエリー×source/dist=20条件を、隔離ブラウザ内で実アセットを供給して検証。いずれも同じT-6で比較は起動しない。[ホスト別結果](host-query-checks.json)。実サービスの設定や認証を変更する試験ではない。

既存h1、ID、tabindexとフォーカス制御の接続を維持。Chromium Accessibility treeでrole=heading、level=1、name=My Listening Archive、ignored=falseを確認。ページtitle・正式名称・利用規約/プライバシーは不変。日英や画面遷移でも名称は変わらない。

## 静的配布

配布許可リストからbrand-compare.jsだけを除外し、想定どおり**20ファイル**。不要素材・docs・SVG・比較用JSなし。brand.css、WOFF2、OFLを維持する。全ファイル名とSHA-256は[dist-sha256.json](dist-sha256.json)を参照。

|配布ファイル|bytes|
|---|---|
|`.nojekyll`|0|
|`404.html`|1511|
|`JosefinSans-OFL.txt`|4449|
|`archive-store.js`|15752|
|`archive-toolbar.css`|3271|
|`archive-toolbar.js`|5784|
|`brand.css`|644|
|`index.html`|178940|
|`insights.css`|8727|
|`insights.js`|32670|
|`josefin-sans.woff2`|47740|
|`legal.css`|1391|
|`legal.js`|863|
|`mobile-navigation.js`|11138|
|`photo-lifecycle.js`|8183|
|`photo-store.js`|4384|
|`privacy.html`|27941|
|`recovery-export.js`|1295|
|`search.js`|15441|
|`terms.html`|19003|

`.nojekyll`はビルドが生成する空ファイル。それ以外の19ファイルはsource/distのバイト列・SHA-256が一致。HTML/CSS参照は相対パス。ルートとGitHub Pages型サブパスで検証した。明示許可リスト、symlink拒否、欠落/不正参照拒否、古いdistの消去、バイナリをUTF-8解析しない安全性を維持。静的ビルド試験では、sourceの不要な比較JSを公開しないことと、distに残る古い比較JSを次のビルドが消去することも確認。

フォントは既存の公式Google Fonts Josefin Sans 2.001（WOFF2 47,740 bytes）、SIL OFL 1.1（4,449 bytes）を変更せず配布。[出典・バージョン・変換・Reserved Font Name確認](../brand-logo-02/font-source.md)。追加の外部依存・CDN・実行時フォント通信はない。

## ブランド素材・過去資料の保持

[全618ファイルの不変確認・SHA-256](preservation.json)。第1〜7次報告、比較画像・計測・ログ、ブランド素材と規約/フォントを開始HEADのバイト列と照合し、すべて不変だった。過去の報告書に書かれた当時の暫定判断も改変していない。

- F-1原案: `docs/brand-symbols/f-series/F-1-reference.jpg`
- F-1/F-2/F-3 SVG: `docs/brand-symbols/f-series/`
- 思想・形状/線幅/余白計測・第4〜6次証跡: [F系README](../brand-symbols/f-series/README.md)およびリンク先。
- F-4=F-1の36px、F-5=F-2の36pxという記録も維持。
- B-4 SVG: `docs/brand-symbols/archive/B-4.svg`および過去報告。
- M-1/M-2/M-3: [第7次報告・仕様・画像・計測](../brand-logo-02-round7/report.md)。将来のネイティブアプリやブランド展開時の再検討候補として保持。
- T系の他候補: [第6次比較](../brand-logo-02-round6/report.md)、T-6正式採用の経緯は本報告。

これらは開発・ブランド資料でありdist対象外。F系は暫定ブランドシンボルとして保持し、ヘッダー採用とは別に扱う。今回、造形/線幅の最終選定、再設計、新アイコン、Xプロフィール、favicon、Apple Touch Icon、Manifest、商標・著作権上の最終判断は行わない。

## 自動検証・データ保全

- Node全197件成功（`node.log`）。
- 静的ビルド6件成功（`build-tests.log`）、20ファイル（`build.log`）。
- 正式ブランド24条件：6幅×日英×source/dist。実Josefin Sans使用、他UIフォント非干渉、正式見出しAX、3領域起動・アーカイブ/Insights遷移、記録/写真不変、200%文字設定、外部通信0（`default-header.log`、[実フォントと実測](default/metrics.json)）。
- 320pxでフォント取得遮断を4条件（source/dist×通常/旧比較URL）確認し、正式名称を表示。
- 最終専用試験：24条件で第7次T-6と数値・画像厳密一致、画像差分0px。旧クエリー48条件、5ホスト×2URL×source/distの20条件、200%文字設定、旧版からの合成データ更新安全性が成功（`final-browser.log`）。
- 静的配布12条件：source/dist/clean URL×ルート/サブパス×日英。3領域CRUD・写真表示・JSON往復・IndexedDB・規約ナビ・404、JavaScript無効時の規約日英を確認（`distribution.log`）。
- `git diff --check`成功。新規回帰なし。

旧比較試験`tests/brand_comparison.py`は削除した。撤去済み候補の切り替え・操作ボタンを試す意味がなくなったため、`tests/brand_final.py`による正式表示、旧版との厳密一致、比較機能不在、旧URL/ホスト、同一originでの更新安全性へ置き換えた。`brand_logo.py`と実測helperも正式表示・アクセシビリティ・フォールバック用へ整理した。旧試験を単に実行対象外にして検証を省略していない。

同一originで第7次版へ合成Listening35件・Collection2件・Live2件と写真を投入し、最終distへ更新して旧比較URLを開く試験では、全IndexedDB・localStorageスナップショットが完全一致。JSON書き出しのバイト列・SHA-256も一致した。3領域のアーカイブ写真とInsightsが表示でき、往復後のJSONも不変。[更新安全性](upgrade-safety.json)。比較コードが存在しないので、比較操作に伴う再描画・読み書き・追加通信の実行経路も存在しない。

言語切り替えは従来どおり設定と世代メタデータを保存するため、その操作まで無書込とは扱わない。通常ブランド試験では言語操作後の記録本体・写真を比較し、更新安全性試験では言語操作を挟まず全DB/localStorageを比較した。検証は隔離ブラウザと合成/空データのみで、個人記録・写真への操作なし。

旧Python5試験の既存失敗は第1次でmainと照合済み（旧データ比較、旧記録検索、旧注入点、旧Gridボタン、非表示旧Listボタン）。[第1次報告とlegacyログ](../brand-logo-02/report.md)を活用し、新規回帰と区別する。未変更の検索・保存保護・Insights集計などは第1〜7次の検証結果も活用し、無関係な修正・全面再検証を行わない。

## 変更・削除ファイルとPR全体の変更概要

今回:

- `index.html`: 単純な正式名称h1、比較script撤去、CSS参照キャッシュ更新。
- `brand.css`: 正式T-6だけに整理。見た目は不変。
- `brand-compare.js`: 削除。
- `scripts/build-static.cjs`: 比較JSを許可リストから除外。
- `tests/static_build.py`: 20ファイル、旧比較JSの排除/残留消去を確認。
- `tests/brand_comparison.py`: 削除し、`tests/brand_final.py`へ代替。
- `tests/brand_logo.py`、`tests/brand_text_metrics.py`: 正式表示・AX・フォールバック用に整理。
- `docs/brand-logo-02-final/`: 本報告、日英6幅・旧版との同倍率比較画像、実測・ログ・配布/保持ハッシュ。

PR #60全体（mainからの最終差分）では、旧レコード収納箱と背景タイルを除去し、ブランドh1をローカルJosefin Sansで控えめに中央表示する。フォント/OFLとbrand.cssを導入し、許可リストに3つの必要アセットを追加、バイナリ/OFL/CSS内相対参照の安全な配布検証を整えた。第1〜7次でC/B/E/F/T/Mを比較した資料を保持し、最終的な実行時コードから候補・シンボル・比較機能を除去した。ブランド以外のUI・アプリ全体のフォント/配色・保存/IndexedDB/写真/JSON/CSV・MusicBrainz/CAA・規約本文・アイコン類は変更していない。

## 未検証・残存リスク・次の判定

最終整理後のiPhone Safari実機・VoiceOver実音声、実ユーザーデータは未検証。Chromiumの厳密比較・AX treeと合成データ検証は実機確認の代わりではない。ブラウザやOSによるフォント描画差は最終実機で確認する。未認証Accessリダイレクトとデプロイ成功を確認し、認証後の実機確認は運営者が行う。

T-6は今回の指示で正式採用済み。F系シンボル自体の正式造形・線幅・権利判断は別作業であり、本PRの完了条件には含めない。実装・検証・Preview反映後、運営者の最終iPhone Safari確認と①開発・検証ルームの最終品質判定を待つ。

mainへのマージ・GitHub Pages/Production反映・Access設定変更・正式URL公開状態の変更は行っていない。mainマージと本番反映には別途承認が必要。
