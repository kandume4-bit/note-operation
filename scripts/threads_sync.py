#!/usr/bin/env python3
"""
note RSS -> Threads 自動同期スクリプト（GitHub Actionsから定期実行）

- note RSS の新着記事を検知し、Threads API で自動投稿する。
- 投稿済みは logs/threads-synced.json で記録し、重複投稿を防ぐ。
- 初回実行時は「その時点の既存記事をすべて済み扱い」にして投稿しない
  （過去記事の一斉投稿を防ぐ）。以降の新着だけが対象。
- 本文にnote URLを入れるので、Threads側でプレビューカードが自動生成される。

必要な環境変数（GitHub Secrets）:
  THREADS_ACCESS_TOKEN : Threads API の長期アクセストークン
  THREADS_USER_ID      : Threads ユーザーID（数値）

依存ライブラリなし（Python標準ライブラリのみ）。
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://note.com/tommykaoleo/rss"
STATE_PATH = "logs/threads-synced.json"
GRAPH = "https://graph.threads.net/v1.0"

TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
USER_ID = os.environ.get("THREADS_USER_ID", "")


def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "note-threads-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
    root = ET.fromstring(data)
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link).strip()
        if link:
            items.append({"title": title, "link": link, "guid": guid})
    return items  # note RSSは新しい順


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"posted": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def hashtags(title):
    # タイトルで連載ジャンルを判定してハッシュタグを出し分ける
    if "糖尿病" in title or "インスリン" in title:
        return "#1型糖尿病 #糖尿病 #エッセイ #闘病記"
    if "Day" in title:
        return "#睡眠の質 #快眠 #働く世代"
    return "#新NISA #投資初心者 #日経平均"


def compose(item):
    return f"{item['title']}\n\n続きはnoteで\n{item['link']}\n\n{hashtags(item['title'])}"


def _post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def post_to_threads(text):
    # 1) コンテナ作成
    created = _post(
        f"{GRAPH}/{USER_ID}/threads",
        {"media_type": "TEXT", "text": text, "access_token": TOKEN},
    )
    creation_id = created["id"]
    # Threadsはコンテナ作成直後の公開で稀に失敗するため軽く待つ
    time.sleep(5)
    # 2) 公開
    published = _post(
        f"{GRAPH}/{USER_ID}/threads_publish",
        {"creation_id": creation_id, "access_token": TOKEN},
    )
    return published.get("id", "")


def main():
    if not TOKEN or not USER_ID:
        print("THREADS_ACCESS_TOKEN / THREADS_USER_ID が未設定です。", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    posted = set(state.get("posted", []))
    items = fetch_rss()

    # 初回（状態が空）は既存をすべて済み扱いにし、投稿しない（過去記事の暴発防止）
    if not posted:
        state["posted"] = [it["guid"] for it in items]
        save_state(state)
        print(f"初回初期化：既存{len(items)}件を済み扱い（投稿なし）。次回以降の新着から同期します。")
        return

    # 新着のみ、古い順に投稿（連載の順序を保つ）
    new_items = [it for it in items if it["guid"] not in posted]
    new_items.reverse()

    count = 0
    for it in new_items:
        try:
            pid = post_to_threads(compose(it))
            posted.add(it["guid"])
            count += 1
            print(f"投稿成功: {it['title']} -> {pid}")
        except Exception as e:  # noqa: BLE001
            print(f"投稿失敗: {it['title']} : {e}", file=sys.stderr)

    state["posted"] = list(posted)
    save_state(state)
    print(f"完了。新規投稿 {count} 件。")


if __name__ == "__main__":
    main()
