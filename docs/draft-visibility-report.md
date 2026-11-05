# 未保存入力回収ボタンの表示制御

①開発・検証ルーム #2 レビュー用。基準: `c7bffd4843658855f680ab6bd0c23dff3a9892fe`。

## 変更内容

- `index.html`: 初期HTMLの既存ボタンに `hidden` を付加。`showDraft()` で `!pendingDraft()` をhiddenに設定し、既存のdraft生成・解消時の更新に追従する。
- 回収確認ハンドラでも同じ条件でボタンを更新する。確認時のdraft消去は追加しない。
- 回収パネルをフォーム内へ移す既存処理で、同じボタンもパネル直前に移す。モーダル外のボタンはオーバーレイに遮られるため、「入力へ戻る」後の実クリックによる再表示に必要。新しいボタン・メニュー・CSSは追加しない。
- `tests/draft_visibility.py`: 3領域の新規・編集、基準版との回収JSON/テキスト/ダウンロード比較、クリックによる再表示、確認時のdraft保持、再保存成功、閉鎖保護、通常操作を検証。アプリ差分が指定4置換だけであることも検証。
- `tests/backup_guide.py`: 旧「全JavaScript不変」チェックは今回の表示変更と両立しないため、案内details全文の基準版一致チェックに変更。アプリ変更範囲は追加試験が厳密に検査する。案内の操作・全文・保存失敗時の保全試験は維持。

## 表示条件

`pendingDraft()`、すなわち `draft && !draftRecovered` が真の場合のみ表示する。通常閲覧・検索・並べ替え・絞り込み・新規/編集開始時は非表示。失敗draft生成時に表示し、「入力へ戻る」では表示を維持する。確認後、または既存ロジックによる同じ入力の再保存成功後は非表示。確認後に編集して既存ロジックが再びdraftを未回収にした場合は再表示する。

## 手動回収への影響

draftなしでモーダル入力を手動captureする既存onclickは残しているが、通常時のボタン非表示により通常UIからは利用できなくなる。保存前の入力を任意に手動書き出しする経路が失われる点は仕様上の変更である。ソースを調査し、他の処理がこのonclickを呼んで回収を開始する依存経路はないことを確認した。

保存失敗、別タブ競合、写真変換失敗、削除失敗、復元失敗等はボタンとは独立して既存captureDraftを呼ぶ。これらの必要な回収経路と、保持したパネルの再表示を維持する。別タブ更新通知だけでdraftがない場合には表示せず、保存拒否によりdraftが生成されると表示する。

## データ保全

DB version・保存キー・JSONバックアップ/復元・Web Locks・保存/競合検出・回収JSON/テキスト生成・写真変換・フォーム閉鎖保護・draft解消条件は変更なし。確認時のdraft保持と既存の確認後動作も維持。PR #14の案内HTML/CSS、サイト名、その他画面レイアウトは変更なし。試験は隔離Chromium・合成データ・ループバックHTTPを使用し、外部HTTPSを遮断した。

## 自動検証

実行ログは `draft-visibility-evidence/` に格納。

- `node --test tests/*.test.cjs`: 126件成功、失敗0。
- `python -u tests/draft_visibility.py`: 3領域 × 新規/編集の6ケース。初期/通常操作、保存失敗、パネルを閉じた後の実クリック、確認、再保存、JSON/テキスト比較。
- `python -u tests/pr_b_draft_review.py`: 36件成功、失敗0、未実施0。
- `python -u tests/pr_b_browser.py`: 70シナリオ成功。別タブ競合、Web Locks、復元失敗、写真、非同期競合を含む。
- `python -u tests/data_preservation.py`: 保存失敗時の削除・編集・写真・読込失敗の既存保全回帰試験成功。
- `python -u tests/backup_guide.py`: PR #14の全文、日英/キーボード開閉、24モバイルレイアウト、3領域の保存失敗回収と案内表示成功。
- `python -u tests/ui_v0322.py`: 6グループ成功。通常登録・編集・削除、JSON/CSV、復元・再読み込みを含む。
- `git diff --check`: 成功。

初回の権限なし実行では、HTTPソケット作成とgit子プロセスが実行環境に拒否された。必要なネットワーク実行権限で再実行して解消した。Git取得も同じ権限で成功し、ローカル作業ブランチの基準を指定コミットに合わせた。製品の不具合ではない。

## 未確認事項

新たなSafari実機検証、実容量不足、OSによるページ破棄・強制終了、OS上の保存先確認は未実施。例外注入による失敗試験を実容量不足の実測とは扱わない。①のレビュー承認待ち。mainへの変更・マージ・デプロイは行わない。

## 変更ファイル一覧

- `index.html`
- `tests/draft_visibility.py`
- `tests/backup_guide.py`
- `docs/draft-visibility-report.md`
- `docs/draft-visibility-evidence/visibility.log`
- `docs/draft-visibility-evidence/unit.log`
- `docs/draft-visibility-evidence/review.log`
- `docs/draft-visibility-evidence/prb.log`
- `docs/draft-visibility-evidence/preservation.log`
- `docs/draft-visibility-evidence/guide.log`
- `docs/draft-visibility-evidence/ui.log`
