from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import json
import re
import time


URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"


def clean_title(t):
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def classify(title):
    if "サウンドプログラミング" in title:
        return "sound"

    if "Python" in title or "HTML" in title or "テキスト" in title:
        return "text"

    return "other"



def scrape():

    results = {}

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()


        # 通信確認用
        page.on(
            "response",
            lambda r: print(
                "RESPONSE:",
                r.url
            )
        )


        page.goto(
            URL,
            wait_until="domcontentloaded"
        )


        page.wait_for_timeout(10000)


        cards = page.locator(
            "div.clickable-element"
        )

        count = cards.count()

        print(
            "cards:",
            count
        )


        for i in range(count):

            try:

                card = cards.nth(i)


                text = card.inner_text()

                lines = [
                    x.strip()
                    for x in text.split("\n")
                    if x.strip()
                ]


                if not lines:
                    continue


                title = clean_title(lines[0])


                if title in [
                    "ログイン",
                    "みなと"
                ]:
                    continue


                kind = classify(title)


                if kind == "other":
                    continue


                print()
                print("TITLE")
                print(title)


                old = page.url


                # navigation禁止
                card.click(
                    timeout=5000
                )


                page.wait_for_timeout(
                    2000
                )


                new = page.url


                print(
                    "before:",
                    old
                )

                print(
                    "after:",
                    new
                )


                item = results.setdefault(
                    title,
                    {
                        "title": title,
                        "sound_url": "",
                        "text_url": "",
                        "updated": ""
                    }
                )


                if kind == "sound":

                    item["sound_url"] = new


                elif kind == "text":

                    item["text_url"] = new


                item["updated"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )


                # 戻る
                page.goto(
                    URL,
                    wait_until="domcontentloaded"
                )

                page.wait_for_timeout(5000)


            except Exception as e:

                print(
                    "ERROR",
                    i,
                    e
                )


        browser.close()


    return list(results.values())



if __name__ == "__main__":


    data = scrape()


    output = {

        "last_updated":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(data),

        "programs":
            data

    }


    with open(
        "sound.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )


    print(
        "SAVED sound.json"
    )

    print(
        "COUNT:",
        len(data)
    )
