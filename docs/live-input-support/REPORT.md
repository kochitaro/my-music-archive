# Live入力支援・タグ・未保存入力保護 改修報告

- 基準: main `7aa09aa`（PR #50取り込み済み）
- ブランチ: `feat/live-suggestions-tags-discard`
- 実データ・既存186公演にはアクセスせず、合成データと使い捨てブラウザコンテキストのみで検証。
- mainへのマージ・本番反映は行わない。

## 変更と影響範囲

`index.html` のLiveフォームと共通サジェストのみを中心に変更。

1. `artistEditor()` が追加する各入力に、共通化した `setupSuggestion()` を接続。`distinctValues()` でLive出演者配列を集計し、大小文字を区別せず重複統合・頻度順・部分一致・最大5件表示。完全一致は除外し、選択後・blur時に閉じる。IME中は候補を無効化。WebKitのタッチ操作でblurにより候補確定が消えないよう、touchstartでフォーカスを保ち、touchendで確定して後続の互換クリックを抑止する。削除ボタンは入力と同じ高さに配置。
2. 新規・編集に任意のカンマ区切りタグ入力とLive履歴候補を追加。既存の `parseInput()` と同じ空白除去・全角カンマ・重複統合を使用。`archiveFilterDefinitions()` にLiveタグを追加し、既存のアーティスト・年・会場とのAND条件、領域別状態保持、未設定選択、下部バーの適用中表示を再利用。詳細画面にもタグを表示。
3. 新規Liveの閉じるボタン・背景・Escapeを `requestCloseLiveCreate()` に集約。既存 `formBaseline` / `formState()` / `sameForm()` で初期状態と比較するため、初期日付・初期スコアだけでは確認しない。入力・日付パーツ・スコア・動的行・File参照を比較。確認中は背後のフォームをinertにし、キャンセル・Escapeで内容と添付をそのまま保持。破棄でフォーム・写真・出演者行を初期化。保存成功は既存の終了経路を利用し、保存失敗時は既存の下書き保護を優先。

## データ互換性

- Liveに任意の `tags: string[]` を追加。DB/JSON version 3、IndexedDBの構造・保存・写真圧縮・復旧方式は変更しない。バックアップは既存の汎用レコード保存・復元経路で保持。
- タグが存在しない・null・文字列・配列の既存データは既存パーサーで表示。未編集ならタグの元表現や項目の有無を保存時にも保持。
- Live編集で変更していない日付・公演名・会場・スコア・メモ・出演者を更新対象から除外。タグだけの変更で、旧記録の年のみの日付、元のスコア表現、空白や未設定項目を上書きしない。
- 自動タグ付与・一括書き換え・外部API追加はなし。日付UI、Insights、表示切替、操作バー構造、写真エンジン、スワイプ/Pull to Refreshは変更しない。

## 自動・ブラウザ検証

最終結果は `node-tests.log` と `browser-tests.log` を参照。

- 既存Node回帰試験: 既存164件＋追加2件、全166件通過（9ファイル）。履歴を使う既存試験のためGit全履歴を取得し、子プロセス実行が許される環境で実施。
- 新規 `tests/live_input_support.py`: Chromium / WebKit、各日本語・英語、390×844px、タッチ有効の隔離コンテキスト。外部HTTPS通信は遮断。
- 出演者候補の頻度・部分一致・完全一致除外・タップ・自由入力・2行以上・行追加削除・blur・合成IMEイベントを検証。
- タグの複数保存・編集・削除・履歴候補・未設定旧記録・他フィルターとのAND条件・領域切替の状態保持・下部バー適用中表示を検証。
- 写真を含むJSON書き出しと復元、タグのない旧JSON復元、IndexedDB再読込、タグだけの編集で旧記録の他項目が保たれることを比較。
- 未変更終了、日付のみ・スコアのみ・行追加のみの変更、ボタン・背景・Escape、キャンセル時の写真/行/値保持、破棄後の新規初期状態、保存成功時の確認抑止、保存失敗後の入力保持と再保存を検証。
- Listening / Collectionの作成・タグ候補・編集・削除を両言語・両エンジンで検証。

## 補足・残存リスク

- iPhone Safari実機、実ソフトウェアキーボード表示下のタップ、実日本語IME変換は未検証。Playwright WebKitのタッチ操作・合成compositionイベントは実機検証を代替しない。
- 旧 `pr_a_browser.py` も試行したが、現在のJSON回収形式に合わないrawバイト比較で失敗。同一失敗を未変更mainでも再現した。旧 `pr_b_draft_review.py` は旧localStorage保存失敗注入と非同期起動前のseed投入を前提とし、フォーム操作でタイムアウトするため中断。これらの古いハーネス更新は今回の範囲外。現行IndexedDB経路の保存失敗・再保存・互換性は新規ブラウザ試験で検証。
- WebKitは環境の不足ライブラリを `/tmp` に展開してヘッドレス実行。配布ソースやシステム領域には導入しない。

## 再実行

```sh
node --test --test-reporter=tap tests/*.test.cjs
python tests/live_input_support.py
```

Chromiumは既存試験同様 `/usr/bin/chromium`、WebKitはPlaywrightのブラウザと対応ライブラリが必要。`MLA_ENGINES=chromium` または `webkit` で対象を限定可能。

## スクリーンショット

各画像は合成データ。`chromium-*` / `webkit-*`、`ja` / `en` の新規・編集・タグ絞り込み・破棄確認を同ディレクトリに保存。モーダルはスクロール位置に応じた入力領域を撮影。両エンジン・両言語の4条件すべて通過。

| 画面 | 日本語Chromium | 日本語WebKit |
|---|---|---|
| 新規・出演者候補・タグ | [create](chromium-ja-create.png) | [create](webkit-ja-create.png) |
| 編集 | [edit](chromium-ja-edit.png) | [edit](webkit-ja-edit.png) |
| タグ絞り込み | [filter](chromium-ja-filter.png) | [filter](webkit-ja-filter.png) |
| 破棄確認 | [discard](chromium-ja-discard.png) | [discard](webkit-ja-discard.png) |
