# threads-sync-setup.md — note→Threads 自動同期の構築手順（ノーコード／IFTTT）

noteに投稿した記事を、順次Threadsへ自動で同期する仕組みのセットアップ手順。

> 【2026-06-17 最終方式：GitHub Actions（無料・完全自動）】
> Make＝公式Threads非対応、IFTTT＝RSSトリガーが有料(Pro)、と判明。無料のノーコード完結は不可。
> → **既存のGitHubリポジトリ＋GitHub Actions**でRSSを定期チェックしThreads APIで自動投稿する方式に決定。費用ゼロ・完全自動。Threads APIトークンの一度きりの取得だけが必要。

構成：
- `scripts/threads_sync.py`：note RSS新着 → Threads APIで投稿。`logs/threads-synced.json` で重複防止。初回は既存を済み扱いにして暴発を防ぐ。
- `.github/workflows/threads-sync.yml`：毎時実行（cron `10 * * * *`）＋手動実行。状態ファイルをコミット。
- GitHub Secrets：`THREADS_ACCESS_TOKEN` と `THREADS_USER_ID`。
- プレビューカード：本文にnote URLを入れるのでThreads側で自動生成。
- 時間差：毎時チェックなので新着は1時間以内に同期。

RSS URL：`https://note.com/tommykaoleo/rss`

---

## Threads APIトークンの取得（一度だけ）

1. https://developers.facebook.com/ にログイン（Threadsアカウントと連携しているFacebook/Instagramアカウントで）。
2. 「マイアプリ」→「アプリを作成」。ユースケースで **Threads** を選ぶ。
3. アプリに **Threads API** を追加し、自分のThreadsアカウントを接続（テスター/本人として認可）。
4. Threads API設定画面で **アクセストークンを生成**（自分のアカウント用。スコープに `threads_basic` と `threads_content_publish` を含める）。
5. 取得した短期トークンを**長期トークン（約60日有効）**に交換：
   `GET https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=（アプリのシークレット）&access_token=（短期トークン）`
6. **ユーザーID**を取得：
   `GET https://graph.threads.net/v1.0/me?fields=id&access_token=（長期トークン）` の `id` を控える。

### GitHub Secretsに登録
リポジトリ（kandume4-bit/note-operation）→ Settings → Secrets and variables → Actions → New repository secret:
- `THREADS_ACCESS_TOKEN` = 長期トークン
- `THREADS_USER_ID` = 上記のid

### 動作確認
- リポジトリの Actions タブ →「note to Threads sync」→「Run workflow」で手動実行。
- 初回は既存記事を済み扱いにするだけ（投稿されない）。2回目以降、noteに新規投稿すると毎時のチェックでThreadsへ自動投稿される。
- テストしたい場合は、初回実行後に新しいnote記事を1本投稿し、次の毎時実行（または手動実行）で1件だけ投稿されるか確認。

### 注意：トークンの更新（約60日ごと）
長期トークンは約60日で失効する。失効前に再取得してSecretを更新するか、将来オプションで自動更新（refresh）ステップを追加する（要相談）。失効すると投稿が止まるだけで、noteやリポジトリには影響しない。

---

## 仕組みの全体像

```
[note RSS]（新着を検知）→[整形：タイトル＋抜粋＋URL＋ハッシュタグ]→[Threadsへ自動投稿]
                                                                  └ URLからプレビューカードが自動生成
```

- **RSSフィード**：`https://note.com/tommykaoleo/rss`
- **検知**：Makeが新着アイテムだけを拾う（既出は再投稿しない）
- **時間差**：シナリオの実行間隔（例：15分ごと）が自然なラグになる
- **プレビューカード**：本文にURLを入れるだけで自動生成（画像添付は不要）

---

## IFTTT版セットアップ手順（こちらを使う）

### 事前準備
1. **IFTTT** の無料アカウントを作成（https://ifttt.com/）。
2. **Threadsアカウント**を用意（Instagram連携済みのもの）。

### 手順
1. IFTTTで「**Create**（applet作成）」、または直接 https://ifttt.com/connect/feed/threads を開く。
2. **If This = RSS Feed**：トリガー「**New feed item**」を選び、Feed URL に
   `https://note.com/tommykaoleo/rss` を入力。
3. **Then That = Threads**：アクション「**Post to Threads**（投稿）」を選び、**ThreadsアカウントをOAuth連携**（1回だけ許可）。
4. **投稿本文（テキスト）**のテンプレ（IFTTTの材料 `{{EntryTitle}}` `{{EntryUrl}}` を使う）：

```
{{EntryTitle}}

続きはnoteで
{{EntryUrl}}

#note #投資 #睡眠の質
```

5. 保存（Finish）して applet を **ON**。
6. **プレビューカード**は本文にURL（`{{EntryUrl}}`）が入っていれば自動生成。

### 注意・運用
- IFTTTのRSSトリガーは**新着のみ**発火するので、過去記事の一斉投稿は起きにくい（Makeのような開始位置選択は不要）。最初は1本投稿してテスト確認するのが安全。
- **時間差**：IFTTT無料版はRSSのチェック間隔が概ね1時間ごと。これが自然なラグになる。厳密な遅延が欲しければPubler等の予約投稿ツールを検討。
- **ハッシュタグのジャンル出し分け**：IFTTT無料版は条件分岐が弱い。まずは株式・快眠共通のタグで運用し、こだわるならPublerやIFTTT Pro（フィルター機能）へ。

---

## （旧・参考）Make.com版 ※Threadsネイティブ非対応のため非推奨

> Makeには公式Threadsモジュールが無いため、この方式はHTTP＋Threads APIトークンが必要。トークンを用意できる場合のみ。RSSトリガー部分の設定は参考になる。

### モジュール1：RSS「Watch RSS feed items」（トリガー）
- **URL**：`https://note.com/tommykaoleo/rss`
- **Maximum number of returned results**：`1`〜`3`
- **重要**：初回有効化時に「どこから処理を始めるか」を聞かれたら、**必ず「最新（今この時点）から」を選ぶ**。

### モジュール1：RSS「Watch RSS feed items」（トリガー）
- **URL**：`https://note.com/tommykaoleo/rss`
- **Maximum number of returned results**：`1`〜`3`
- **重要**：初回有効化時に「どこから処理を始めるか」を聞かれたら、**必ず「最新（今この時点）から」を選ぶ**。
  - これを誤ると、フィードにある過去30件を一気にThreadsへ投稿してしまう。最初は「直近1件まで」にして様子を見ると安全。

### モジュール2：Threads「Create a Post」（アクション）
- 接続：作成したThreads接続を選択。
- **Text**（本文）に次のテンプレを貼る（`{{...}}`はRSSの値をマッピング）：

```
{{1.title}}

続きはnoteで↓
{{1.link}}

#note #投資 #睡眠の質
```

- これだけで、投稿時にURLからプレビューカードが自動で付く。

### 実行スケジュール
- シナリオ右下の時計マークで **「15 minutes」ごと**などに設定。
- noteに投稿してから最大15分ほどで自動的にThreadsへ流れる（これが「時間差」になる）。

---

## 発展形：ジャンルで出し分け＋抜粋を添える（任意）

基本形が動いたら、質を上げる拡張。

### A. 抜粋を1行添える
モジュール2のTextを次のようにする（抜粋からHTMLを除き先頭80文字）：

```
{{1.title}}

{{substring(stripHTML(1.description); 0; 80)}}…

続きはnoteで↓
{{1.link}}
```

### B. ハッシュタグをジャンル別に出し分ける（Router）
RSS直後に **Router** を置き、2ルートに分ける。

- **ルート1（快眠）**：フィルタ条件「`{{1.title}}` contains `Day`」
  - ハッシュタグ：`#睡眠の質 #快眠 #働く世代`
- **ルート2（株式・その他）**：フォールバック（上記以外）
  - ハッシュタグ：`#新NISA #投資初心者 #日経平均`

> 連載快眠は「Day○/14｜…」で始まるので「Dayを含む＝快眠」で判別できる。応用編など「Day」を含まない快眠記事は株式タグ側に入る点だけ留意（必要なら条件に `睡眠`/`快眠`/`カフェイン` 等を追加）。

### C. 時間差をしっかり取りたい場合
- 実行間隔を広げる（例：30分・1時間ごと）と、その分ラグが大きくなる。
- 厳密な「投稿の○分後」を狙うなら、Bufferの予約機能のほうが向く（代替ツール参照）。

---

## 重複・暴発を防ぐ要点

- MakeのRSSトリガーは**新着のみ**発火し、処理済みアイテムは記憶するので二重投稿しない。
- ただし**初回有効化時の開始位置**だけは要注意（上記モジュール1の警告）。
- テスト時は「Run once」で1件だけ流して、Threadsの見え方（プレビューカード）を確認してから定期実行をON。

---

## 代替ツール

| ツール | 特徴 |
|--------|------|
| **IFTTT** | 最も簡単。「RSS feed → Threads」レシピを作るだけ。ただし整形・分岐は弱い |
| **Buffer** | 予約投稿が得意。「時間差」を厳密に設定したいならこれ。RSS連携やThreadsチャンネル対応 |
| **Zapier** | 高機能だがThreads対応は要確認。RSS by Zapier → Threads |

---

## 運用メモ

- 投稿が流れたら `logs/published.md` の該当行の「Threads済」を○にする（手動 or 余裕があれば後日自動化）。
- Threads文の質をもっと上げたくなったら、将来「Threads公式API＋自作」方式に切り替え、毎朝生成している“整えたThreads短文”をそのまま流す構成も可能（その場合はMetaトークンの用意が必要）。
- noteのRSS URL：`https://note.com/tommykaoleo/rss`
