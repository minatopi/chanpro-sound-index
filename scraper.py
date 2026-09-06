
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import json
import re
import time


# ============================================================
# 設定
# ============================================================

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"

OUTPUT_FILE = "sound.json"


# ============================================================
# タイトルをきれいにする
# ============================================================

def clean_title(title: str) -> str:
    title = title.strip()

    # 改行・連続スペースを1個にする
    title = re.sub(r"\s+", " ", title)

    return title


# ============================================================
# プログラムの種類を判定
# ============================================================

def classify(title: str) -> str:

    # サウンド系
    if (
        "サウンドプログラミング" in title
        or "サウンドプログラム" in title
    ):
        return "sound"

    # テキスト・コード系
    if (
        "Python" in title
        or "HTML" in title
        or "テキスト" in title
    ):
        return "text"

    return "other"


# ============================================================
# 現在時刻
# ============================================================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# URLを正規化
# ============================================================

def clean_url(url: str) -> str:

    if not url:
        return ""

    url = url.strip()

    # 万一 Markdown の
    # [https://example.com](https://example.com)
    # のようになっていた場合にURLだけ取り出す
    match = re.match(
        r"^\[.*?\]\((https?://.*?)\)$",
        url
    )

    if match:
        url = match.group(1)

    return url


# ============================================================
# プログラムを取得
# ============================================================

def scrape():

    results = {}

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        # ----------------------------------------------------
        # 通信確認
        # ----------------------------------------------------

        page.on(
            "response",
            lambda response: print(
                "RESPONSE:",
                response.status,
                response.url
            )
        )

        # ----------------------------------------------------
        # プロフィールページを開く
        # ----------------------------------------------------

        print()
        print("========================================")
        print("プロフィールページを開いています")
        print("========================================")
        print()

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        # ページの読み込み待ち
        page.wait_for_timeout(10000)

        # ----------------------------------------------------
        # カード取得
        # ----------------------------------------------------

        cards = page.locator(
            "div.clickable-element"
        )

        count = cards.count()

        print()
        print("カード数:", count)
        print()

        # ----------------------------------------------------
        # 全カード処理
        # ----------------------------------------------------

        for i in range(count):

            print("----------------------------------------")
            print(f"{i + 1} / {count}")
            print("----------------------------------------")

            try:

                # ------------------------------------------------
                # 元ページを毎回確認
                # ------------------------------------------------

                if page.url != URL:
                    page.goto(
                        URL,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    page.wait_for_timeout(3000)

                # カードを再取得
                cards = page.locator(
                    "div.clickable-element"
                )

                card = cards.nth(i)

                # ------------------------------------------------
                # カード本文
                # ------------------------------------------------

                text = card.inner_text()

                lines = [
                    line.strip()
                    for line in text.split("\n")
                    if line.strip()
                ]

                if not lines:
                    print("SKIP: 空のカード")
                    continue

                # ------------------------------------------------
                # タイトル
                # ------------------------------------------------

                title = clean_title(lines[0])

                print("TITLE:", title)

                # ------------------------------------------------
                # 不要なカード
                # ------------------------------------------------

                if title in (
                    "ログイン",
                    "みなと"
                ):
                    print("SKIP: 不要カード")
                    continue

                # ------------------------------------------------
                # 種類
                # ------------------------------------------------

                kind = classify(title)

                print("TYPE:", kind)

                if kind == "other":
                    print("SKIP: 対象外")
                    continue

                # ------------------------------------------------
                # クリック前URL
                # ------------------------------------------------

                before_url = page.url

                print("BEFORE:", before_url)

                # ------------------------------------------------
                # カードをクリック
                # ------------------------------------------------

                card.click(
                    timeout=10000
                )

                # 遷移を待つ
                page.wait_for_timeout(2500)

                # ------------------------------------------------
                # クリック後URL
                # ------------------------------------------------

                new_url = clean_url(
                    page.url
                )

                print("AFTER :", new_url)

                # ------------------------------------------------
                # log URLか確認
                # ------------------------------------------------

                if "00-program-share" not in new_url:
                    print(
                        "WARNING: shareページではありません"
                    )

                # ------------------------------------------------
                # 既存データ取得
                # ------------------------------------------------

                if title not in results:

                    results[title] = {
                        "title": title,
                        "sound_url": "",
                        "text_url": "",
                        "updated": ""
                    }

                item = results[title]

                # ------------------------------------------------
                # URL保存
                # ------------------------------------------------

                if kind == "sound":

                    item["sound_url"] = new_url

                elif kind == "text":

                    item["text_url"] = new_url

                # 更新時刻
                item["updated"] = now_iso()

                print("SAVED:", title)

                # ------------------------------------------------
                # 元ページへ戻る
                # ------------------------------------------------

                page.goto(
                    URL,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(3000)

            except Exception as e:

                print()
                print("ERROR")
                print("INDEX:", i)
                print("ERROR:", repr(e))
                print()

                # エラーが出ても元ページに戻す
                try:

                    page.goto(
                        URL,
                        wait_until="domcontentloaded",
                        timeout=60000
                    )

                    page.wait_for_timeout(3000)

                except Exception as e2:

                    print(
                        "RETURN ERROR:",
                        repr(e2)
                    )

                continue

        # ----------------------------------------------------
        # ブラウザ終了
        # ----------------------------------------------------

        browser.close()

    return list(results.values())


# ============================================================
# JSON保存
# ============================================================

def save_json(data):

    output = {
        "last_updated": now_iso(),
        "count": len(data),
        "programs": data
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    return output


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":

    print()
    print("========================================")
    print("Chanpro プログラム取得開始")
    print("========================================")
    print()

    data = scrape()

    output = save_json(data)

    print()
    print("========================================")
    print("取得完了")
    print("========================================")
    print()

    print(
        "保存先:",
        OUTPUT_FILE
    )

    print(
        "COUNT:",
        output["count"]
    )

    print()

    for i, program in enumerate(
        output["programs"],
        start=1
    ):

        print(
            f"{i}.",
            program["title"]
        )

        if program["sound_url"]:
            print(
                "   sound:",
                program["sound_url"]
            )

        if program["text_url"]:
            print(
                "   text :",
                program["text_url"]
            )

    print()
    print("SAVED sound.json")

