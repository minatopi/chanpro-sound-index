import json
import os
import re
import sys
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


# ============================================================
# 設定
# ============================================================

DATA_FILE = "data.json"
OUTPUT_FILE = "sound.json"

PROFILE_WAIT_MS = 8000

BASE_URL = "https://chanpro.jp"


# ============================================================
# 共通
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def safe_int(value, default=0):
    try:
        if value is None:
            return default

        if isinstance(value, int):
            return value

        text = str(value).replace(",", "").strip()

        match = re.search(r"\d+", text)

        if not match:
            return default

        return int(match.group(0))

    except Exception:
        return default


# ============================================================
# data.json
# ============================================================

def load_data():
    """
    data.jsonから監視対象プロフィールURLを取得する。

    形式:

    [
      "https://chanpro.jp/00-program-profile/..."
    ]
    """

    if not os.path.exists(DATA_FILE):
        print(f"ERROR: {DATA_FILE} がありません。")
        sys.exit(1)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    except Exception as e:
        print(f"ERROR: {DATA_FILE} の読み込みに失敗しました。")
        print(repr(e))
        sys.exit(1)

    if not isinstance(data, list):
        print(f"ERROR: {DATA_FILE} は配列形式にしてください。")
        sys.exit(1)

    urls = []

    for value in data:

        if not isinstance(value, str):
            continue

        url = value.strip()

        if not url:
            continue

        if not url.startswith(
            "https://chanpro.jp/00-program-profile/"
        ):
            print(
                f"WARNING: ChanProプロフィールURLではありません: {url}"
            )
            continue

        if url not in urls:
            urls.append(url)

    if not urls:
        print("ERROR: 監視対象プロフィールURLがありません。")
        sys.exit(1)

    return urls


# ============================================================
# 前回状態
# ============================================================

def load_previous_state():
    """
    sound.jsonに前回の取得結果があれば読み込む。
    初回はNone。
    """

    if not os.path.exists(OUTPUT_FILE):
        return None

    try:
        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return None

        return data

    except Exception as e:
        print("WARNING: sound.jsonを読み込めませんでした。")
        print(repr(e))
        return None


# ============================================================
# URL正規化
# ============================================================

def normalize_url(url):
    """
    相対URLを絶対URLに変換。
    """

    if not url:
        return None

    url = str(url).strip()

    if not url:
        return None

    if url.startswith("/"):
        return BASE_URL + url

    if url.startswith("http://"):
        return url

    if url.startswith("https://"):
        return url

    return None


# ============================================================
# カードURL
# ============================================================

def get_card_url(card):
    """
    カード内部のリンクからURLを取得。
    """

    try:

        links = card.locator("a")

        count = links.count()

        for i in range(count):

            try:

                href = links.nth(i).get_attribute("href")

                if not href:
                    continue

                href = normalize_url(href)

                if href:
                    return href

            except Exception:
                continue

    except Exception:
        pass

    return None


# ============================================================
# プロフィールカード解析
# ============================================================

def parse_card(card):
    """
    プロフィールカードから、

    title
    likes
    views

    を取得。

    想定:

        タイトル
        Lv.10
        1252
        3045

    → likes = 1252
      views = 3045

    いいね0の場合:

        タイトル
        Lv.10
        3045

    → likes = 0
      views = 3045
    """

    try:
        text = card.inner_text()

    except Exception as e:
        print("カードのinner_text取得失敗:")
        print(repr(e))
        return None

    lines = [
        line.strip()
        for line in text.split("\n")
        if line.strip()
    ]

    # ログインを除外
    lines = [
        line
        for line in lines
        if line != "ログイン"
    ]

    # Lv.10などを除外
    lines = [
        line
        for line in lines
        if not line.startswith("Lv.")
    ]

    if not lines:
        return None

    # --------------------------------------------------------
    # 1行目をタイトルとする
    # --------------------------------------------------------

    title = lines[0]

    # --------------------------------------------------------
    # 数字だけの行を抽出
    # --------------------------------------------------------

    numbers = []

    for line in lines[1:]:

        value = line.replace(",", "").strip()

        if re.fullmatch(r"\d+", value):

            try:
                numbers.append(
                    int(value)
                )

            except Exception:
                pass

    # --------------------------------------------------------
    # いいね / 閲覧数
    # --------------------------------------------------------

    if len(numbers) >= 2:

        likes = numbers[0]
        views = numbers[1]

    elif len(numbers) == 1:

        # いいね0で表示が空欄の場合
        likes = 0
        views = numbers[0]

    else:

        likes = 0
        views = 0

    return {
        "title": title,
        "likes": likes,
        "views": views
    }


# ============================================================
# プロフィール取得
# ============================================================

def scrape_profile(page, profile_url):
    """
    ChanProプロフィールページから
    作品一覧を取得。
    """

    print()
    print("=" * 70)
    print("プロフィール取得")
    print(profile_url)
    print("=" * 70)

    works = []

    try:

        page.goto(
            profile_url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(
            PROFILE_WAIT_MS
        )

        # ----------------------------------------------------
        # 動作確認済みのプロフィールコンテナ
        # ----------------------------------------------------

        container = page.locator(
            "div.bubble-element.Group.baTcwaH1"
        ).first

        container.wait_for(
            state="visible",
            timeout=30000
        )

        cards = container.locator(
            "div.clickable-element"
        )

        count = cards.count()

        print(
            f"作品カード数: {count}"
        )

        for i in range(count):

            try:

                card = cards.nth(i)

                parsed = parse_card(card)

                if not parsed:
                    continue

                card_url = get_card_url(card)

                parsed["url"] = card_url

                # ------------------------------------------------
                # 作品識別キー
                #
                # URLがあればURL。
                # URLがなければタイトル。
                # ------------------------------------------------

                if card_url:
                    key = card_url
                else:
                    key = parsed["title"]

                parsed["key"] = key

                works.append(parsed)

                print()
                print(
                    f"[{i + 1}/{count}]"
                )

                print(
                    f"タイトル: {parsed['title']}"
                )

                print(
                    f"いいね: {parsed['likes']}"
                )

                print(
                    f"閲覧数: {parsed['views']}"
                )

                print(
                    f"URL: {card_url}"
                )

            except Exception as e:

                print()
                print(
                    f"CARD {i + 1} 取得失敗"
                )

                print(
                    repr(e)
                )

    except Exception as e:

        print()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("プロフィール取得失敗")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        print(
            profile_url
        )

        print(
            repr(e)
        )

        print()

        return None

    return works


# ============================================================
# 前回作品データ
# ============================================================

def get_previous_programs(previous_state):
    """
    前回のsound.jsonから作品データを辞書化。
    """

    if not isinstance(previous_state, dict):
        return {}

    programs = previous_state.get(
        "programs",
        {}
    )

    if not isinstance(programs, dict):
        return {}

    return programs


# ============================================================
# いいね比較
# ============================================================

def compare_likes(
    previous_programs,
    current_programs,
    first_run
):
    """
    前回と今回のいいね数を比較。

    初回:
        通知対象なし

    増加:
        increase > 0
    """

    increases = []

    for program in current_programs:

        key = program["key"]

        current_likes = safe_int(
            program.get("likes"),
            0
        )

        old_program = previous_programs.get(
            key
        )

        # ----------------------------------------------------
        # 初回 / 新規作品
        # ----------------------------------------------------

        if old_program is None:

            print()
            print(
                f"初回登録: {program['title']}"
            )

            print(
                f"いいね: {current_likes}"
            )

            continue

        old_likes = safe_int(
            old_program.get("likes"),
            0
        )

        diff = current_likes - old_likes

        print()
        print(
            f"比較: {program['title']}"
        )

        print(
            f"  前回: {old_likes}"
        )

        print(
            f"  今回: {current_likes}"
        )

        print(
            f"  増減: {diff:+d}"
        )

        if current_likes > old_likes:

            increases.append({
                "key": key,
                "title": program["title"],
                "url": program.get("url"),
                "old_likes": old_likes,
                "new_likes": current_likes,
                "increase": diff
            })

    return increases


# ============================================================
# sound.json生成
# ============================================================

def build_output(
    profile_url,
    works,
    increases,
    first_run
):
    """
    sound.jsonのデータを作成。
    """

    programs = {}

    for work in works:

        key = work["key"]

        programs[key] = {
            "title": work["title"],
            "url": work.get("url"),
            "likes": safe_int(
                work.get("likes"),
                0
            ),
            "views": safe_int(
                work.get("views"),
                0
            ),
            "updated_at": now_iso()
        }

    output = {
        "updated_at": now_iso(),

        "profile_url": profile_url,

        "first_run": first_run,

        "program_count": len(works),

        "like_increases": increases,

        "programs": programs
    }

    return output


# ============================================================
# JSON保存
# ============================================================

def save_output(data):
    """
    sound.jsonを安全に保存。
    """

    temp_file = OUTPUT_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        OUTPUT_FILE
    )

    print()
    print("=" * 70)
    print(
        f"{OUTPUT_FILE} 保存完了"
    )
    print("=" * 70)


# ============================================================
# メイン
# ============================================================

def main():

    started_at = now_iso()

    print()
    print("=" * 70)
    print("ChanPro Sound Index")
    print("=" * 70)

    print(
        f"開始: {started_at}"
    )

    # --------------------------------------------------------
    # 監視URL
    # --------------------------------------------------------

    profile_urls = load_data()

    print()
    print(
        f"監視プロフィール数: {len(profile_urls)}"
    )

    for url in profile_urls:
        print(
            f"  - {url}"
        )

    # --------------------------------------------------------
    # 前回状態
    # --------------------------------------------------------

    previous_state = load_previous_state()

    first_run = previous_state is None

    if first_run:

        print()
        print(
            "★ 初回実行です"
        )

        print(
            "★ 初回はいいね増加を通知対象にしません"
        )

    # --------------------------------------------------------
    # 現在は1プロフィールを想定
    #
    # data.jsonに1件だけ入れる仕様なので
    # 最初のURLを使用。
    # --------------------------------------------------------

    profile_url = profile_urls[0]

    # --------------------------------------------------------
    # Playwright
    # --------------------------------------------------------

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 2000
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/120.0.0.0 "
                "Safari/537.36"
            )
        )

        # ----------------------------------------------------
        # プロフィール取得
        # ----------------------------------------------------

        works = scrape_profile(
            page,
            profile_url
        )

        browser.close()

    # --------------------------------------------------------
    # 取得失敗
    #
    # 重要:
    # 取得失敗時に空データで上書きしない。
    # --------------------------------------------------------

    if works is None:

        print()
        print("ERROR: プロフィール取得に失敗しました。")
        print(
            "sound.jsonは上書きしません。"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # 前回作品
    # --------------------------------------------------------

    previous_programs = get_previous_programs(
        previous_state
    )

    # --------------------------------------------------------
    # いいね比較
    # --------------------------------------------------------

    increases = compare_likes(
        previous_programs,
        works,
        first_run
    )

    # --------------------------------------------------------
    # 結果表示
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("いいね増加結果")
    print("=" * 70)

    if first_run:

        print(
            "初回実行のため通知対象なし"
        )

    elif increases:

        for increase in increases:

            print()
            print(
                f"★ {increase['title']}"
            )

            print(
                f"  {increase['old_likes']}"
                f" → "
                f"{increase['new_likes']}"
            )

            print(
                f"  +{increase['increase']}"
            )

    else:

        print(
            "いいね増加なし"
        )

    # --------------------------------------------------------
    # sound.json
    # --------------------------------------------------------

    output = build_output(
        profile_url=profile_url,
        works=works,
        increases=increases,
        first_run=first_run
    )

    save_output(
        output
    )

    # --------------------------------------------------------
    # 完了
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("処理完了")
    print("=" * 70)

    print(
        f"プロフィール: {profile_url}"
    )

    print(
        f"作品数: {len(works)}"
    )

    print(
        f"いいね増加作品数: {len(increases)}"
    )

    print(
        f"完了: {now_iso()}"
    )

    print("=" * 70)


# ============================================================
# 実行
# ============================================================

if __name__ == "__main__":
    main()
