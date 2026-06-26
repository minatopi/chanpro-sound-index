from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import json
import re


URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"


def clean(s):
    return re.sub(r"\s+", " ", s.strip())


def get_type(title):

    if "サウンドプログラミング" in title:
        return "sound"

    if (
        "Python" in title
        or "HTML" in title
        or "コード" in title
    ):
        return "text"

    return None



def scrape():

    data = {}

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()


        page.goto(
            URL,
            wait_until="domcontentloaded"
        )

        page.wait_for_timeout(8000)


        cards = page.locator(
            "div.clickable-element"
        )


        for i in range(cards.count()):

            card = cards.nth(i)

            try:

                title = clean(
                    card.locator(
                        "div.bubble-element.Text"
                    ).first.inner_text()
                )


                kind = get_type(title)

                if not kind:
                    continue


                print(title)


                # クリック前
                before = page.url


                # 新しいURL監視
                with page.expect_popup(
                    timeout=3000
                ) as popup:

                    card.click()


                new_page = popup.value

                new_page.wait_for_load_state(
                    "domcontentloaded"
                )


                target = new_page.url


                print(
                    "FOUND:",
                    target
                )


                new_page.close()



                item = data.setdefault(
                    title,
                    {
                        "title": title,
                        "sound_url": "",
                        "text_url": "",
                        "updated": ""
                    }
                )


                if kind == "sound":

                    item["sound_url"] = target


                if kind == "text":

                    item["text_url"] = target


                item["updated"] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )


            except Exception as e:

                # popupなしの場合
                print(
                    "skip",
                    i,
                    e
                )


        browser.close()


    return list(data.values())




if __name__ == "__main__":


    result = scrape()


    output = {

        "last_updated":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "count":
            len(result),

        "programs":
            result

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
        "saved",
        len(result)
    )
