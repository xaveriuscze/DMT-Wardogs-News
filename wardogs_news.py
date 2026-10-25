
import os
import json
import re
import html
import urllib.request
import urllib.parse
from pathlib import Path

APP_ID = 1867240
STATE = Path("seen_news.json")

WEBHOOKS = {
    "ASSAULT": os.getenv("DISCORD_ASSAULT"),
    "RECON": os.getenv("DISCORD_RECON"),
    "ARMOR": os.getenv("DISCORD_ARMOR"),
    "AIR": os.getenv("DISCORD_AIR"),
    "BUILDING": os.getenv("DISCORD_BUILDING"),
}

KEYWORDS = {
    "ASSAULT": [
        "assault", "rifle", "smg", "shotgun", "grenade",
        "infantry", "pistol", "recoil", "molotov", "c4"
    ],
    "RECON": [
        "recon", "sniper", "marksman", "scope",
        "ghillie", "thermal", "spotting", "rangefinder"
    ],
    "ARMOR": [
        "tank", "armor", "armour", "apc", "ifv",
        "ciws", "cannon", "vehicle", "havoc"
    ],
    "AIR": [
        "helicopter", "aircraft", "pilot", "aviation",
        "flight", "rocket pod", "air support", "havoc"
    ],
    "BUILDING": [
        "fob", "building", "construction", "supply",
        "supplies", "logistics", "fortification",
        "resupply", "repair station"
    ],
}


def request_json(url, payload=None):
    data = None
    headers = {"User-Agent": "DMT-Wardogs-News/1.0"}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url, data=data, headers=headers
    )
    with urllib.request.urlopen(req, timeout=25) as res:
        return json.loads(res.read().decode("utf-8"))


def get_news():
    query = urllib.parse.urlencode({
        "appid": APP_ID,
        "count": 20,
        "maxlength": 0,
    })
    url = (
        "https://api.steampowered.com/"
        "ISteamNews/GetNewsForApp/v2/?" + query
    )
    result = request_json(url)
    return result["appnews"]["newsitems"]


def clean_text(raw):
    raw = re.sub(r"\[/?[a-zA-Z][^\]]*\]", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return html.unescape(raw)


def classify(text):
    text = text.lower()
    return [
        squad for squad, words in KEYWORDS.items()
        if any(re.search(
            r"(?<!\w)" + re.escape(word) + r"(?!\w)",
            text
        ) for word in words)
    ]


def send(webhook, squad, item, excerpt):
    payload = {
        "username": "DMT | WARDOGS NEWS",
        "allowed_mentions": {"parse": []},
        "embeds": [{
            "title": item["title"][:256],
            "url": item["url"],
            "description": excerpt[:3500],
            "color": 15158332,
            "footer": {
                "text": f"DMT | {squad} SQUAD | Steam"
            }
        }]
    }
    request_json(webhook, payload)


def main():
    items = get_news()
    if STATE.exists():
        seen = set(json.loads(STATE.read_text()))
    else:
        # První spuštění: uloží existující zprávy
        # a nezahlcuje Discord starými aktualizacemi.
        STATE.write_text(json.dumps(
            [x["gid"] for x in items], indent=2
        ))
        print("Inicializace dokončena.")
        return

    for item in reversed(items):
        gid = item["gid"]
        if gid in seen:
            continue

        content = clean_text(item.get("contents", ""))
        title = item.get("title", "")
        sections = re.split(r"[\r\n]+", content)

        for squad, webhook in WEBHOOKS.items():
            if not webhook:
                continue

            matched = [
                line.strip() for line in sections
                if squad in classify(line)
            ]

            if not matched and squad in classify(title):
                matched = [content[:1500]]

            if matched:
                excerpt = "\n".join(matched)[:3500]
                send(webhook, squad, item, excerpt)
                print(f"Odesláno: {squad} - {title}")

        seen.add(gid)

    STATE.write_text(json.dumps(
        sorted(seen), indent=2
    ))


if __name__ == "__main__":
    main()
