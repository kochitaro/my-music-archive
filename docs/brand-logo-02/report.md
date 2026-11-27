# 一般公開前ブラッシュアップ02：C-1ブランドロゴ

2026-11-27。正式採用前の視覚評価用。iPhone Safari実機評価待ち。

## リビジョンと公開範囲

開始main: `6fef37adaf6d96a7087ea474aef65546159bdb01`。
開始tree: `fbdc2bcfd8bf06835a4fea74cdba45c3a020cd40`。接続済みGitHubのmainとローカルで一致を確認。

新規ブランチ: `feat/brand-logo-c1`。PR番号・最終HEAD SHA/tree・Preview SHA/treeはPR本文と最終回答に記載する（自己参照コミットを避けるため）。

固定Preview: https://deploy-preview.my-listening-archive.pages.dev/

既存`deploy/preview`の配信方式を使用。main、GitHub Pages、Production、正式URL公開状態、Access設定の変更は行わない。Previewは配信前後に未認証アクセスがCloudflare Accessへ302となることを確認する。Access認証後の実機表示は運営者の評価対象。

## 実装ファイル

- `index.html`: C-1インラインSVG、旧ブランドCSSの撤去、brand.css参照。h1・page-heading・tabindex=-1を維持。JavaScriptは変更しない。
- `brand.css`: ブランドh1だけにJosefin Sansを適用。寸法・余白・拡大時の折り返し。
- `josefin-sans.woff2`、`JosefinSans-OFL.txt`: ローカルフォントとライセンス。
- `scripts/build-static.cjs`: 上記3公開アセットだけを許可リストへ追加。HTML/CSS以外をUTF-8解析しない。
- `tests/static_build.py`: 新規公開ファイルのハッシュ・再現性、フォントCSSの参照漏れ・絶対パス・欠落を検証。
- `tests/brand_logo.py`: 指定6幅×日英×source/distの検証と画像生成。
- `docs/brand-logo-02/`: 本報告、比較画像、検証ログ。静的配布対象外。

## シンボルの出典・抽出・形状比較

素材は運営者が提供した2画像のみ。横長の`2-a_minimalist_logo_on_a_nearly_black_dark_charcoal.png`を主基準とし、比較表の`1-a_clean_dark_charcoal_black_background_design_shee.png`のC-1を補助参照。別の素材・ロゴ・ジャケットは使っていない。

横長原案のシンボル領域を切り出し、RGB平均輝度128の等高線をscikit-imageのmarching squaresで抽出。連続した最大輪郭を、元画像で0.45px以内のDouglas–Peucker簡略化により112頂点の閉じた塗りつぶしパスへ変換。一定幅strokeではない。上端、中央の折り返し、太さの増加、下端の切断面、間隙を抽出輪郭から保持。座標を原点へ平行移動し小数2桁へ丸めた。手作業の曲線再設計・新モチーフ追加はない。

抽出範囲: x=361.237〜687.662、y=161.447〜544.891。viewBox `0 0 326.43 383.44`、比率約0.8513。元解像度の二値輪郭に対する簡略化後マスクのIoUは99.21%、差分193px。差は輪郭の簡略化とラスター境界処理によるもの。完全一致のSVG原本があるとは扱わない。大きく拡大すると直線分が確認できるが、ヘッダー表示では視認上滑らか。

比較表C-1は横長原案より相対的に横幅が広く、下部の太さ・折り返しの比率も異なる。比較表へ合わせる変形はせず、横長原案を優先した。下端のほぼ垂直な切断面も原案輪郭を維持している。

[主原案の切り出し](original-symbol.png) / [比較表C-1](comparison-c1.png) / [SVG単体](svg-symbol.png) / [同一高さの比較](shape-comparison.png)

[旧・新ヘッダー390px](header-comparison-390.png) / [旧・新ヘッダー1280px](header-comparison-1280.png)

SVGは1個のpathのみ、currentColor（#f0f1f3）。外部参照・script・イベント・メタデータなし。aria-hidden=true、focusable=falseとし、旧「レコード収納箱」の読み上げを除去。背景タイル・枠線・グラデーション・影なし。元画像全体、作業中間ファイルはdistへ含めない。

## フォントと寸法

[公式配布元・バージョン・OFL・容量の詳細](font-source.md)。Version 2.001、SIL OFL 1.1。Reserved Font Nameを維持したWOFF2コンテナ変換。サブセット化なし。47,740 bytes、ライセンス4,449 bytes、CSS893 bytes、追加公開ファイル計53,082 bytes。

|設定|デスクトップ|540px以下|
|---|---|---|
|シンボル|40.86×48px|34.05×40px|
|シンボルと文字の間隔|12px|10px|
|文字|28px|320pxで20px、375pxで22px、390pxで約22.55px、393pxで約22.65px、430pxで24px|
|ウェイト|400 Regular|400 Regular|
|字間|.02em|.02em|
|行高|1.25|1.25|
|ブランド上下余白|上5px・下16px|同左|

display:flex、align-items:center。原則1行。remを含むサイズ式を採用し、文字拡大時は折り返しで欠落を防ぐ。フォールバックはAvenir Next / Helvetica Neue / Arial / sans-serif、font-display:swap。外部フォント通信・CDNなし。他のUIは既存システムフォント。寸法・ウェイト・字間は暫定で、iPhone評価後に調整可能。

## 日英画像

|幅|日本語|英語|
|---|---|---|
|320|[画像](header-320-ja.png)|[画像](header-320-en.png)|
|375|[画像](header-375-ja.png)|[画像](header-375-en.png)|
|390|[画像](header-390-ja.png)|[画像](header-390-en.png)|
|393|[画像](header-393-ja.png)|[画像](header-393-en.png)|
|430|[画像](header-430-ja.png)|[画像](header-430-en.png)|
|1280|[画像](header-1280-ja.png)|[画像](header-1280-en.png)|

## 検証

- Node全197件成功。変更前mainも197件成功。sandbox内で起きた子プロセスEPERMは実行環境制約であり、通常権限で全件再実行して解消。
- 静的ビルド6件成功。20配布ファイル。バイナリ・OFLの元/dist完全一致、許可リスト・symlink拒否・不要ファイル排除・再現性を維持。[成果物SHA-256](dist-sha256.json)。
- ヘッダー24条件（6幅×日英×source/dist）成功。文字の欠落・シンボル変形・ヘッダーの横はみ出しなし、通常時1行。200%以上の文字拡大時も欠落なし。
- CDP実フォント情報でJosefin Sansのカスタムフォント使用を確認。他UIのfont-familyが変わらず、外部通信0。フォント取得を遮断してもサービス名を表示。[代替表示](fallback-source-320.png)。
- フォント読み込み前後のヘッダー・ボタン位置を6幅で比較。[計測](loading.json)。
- 既存`static_distribution.py`: source/dist/クリーンURL×ルート/サブパス×日英の12条件、3領域起動・CRUD・写真表示・JSON書出し/復元・IndexedDB・規約ナビ・404を確認。
- 既存`browser_smoke.py`: モック検索、検索経由登録、編集・削除、日英、写真/記録の再読み込み、JSON復元の14グループ成功。
- 既存`insights_polish.py`: 320/375/390/393/430px日英、3領域Insights、設定・スクロール・CRUD・JSON・データ不変性を確認。
- 既存`restore_safety.py`: 書込/容量/トランザクション/写真部分失敗、壊れたJSON等の保護を確認。
- 旧5試験はmainと変更後を別々に実行。旧データ比較、旧記録検索、旧注入点、旧Gridボタン、非表示旧Listボタンの既存失敗と新規回帰を区別。旧試験は修正していない。`legacy-*.log`参照。

全試験は隔離ブラウザと合成・空データのみ。運営者の記録は操作していない。保存機構・IndexedDB・写真・JSON関連コードを変更していない。言語変更は従来どおりsettingsと世代メタデータを更新するため、それを無変更と誤認せず、記録本体・写真の不変性を検証した。既存配布・復元試験では全データの往復・保護も確認。

## 未検証と運営者確認

iPhone Safari実機、VoiceOver実音声、実ユーザーデータ、権利上の最終安全性は未検証。今回の採用は暫定。ロゴの商標・著作権判断は運営者および①で別途行う。

認証付きPreviewで、iPhone上のシンボルと文字の視覚的な中央揃え、サイズ、間隔、先端/余白の見え方を評価する。正式採用、mainマージ、本番反映は別途判断とする。
