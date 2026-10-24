import os, re, sys, requests

URLS = [
    "https://in.bookmyshow.com/explore/movies-bengaluru",
    "https://www.pvrcinemas.com/",
    "https://www.pvrcinemas.com/cinemas/nowshowing",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
}
known = sys.argv[1].lower() if len(sys.argv) > 1 else None
lines = []

for i, url in enumerate(URLS):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
    except Exception as e:
        lines.append(f"{url}\n  ERROR: {e}\n")
        continue
    html = r.text
    open(f"page_{i}.html", "w", encoding="utf-8").write(html)
    low = html.lower()
    out = [url,
           f"  status: {r.status_code} | size: {len(html):,} chars",
           f"  script tags: {len(re.findall(r'<script', html, re.I))}"]
    if known:
        out.append(f"  contains '{known}': {known in low}")
    if re.search(r"captcha|access denied|are you a robot", html, re.I):
        out.append("  WARNING: looks like a bot-block page")
    lines.append("\n".join(out) + "\n")

report = "\n".join(lines)
print(report)

topic = os.getenv("NTFY_TOPIC")
if topic:
    r = requests.post(f"https://ntfy.sh/{topic}", data=report.encode("utf-8"),
                      headers={"Title": "Scraper diagnosis", "Tags": "mag"}, timeout=20)
    print("ntfy status:", r.status_code)
else:
    print("NTFY_TOPIC not set, no notification sent")