# Josefin Sans 配布記録

公式: https://github.com/google/fonts/tree/0fd277cf519ed2c02e63e4e19220f4cf6103df51/ofl/josefinsans

取得日: 2026-11-27。`JosefinSans[wght].ttf`、118,588バイト、内部バージョン`Version 2.001`。取得時の公式ディレクトリの最新コミットは上記。内部family名には既定のThin instanceもあるが、CSSは可変フォントの400を選択する。

ライセンス: SIL Open Font License 1.1。Copyright 2010 The Josefin Sans Project Authors。Reserved Font Name: Josefin Sans。公式OFL全文をルートの`JosefinSans-OFL.txt`で配布する。

fontTools TTFontでTTF全体をWOFF2へコンテナ変換。サブセット化、字形変更、名前変更、ウェイト固定化は行わない。字形・name等のテーブルは元と一致。変換に伴うheadチェックサム変更とDSIG除去のみ。WOFF/WOFF2の圧縮・コンテナ変換として扱い、Reserved Font Nameを維持する。アプリの依存パッケージは追加しない。

配布WOFF2: 47,740 bytes、SHA-256 `8dc6f07227fe5b2270410e95571062222a37bb5a732f32568b071cea532550a1`。

OFL: 4,449 bytes、SHA-256 `aee5a4081e8a52f80428b30f178b719d115f18dad3e1fa15a986163e1078a85b`。

CSS: 893 bytes。新規公開アセット合計53,082 bytes。外部フォント通信・CDN不要。フォールバックを含めてブランドh1にのみ適用する。
