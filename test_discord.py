
import os
import json
import urllib.request
import urllib.error

webhooks = {
    "ASSAULT": os.getenv("DISCORD_ASSAULT"),
    "RECON": os.getenv("DISCORD_RECON"),
    "ARMOR": os.getenv("DISCORD_ARMOR"),
    "AIR": os.getenv("DISCORD_AIR"),
    "BUILDING": os.getenv("DISCORD_BUILDING"),
}

for squad, url in webhooks.items():
    if not url:
        print(f"CHYBA: Chybi webhook pro {squad}")
        continue

    message = {
        "username": "DMT | WARDOGS NEWS",
        "content": (
            f"**DMT NEWS - TEST PRIPOJENI**\n"
            f"Squad: **{squad}**\n"
            "Discord webhook funguje!"
        ),
        "allowed_mentions": {"parse": []}
    }

    data = json.dumps(message).encode("utf-8")
    req = urllib.request.Request(
        url + ("&" if "?" in url else "?") + "wait=true",
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "DMT-Wardogs-News/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            print(f"OK: {squad} - HTTP {res.status}")
    except urllib.error.HTTPError as e:
        print(f"CHYBA: {squad} - HTTP {e.code}")
    except Exception as e:
        print(f"CHYBA: {squad} - {type(e).__name__}")
