import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import argostranslate.package
import argostranslate.translate

APP_ID = 1867240
STATE = Path('seen_news.json')
URL = f'https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?{urllib.parse.urlencode({"appid": APP_ID, "count": 30, "maxlength": 0})}'
WEBHOOKS = {s: os.getenv(f'DISCORD_{s}') for s in ('ASSAULT', 'RECON', 'ARMOR', 'AIR', 'BUILDING')}
TOPICS = {
    'ASSAULT': {
        '🔫 Pěchotní výzbroj': [r'\b(assault rifle|battle rifle|submachine gun|\bsmg\b|\blmg\b|shotgun|infantry weapon|pistol|handgun)\b'],
        '📦 Pěchotní munice': [r'\b(rifle|pistol|smg|infantry|small arms)\b.{0,50}\b(ammo|ammunition|rounds|caliber|calibre|magazine)\b', r'\b(ammo|ammunition|rounds|magazine)\b.{0,50}\b(rifle|pistol|smg|infantry|small arms)\b'],
        '💣 Výbušniny': [r'\b(grenade|molotov|\bc4\b|frag grenade|flashbang|anti-personnel mine)\b'],
        '🪖 Výstroj': [r'\b(body armor|body armour|plate carrier|infantry equipment|ballistic vest)\b'],
    },
    'RECON': {
        '🎯 Odstřelovací výzbroj': [r'\b(sniper|marksman|dmr|bolt.action rifle)\b'],
        '🔭 Optika': [r'\b(sniper scope|rifle scope|rangefinder|binocular|spotting scope|optic)\b'],
        '🌿 Maskování': [r'\b(ghillie|camouflage|concealment)\b'],
        '📡 Průzkum': [r'\b(recon|reconnaissance|spotting|scouting)\b'],
    },
    'ARMOR': {
        '🛡️ Obrněná technika': [r'\b(tank|armored vehicle|armoured vehicle|\bapc\b|\bifv\b|\bmbt\b)\b'],
        '💥 Tanková munice': [r'\b(tank|vehicle|cannon|main gun|120mm|125mm|105mm)\b.{0,60}\b(ammo|ammunition|shell|round|\bapfsds\b|\bheat\b|\bhe\b)\b', r'\b(apfsds|heat.fs|tank shell|tank round)\b'],
        '🔥 Výzbroj vozidel': [r'\b(tank cannon|vehicle cannon|coaxial|autocannon|anti.air gun|\bciws\b)\b'],
        '🔧 Pancíř a opravy': [r'\b(vehicle armor|vehicle armour|tank armor|tank armour|vehicle repair|armor penetration|armour penetration)\b'],
    },
    'AIR': {
        '🚁 Letecká technika': [r'\b(helicopter|aircraft|chopper|gunship|aviation)\b'],
        '🚀 Letecká výzbroj': [r'\b(air.to.ground|air.to.air|rocket pod|helicopter rocket|helicopter missile|aircraft cannon)\b'],
        '📦 Letecká munice': [r'\b(helicopter|aircraft|rocket pod|gunship)\b.{0,60}\b(ammo|ammunition|missile|rocket|rounds)\b'],
        '🛠️ Letové vlastnosti': [r'\b(flight model|flight physics|rotor|flight control|helicopter handling)\b'],
    },
    'BUILDING': {
        '🏗️ FOB a opevnění': [r'\b(\bfob\b|forward operating base|fortification|bunker|emplacement|construction)\b'],
        '🚛 Zásobování': [r'\b(logistics|supply truck|resupply|supply run|supplies|supply delivery)\b'],
        '📦 Materiály': [r'\b(building material|construction material|construction supplies)\b'],
        '🔧 Stavební mechaniky': [r'\b(building system|construction system|repair station|build limit)\b'],
    },
}

_translation_ready = False

def fetch_news():
    req = urllib.request.Request(URL, headers={'User-Agent': 'DMT-News/1.1'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)['appnews']['newsitems']

def plain(raw):
    raw = re.sub(r'\[(?:/p|p|br|/list|list|\*)\]', '\n', raw, flags=re.I)
    raw = re.sub(r'\[/?[^\]\n]+\]', ' ', raw)
    raw = re.sub(r'<[^>]*>', ' ', raw)
    return html.unescape(raw).replace('\r', '\n')

def chunks(text):
    lines = [re.sub(r'\s+', ' ', x).strip(' -•\t') for x in plain(text).split('\n')]
    return [x for x in lines if len(x) >= 12]

def classify(line):
    result = {}
    for squad, topics in TOPICS.items():
        matched = [label for label, patterns in topics.items() if any(re.search(p, line, re.I) for p in patterns)]
        if matched:
            result[squad] = matched
    return result

def _prepare_translation():
    global _translation_ready
    if _translation_ready:
        return
    installed = argostranslate.translate.get_installed_languages()
    english = next((x for x in installed if x.code == 'en'), None)
    czech = next((x for x in installed if x.code == 'cs'), None)
    if english and czech:
        try:
            english.get_translation(czech)
            _translation_ready = True
            return
        except Exception:
            pass
    print('Pripravuji bezplatny offline preklad Argos Translate (EN -> CS)...')
    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    direct = next((p for p in packages if p.from_code == 'en' and p.to_code == 'cs'), None)
    if direct:
        argostranslate.package.install_from_path(direct.download())
    else:
        # Pokud primy model neni dostupny, zkusime preklad pres nemcinu.
        first = next((p for p in packages if p.from_code == 'en' and p.to_code == 'de'), None)
        second = next((p for p in packages if p.from_code == 'de' and p.to_code == 'cs'), None)
        if not (first and second):
            raise RuntimeError('Model EN -> CS ani cesta EN -> DE -> CS nejsou dostupne.')
        for p in (first, second):
            argostranslate.package.install_from_path(p.download())
    _translation_ready = True

def translate(text):
    try:
        _prepare_translation()
        result = argostranslate.translate.translate(text[:3500], 'en', 'cs')
        return result or text
    except Exception as error:
        print(f'Preklad Argos nedostupny ({type(error).__name__}: {error}); odesilam anglicky text.')
        return text

def send(squad, item, description):
    webhook = WEBHOOKS[squad]
    if not webhook:
        raise RuntimeError(f'Chybi secret DISCORD_{squad}')
    payload = {'username': 'DMT | WARDOGS NEWS', 'allowed_mentions': {'parse': []}, 'embeds': [{
        'title': f'📰 {item.get("title", "WARDOGS aktualizace")}'[:256],
        'url': item['url'], 'description': description[:3900], 'color': 15158332,
        'footer': {'text': f'DMT | {squad} SQUAD • Oficiální Steam novinky'},
    }]}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(webhook + ('&' if '?' in webhook else '?') + 'wait=true',
                                 data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'DMT-News/1.1'}, method='POST')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status not in (200, 204):
                    raise RuntimeError(f'Discord HTTP {response.status}')
            return
        except urllib.error.HTTPError as error:
            if error.code == 429 and attempt < 2:
                time.sleep(min(float(error.headers.get('Retry-After', '2')), 15))
                continue
            raise

def main():
    news = fetch_news()
    if not STATE.exists():
        STATE.write_text(json.dumps([x['gid'] for x in news], indent=2), encoding='utf-8')
        print('Prvni start: ulozena historie, bez zasilani starych zprav.')
        return
    seen = set(json.loads(STATE.read_text(encoding='utf-8')))
    for item in reversed(news):
        gid = str(item['gid'])
        if gid in seen:
            continue
        per_squad = {s: {} for s in WEBHOOKS}
        for line in chunks(item.get('contents', '')):
            for squad, labels in classify(line).items():
                for label in labels:
                    per_squad[squad].setdefault(label, [])
                    if len(per_squad[squad][label]) < 4:
                        per_squad[squad][label].append(line)
        for squad, topics in per_squad.items():
            if not topics:
                continue
            labels = []
            raw_lines = []
            for label, lines in topics.items():
                labels.append(label)
                raw_lines.extend(lines)
            raw_lines = list(dict.fromkeys(raw_lines))[:12]
            translated = translate('\n'.join('• ' + line[:420] for line in raw_lines))
            description = '**' + ' | '.join(labels) + '**\n' + translated[:3500]
            send(squad, item, description)
            print(f'OK: {squad}: {item.get("title", "")[:90]}')
        seen.add(gid)
        STATE.write_text(json.dumps(sorted(seen), indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
