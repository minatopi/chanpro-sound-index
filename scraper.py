from playwright.sync_api import sync_playwright


URL = "https://chanpro.jp/00-program-profile/1724731678594x659718187856833700"


with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page()

    # 通信ログ保存
    responses = []

    def log_response(response):
        u = response.url

        if (
            "api" in u
            or "program" in u
            or "share" in u
        ):
            responses.append(u)

            print("\n--- RESPONSE ---")
            print(u)


    page.on(
        "response",
        log_response
    )


    page.goto(
        URL,
        wait_until="networkidle"
    )

    page.wait_for_timeout(5000)


    cards = page.locator(
        "div.clickable-element.bubble-element.Group"
    )


    print(
        "cards:",
        cards.count()
    )


    # サウンドだけ探す

    for i in range(cards.count()):

        card = cards.nth(i)

        try:

            text = card.inner_text()

        except:
            continue


        if "サウンドプログラミング" not in text:
            continue


        print("\n===================")
        print("TITLE")
        print(text)


        print("\nCLICK")


        before = page.url


        card.click(
            force=True
        )


        page.wait_for_timeout(3000)


        after = page.url


        print("before:")
        print(before)

        print("after:")
        print(after)


        print("\nHTML")
        print(
            card.evaluate(
                "e => e.outerHTML"
            )[:2000]
        )


        break


    print("\n\n通信一覧")

    for r in responses:
        print(r)


    browser.close()
