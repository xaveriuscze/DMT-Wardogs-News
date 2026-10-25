"""Bezpecny test trideni, prekladu a Discord webhooku bez zmeny seen_news.json."""
from wardogs_news import classify, translate, send

SAMPLES = {
    'ASSAULT': 'Rifle ammunition magazines for infantry have been improved.',
    'RECON': 'Sniper scope optics and rangefinder have been improved.',
    'ARMOR': 'Tank 120mm ammunition shells have improved penetration.',
    'AIR': 'Helicopter rocket pod ammunition has been adjusted.',
    'BUILDING': 'FOB supplies and logistics delivery have been improved.',
}

ITEM = {
    'title': 'TEST – rozdělení novinek (nejde o skutečný patch)',
    'url': 'https://store.steampowered.com/app/1867240/',
}


def main():
    for squad, sample in SAMPLES.items():
        matched = classify(sample)
        if squad not in matched:
            raise RuntimeError(f'Chyba trideni: {squad}: {matched}')
        translated = translate(sample)
        labels = ' | '.join(matched[squad])
        description = (
            '**🧪 TEST – NEJDE O SKUTEČNOU AKTUALIZACI**\n'
            f'**{labels}**\n'
            f'• {translated}\n\n'
            '_Testovací zpráva. Historie novinek zůstává beze změny._'
        )
        send(squad, ITEM, description)
        print(f'OK: {squad}; kategorie: {labels}; preklad: {translated}')


if __name__ == '__main__':
    main()
