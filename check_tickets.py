import os, re, sys, subprocess
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
import requests

MOVIE_KEYWORD = "doomsday"
RELEASE_DATE = date(2026, 12, 18)   # verify the India release date
CITY_SLUG = "bengaluru"
IST = ZoneInfo("Asia/Kolkata")

# IST windows (start, end); the first one wraps past midnight
WINDOWS = [
    (time(23, 0), time(1, 0)),
    (time(6, 0), time(8, 0)),
    (time(21, 30), time(22, 30)),
]

SOURCES = {
    "BookMyShow": [
        f"https://in.bookmyshow.com/explore/movies-{CITY_SLUG}",
        f"https://in.bookmyshow.com/search?q=avengers%20doomsday",
    ],
    "PVR INOX": [
        "https://www.pvrcinemas.com/",
        "https://www.pvrcinemas.com/cinemas/nowshowing",
    ],
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}
BOOKING_HINTS = re.compile(r"book\s*(tickets|now)|buy\s*tickets|select\s*seats", re.I)


def in_window(t):
    for s, e in WINDOWS:
        if (s <= t < e) if s < e else (t >= s or t < e):
            return True
    return False


def interval_hours(days_left):
    if days_left > 45: return None
    if days_left > 21: return 6
    if days_left > 7:  return 2
    return 1


def should_run(now):
    if in_window(now.time()):
        return True
    iv = interval_hours((RELEASE_DATE - now.date()).days)
    return iv is not None and now.hour % iv == 0 and now.minute < 30


def check(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code != 200:
            print(f"  {url} -> HTTP {r.status_code} (possibly blocked)")
            return False
        text = r.text
        idx = text.lower().find(MOVIE_KEYWORD)
        if idx == -1:
            return False
        # look for booking language near the movie mention
        context = text[max(0, idx - 1500): idx + 1500]
        return bool(BOOKING_HINTS.search(context))
    except requests.RequestException as e:
        print(f"  {url} -> error {e}")
        return False


def notify(msg):
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("No Telegram creds set:", msg); return
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  data={"chat_id": chat, "text": msg}, timeout=20)


def main():
    if "--test" in sys.argv:
        notify("✅ Avengers Doomsday ticket watcher: test alert works"); return
    now = datetime.now(IST)
    if "--force" not in sys.argv and not should_run(now):
        print(f"{now:%H:%M IST} - not a check slot, skipping"); return

    print(f"{now:%Y-%m-%d %H:%M IST} - checking")
    hits = [(site, url) for site, urls in SOURCES.items() for url in urls if check(url)]
    if hits:
        lines = "\n".join(f"{s}: {u}" for s, u in hits)
        notify(f"🎬 Avengers: Doomsday tickets may be LIVE!\n{lines}")
        if os.getenv("GITHUB_ACTIONS"):
            subprocess.run(["gh", "workflow", "disable", "ticket-check.yml"])
    else:
        print("Not live yet")


if __name__ == "__main__":
    main()
