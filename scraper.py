from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import json
import re

URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"


def normalize_title(title: str):
    """HTML版とPython版を同じタイトルにする"""
    t = title

    t = t.replace("　HTML版", "")
    t = t.replace("HTML版", "")

    # 外側の「」
    t = t.strip("「」")

    return t.strip()


def scrape():

    songs = {}

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(5000)

        cards = page.locator(
            "div.clickable-element.bubble-element.Group.baTdaPaJ"
        )

        print("cards:", cards.count())

        for i in range(cards.count()):

            card = cards.nth(i)

            try:

                title = card.locator(
                    "div.bubble-element.Text.baTdaPaP"
                ).inner_text().strip()

            except:
                continue

            if "サウンドプログラミング" not in title:
                continue

            nums = re.findall(r"\d+", card.inner_text())

            like = int(nums[0]) if len(nums) >= 1 else 0
            views = int(nums[1]) if len(nums) >= 2 else 0

            # -------------------
            # URL取得
            # -------------------

            with page.expect_navigation():

                card.click()

            url = page.url

            page.go_back(wait_until="networkidle")

            page.wait_for_timeout(1000)

            key = normalize_title(title)

            if key not in songs:

                songs[key] = {
                    "title": key,
                    "python_url": None,
                    "html_url": None,
                    "python_like": None,
                    "python_views": None,
                    "html_like": None,
                    "html_views": None
                }

            if "HTML版" in title:

                songs[key]["html_url"] = url
                songs[key]["html_like"] = like
                songs[key]["html_views"] = views

            else:

                songs[key]["python_url"] = url
                songs[key]["python_like"] = like
                songs[key]["python_views"] = views

        browser.close()

    return list(songs.values())


if __name__ == "__main__":

    songs = scrape()

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "count": len(songs),
        "songs": songs
    }

    with open("sound.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("saved:", len(songs))
