import os, re, sys
from datetime import datetime, date, time, timezone, timedelta
import requests

MOVIE_KEYWORD = os.getenv("MOVIE_KEYWORD", "doomsday").lower()
RELEASE_DATE = date(2026, 12, 18)   # change to the real India release date
CITY_SLUG = "bengaluru"
IST = timezone(timedelta(hours=5, minutes=30))

WINDOWS = [
    (time(23, 0), time(1, 0)),
    (time(6, 0), time(8, 0)),
    (time(21, 30), time(22, 30)),
]

URL = f"https://in.bookmyshow.com/explore/movies-{CITY_SLUG}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}
BOOKING_HINTS = re.compile(r"book\s*(tickets|now)|buy\s*tickets|select\s*seats|buytickets", re.I)


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


def notify(msg, title="Avengers Doomsday", priority="urgent"):
    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set:", msg)
        return
    r = requests.post(f"https://ntfy.sh/{topic}", data=msg.encode("utf-8"),
                      headers={"Title": title, "Priority": priority}, timeout=20)
    print("ntfy status:", r.status_code)


def check_bms():
    """Returns 'live', 'not_live' or 'error'."""
    try:
        r = requests.get(URL, headers=HEADERS, timeout=25)
    except requests.RequestException as e:
        print("BMS request error:", e)
        return "error"
    if r.status_code != 200:
        print(f"BMS -> HTTP {r.status_code}")
        return "error"
    text = r.text
    idx = text.lower().find(MOVIE_KEYWORD)
    if idx == -1:
        print("BookMyShow: movie not listed")
        return "not_live"
    context = text[max(0, idx - 1500): idx + 1500]
    if BOOKING_HINTS.search(context):
        return "live"
    print("BookMyShow: movie listed, but no booking wording yet")
    return "not_live"


def main():
    if "--test" in sys.argv:
        notify("Ticket watcher: test alert works")
        return
    now = datetime.now(IST)
    if "--force" not in sys.argv and not should_run(now):
        print(f"{now:%H:%M IST} - not a check slot, skipping")
        return

    print(f"{now:%Y-%m-%d %H:%M IST} - checking for '{MOVIE_KEYWORD}'")
    result = check_bms()
    if result == "live":
        notify(f"Avengers: Doomsday tickets may be LIVE!\n{URL}")
    elif result == "error":
        notify("BookMyShow check FAILED (blocked or down). Not a 'not live' result.",
               title="Watcher problem", priority="default")
    else:
        print("Not live yet")


if __name__ == "__main__":
    main()