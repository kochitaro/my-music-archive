# ブランドロゴ第7次改修：T-6とMLA略称3案の比較

2026-11-28。第6次の実機評価を尊重し、シンボルなし・小さめ・中央寄せを維持する。T-6の表示仕様を基準に、視覚上の表示文字列MLAと3つの文字サイズを比較。サービスの正式名称は変更しない。正式採用前の実機評価用。

## 作業開始時のリビジョン・配信範囲

|開始時|SHA / tree|
|---|---|
|main SHA|`6fef37adaf6d96a7087ea474aef65546159bdb01`|
|main tree|`fbdc2bcfd8bf06835a4fea74cdba45c3a020cd40`|
|PR HEAD|`3c346197a545a44368a6cfd63043cd429596ab11`|
|Preview SHA|`98e697ac724fb1ee870c5369b8a42e0676ea3f9f`|
|共通tree|`522c6cb284e50689a1d49038522ca1d6216199a8`|

リモート・ローカルで一致を確認。[第6次報告](../brand-logo-02-round6/report.md)を参照し、`feat/brand-logo-c1`・PR #60を継続。最新HEAD/tree、Preview SHA/tree、デプロイ単位の固定URL・成功証跡はPR本文と最終回答に記載（自己参照コミットを避ける）。

固定比較Preview: https://deploy-preview.my-listening-archive.pages.dev/?logo-compare=1

通常Preview: https://deploy-preview.my-listening-archive.pages.dev/

mainへマージせず、GitHub Pages・Cloudflare Production・Access設定・正式URL公開状態は変更しない。本番配信ブランチ`deploy/holding-page`は開始時`3cfb40b0a4a52f652b0873b326fcc7cde88d8222`を維持。author/committerはCodex、GitHub noreplyを使用し、個人メールを公開コミットへ含めない。

## 候補・共通仕様・実測

393px幅、source、日本語、Chromium。利用可能領域はx=12から幅369px、中心x=196.5px。以下は文字の行ボックスの実測（px）。

|案|可視文字列|文字サイズ|配置|開始x|開始y|表示幅|行高|
|---|---|---|---|---|---|---|---|
|T-6|My Listening Archive|22|中央|87.61|30.25|217.78|27.50|
|M-1|MLA|22|中央|171.08|30.25|50.83|27.50|
|M-2|MLA|24|中央|168.77|29.00|55.45|30.00|
|M-3|MLA|26|中央|166.47|27.75|60.06|32.50|

T-6について第6次の各幅・日英・source/distの実測値と比較し、サイズ、開始位置、幅、行高が一致することを確認。表示文字列の出し分けに必要なh1内部要素とアクセシブル名以外に、T-6の表示仕様は変更しない。

Josefin Sans 2.001、Regular 400、字間.02em、行高1.25、文字#f0f1f3、背景#11151b、ローカルWOFF2/OFLを維持。M系は書体の通常のM/L/Aをそのまま表示し、独自の文字加工・モノグラム・シンボル・装飾を追加しない。

通常時のブランド高40px、上余白5px、下余白16px。文字行ボックスの垂直中央はy=44px、後続の大分類ボタン上端はy=80pxで全案一致。シンボル・42×40px配置領域・文字とのgapは存在しない。

### 各画面幅での文字サイズ（日英共通）

|画面幅|T-6|M-1|M-2|M-3|
|---|---|---|---|---|
|320|22|22|24|26|
|375|22|22|24|26|
|390|22|22|24|26|
|393|22|22|24|26|
|430|22|22|24|26|
|1280|22|22|24|26|

すべて通常時1行。指定幅では縮小が必要な条件はなく、不要なvw制約は加えない。rem換算で利用者の文字拡大へ追従し、200%文字設定でも欠落・横はみ出しなし。必要時は折り返して領域を拡張する。拡大時のヘッダーは必要な高さへ伸び、40pxに切り捨てない。通常の40px領域と5/16pxの上下余白を詰める変更は行わない。

[全候補・各幅の実寸とアクセシブル名](metrics.json) / [通常T-6・実フォント計測](default-metrics.json)

## 正式名称・アクセシビリティ・実装方法

正式名称はMy Listening Archiveのまま。HTMLのtitle、利用規約・プライバシーポリシー、サービス紹介、他の既存名称表記は変更しない。規約/プライバシーと`docs/brand-symbols/`に開始HEADとの差分がないことを確認。[ファイルごとの照合結果](preservation.json)。

既存のh1、page-heading、tabindex=-1を維持。h1に常時`aria-label="My Listening Archive"`を付け、内部に正式表記と略称の静的な2spanを置く。視覚用spanはaria-hidden=trueとし、比較ではCSSのdisplayだけを切り替える。T-6は正式表記、M系はMLAだけが見える。非表示spanはレイアウト幅を持たず、シンボル用の余白にもならない。

この方式により、h1の差し替えやtextContent更新を避け、既存の翻訳/描画Observerが比較操作に反応しない。h1は1個で、アクセシブル名は全案で正式名称。Chromiumの実際のAccessibility treeでrole=heading、level=1、name=My Listening Archive、ignored=falseを確認した。MLAが正式名称へ置き換わったとは扱わない。

各候補について日英・3領域・アーカイブ/統計の48遷移条件で、可視文字列・選択ボタン・正式なアクセシブル名・ページタイトルが維持されることを確認。画面遷移でM表示が正式表記へ戻ったり、逆に通常T-6がMLAになることはない。

## 比較操作と画像

比較URL右下の **T-6 / M-1 / M-2 / M-3** をタップする。初期表示はT-6。通常URLはT-6のみ・パネルなし。再読み込みでT-6へ戻り、選択は永続化しない。

既存Preview/デプロイ単位ホスト・localhost＋`logo-compare=1`の条件を維持。本番・GitHub Pagesホストでは指定してもパネルを表示しない。ボタン44×44px以上、320pxでは2列×2行、横はみ出し・重なりなし。選択は色とaria-pressedで示す。タップ・キーボード操作に対応。

比較はbrandの専用data属性とパネルのaria-pressedのみを変更。通常時は高さが変わらず、後続UIも不変。拡大時の折り返しによるネイティブscroll anchoringへの位置保持処理は第6次のものを維持し、スクロール位置を保つ。

- [393pxヘッダー4案：日本語](headers-comparison-393-ja.png) / [英語](headers-comparison-393-en.png)
- [393pxアプリ4案：日本語](apps-comparison-393-ja.png) / [英語](apps-comparison-393-en.png)
- [320px T-6：日本語](T6-320-ja.png) / [英語](T6-320-en.png)
- [1280px T-6：日本語](T6-1280-ja.png) / [英語](T6-1280-en.png)
- [合成記録のアーカイブ](T6-archive-393.png) / [統計](T6-insights-393.png)

画像は同じ画面幅・倍率・空のListening画面で撮影。ヘッダーは利用可能領域全体を撮影し、h1だけを切り抜いて位置を揃え直さない。アプリ比較は同じ393×852px画像を縮小せず2×2に配置。各案・320/393/1280pxの元の個別画像も`top-{幅}-{言語}-{案}.png`として保持する。

## F系資料の保持・配布境界

[既存保存先](../brand-symbols/f-series/README.md)を不変保持する。

- F-1原案: `docs/brand-symbols/f-series/F-1-reference.jpg`
- F-1/F-2/F-3 SVG: `docs/brand-symbols/f-series/`
- 思想・形状/線幅・面積・端部/間隔の計測・過去検証: 同READMEのリンクと第4〜6次資料。
- B-4 SVG: `docs/brand-symbols/archive/B-4.svg`
- F-4はF-1の36px、F-5はF-2の36pxであり、別形状ではないという記録も維持。

ブランド資料の造形変更・外部展開・権利判断は行わない。素材はdist許可リスト外で、21ファイルのdistにdocsフォルダーやシンボル素材は含めない。アプリのヘッダーは全案でSVG/シンボル配置領域なし。

## 自動検証・データ/画面状態

- Node全197件、静的ビルド6件成功。
- 比較96条件（6幅×日英×4候補×source/dist）成功。文字列/サイズ/中央配置・T-6の第6次一致・シンボル/余分領域なし・通常40px高/余白/後続UI位置不変・通常1行・欠落/横はみ出しなし・パネル操作領域を確認。
- 全候補・各幅で200%文字設定も確認。全案で領域が必要に応じて伸び、文字欠落なし。
- 通常T-6の24条件成功。正式可視名称、h1/ID/tabindex、実Accessibility treeで正式見出し名、CDPでJosefin Sans実適用、他UIフォント不変、外部通信0、3領域起動/ナビ、記録/写真不変性を確認。
- フォント取得を遮断した320pxのsource/distでも、全4案の可視文字列・指定サイズ・正式アクセシブル名を検証。フォールバックでもサービス名/MLAは表示される。
- 393pxで合成35記録・写真・モック検索結果を表示し、通常/200%文字のアーカイブ/統計で全4候補をタップ/キーボード切り替え。対象DOM変更0、IDB読み込み0/書き込み0、Storage書き込み0、追加fetch0。検索入力/結果・記録ノード・開いた絞り込みパネル・スクロールと全DB/localStorageスナップショットが完全一致。
- 日英・3領域・2画面の48遷移条件で選択表示・正式名称・h1構造を維持。
- 許可リストは変更なし。21配布ファイルのsource/dist完全一致・相対参照・バイナリ/OFL・symlink拒否・不要ファイル排除を維持。[配布SHA-256](dist-sha256.json)。
- 静的配布12条件（source/dist/clean URL×ルート/サブパス×日英）で3領域CRUD・写真表示・JSON往復・IndexedDB・ナビ/404を確認。
- 未変更の検索/Insights集計/保存保護等は既存証跡を活用。旧5試験は第1次でmainと同じ旧UI/旧データ/旧注入点の失敗を照合済みで、新規回帰と区別。無関係な修正や不要な全面再検証は行わない。

ログ: `browser.log`, `default-header.log`, `node.log`, `build-tests.log`, `build.log`, `distribution.log`。

## 変更ファイル・暫定判断・未検証

- `index.html`: 既存h1に正式なaria-labelと視覚用2span、CSS/JS参照キャッシュ値更新。ページtitleは不変。
- `brand.css`: 初期T-6とM系サイズ、可視文字列の切り替え、全案中央、4項目用の狭幅パネル。書体/ウェイト/字間/行高/配色/高さ/余白は維持。
- `brand-compare.js`: T-6/M-1/M-2/M-3、初期T-6のみ。既存の状態分離・位置保持・Preview条件・非永続化は維持。
- `tests/brand_comparison.py`: 4案、T-6基準一致、AX tree、日英/画面遷移と状態保持。
- `tests/brand_logo.py`: 通常T-6、可視文字列と正式名称、全案のフォント失敗時表示。
- `tests/brand_text_metrics.py`: 4候補の実寸・正式名称と実Accessibility treeの検証。
- `docs/brand-logo-02-round7/`: 本報告・画像・計測・ログ。

初期T-6は比較基準であり正式採用ではない。MLAはヘッダーの視覚表示だけ。M系の文字加工やサービス改名を行っていない。通常40pxと上下余白を詰める調整も行わない。

未検証: iPhone Safari実機、VoiceOver実音声、実ユーザーデータ、F系外部展開と権利上の最終安全性。アクセシビリティはChromium AX treeで確認したもので、実際のVoiceOver音声評価の代用とはしない。

検証は隔離ブラウザと合成/空データのみ。個人記録・写真を操作しない。正式名称、ロゴタイプの書体/ウェイト/字間、F系造形、ヘッダー以外の既存UI、記録/写真/保存、IndexedDB、JSON/CSV、MusicBrainz/CAA、favicon/Apple Touch Icon/Manifest/Xプロフィール、規約/プライバシーは変更していない。

実装後は運営者のiPhone Safari実機評価を待つ。正式採用、比較機能撤去、F系外部展開、権利確認、mainマージ、本番反映は別途判断する。
