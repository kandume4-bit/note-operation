# threads-sync-setup.md — note→Threads 自動同期の構築手順（ノーコード／IFTTT）

noteに投稿した記事を、順次Threadsへ自動で同期する仕組みのセットアップ手順。

> 【2026-06-17 重要な訂正】当初Make.comで構築しようとしたが、**Makeには公式Threadsモジュールが無い**（HTTP＋Threads APIトークンが必要で、トークン不要というメリットが消える）と判明。
> → **トークン不要で最短なのは IFTTT**。「RSS Feed → Threads」の専用レシピがあり、ThreadsのOAuth連携だけで動く。本書はIFTTT版を採用する。
> 代替：Publer（RSS自動投稿＋予約、時間差設定が細かい／RSS機能は有料の場合あり）。

ノーコードツール **IFTTT** を使う。トークン管理は不要（OAuthはIFTTTが処理）。
RSS URL：`https://note.com/tommykaoleo/rss`

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
