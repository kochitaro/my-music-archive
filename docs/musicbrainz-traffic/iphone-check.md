# iPhone Safari確認（外部MusicBrainz通信なし）

対象はAccess保護付きPreview。新しいプライベートブラウズを使い、合成記録だけを扱う。
MacのSafari WebインスペクタをUSB接続したiPhoneの各タブに接続する。
本手順はコンソールだけに模擬Fetchを置く。公開ファイル・Access設定は変更しない。

1. Previewを2タブ開き、Access認証を済ませる。検索はまだ行わない。
2. **各タブに**次のコードを入力し、`MOCK READY`を確認する。再読込したタブには再設定が必要。
3. アルバム名検索へ切替え、タブごとに異なる合成検索語を使う。

```js
(() => {
  const native = window.fetch;
  window.mlaMockStarts = [];
  window.mlaMockMode = 'ok'; // ok / 503 / long / hang
  window.fetch = (input, options = {}) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    if (url.hostname !== 'musicbrainz.org') return native(input, options);
    const mode = window.mlaMockMode;
    const row = { at: performance.timeOrigin + performance.now(), mode };
    window.mlaMockStarts.push(row);
    console.log('MOCK MusicBrainz (no network)', JSON.stringify(row));
    if (mode === 'hang') return new Promise((resolve, reject) => {
      const abort = () => reject(new DOMException('mock aborted', 'AbortError'));
      if (options.signal?.aborted) abort();
      else options.signal?.addEventListener('abort', abort, { once: true });
    });
    const status = mode === 'ok' ? 200 : 503;
    const headers = { 'Content-Type': 'application/json' };
    if (status === 503) headers['Retry-After'] = mode === 'long' ? '60' : '4';
    return Promise.resolve(new Response(JSON.stringify({
      artists: [], count: 0, 'release-groups': [], 'release-group-count': 0
    }), { status, headers }));
  };
  console.log('MOCK READY: MusicBrainz requests are intercepted in this tab');
})();
```

## 最小限の確認

- 2タブから検索。取得結果は0件でよい。両タブの`mlaMockStarts`を取得し、at順に合わせる。
  隣接する開始時刻の差が1250ms以上であることを確認。実APIへの要求がNetworkに出ないことも確認。
- 一方で`mlaMockMode='503'`にして新しい語を検索。別タブでも新しい語を検索し、共有待機することを確認。
  最大4回で終了し、直後の再検索や別タブでも最終クールダウンを迂回しないことを確認。
- `mlaMockMode='hang'`で検索中に別タブへ移動、画面ロック、復帰を試す。
  古い検索が自動再開せず、語や既取得結果を追加で消さず、明示的な再検索が可能なことを確認。
  `ok`へ戻す。凍結中の厳密なタイマー実行時刻は保証対象にしない。
- 最後に`mlaMockMode='long'`で検索。30秒以上待ち続けず終了し、別タブからも60秒の抑制を短縮しないことを確認。
  再読込検証では、再読込後に必ず模擬Fetchを設定してから検索する。
- 待機中に合成記録を手動登録・編集・削除し、写真、Insights、JSON書出し・復元を確認。
  日英のステータス切替、通常ページングと方式切替も確認する。

終了後は検証用プライベートタブを閉じる。通常利用のサイトデータやIndexedDBは消去しない。
この手順はFetch開始制御の実機確認であり、CORS・実ネットワーク到着時刻の検証はローカルHTTP自動テストで補う。
端末実機は本作業環境にないため、実施結果を別途記録する。
