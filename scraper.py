import os
import requests
from bs4 import BeautifulSoup
import sys
from datetime import datetime
from collections import defaultdict, OrderedDict

URL = "https://www.sivola.it/viaggi/giappone-tokyo-kyoto-osaka"

# Token del tuo bot fornito da BotFather
TOKEN = os.environ["CHANNEL_TOKEN"]

# ID del canale dove il bot invierà i messaggi
CHANNEL_ID = os.environ["CHANNEL_ID"]

TARGET_MONTH = sys.argv[1]
KNOWN_DATES = {
    "2026-08-05",
    "2026-08-06",
    "2026-08-10",
    "2026-08-19",
    "2026-08-21",
    "2026-08-23",
    "2026-08-25",
    "2026-08-28",
    "2026-08-29"
}

def send_message(message):
    # print("Sto mandando " + message)
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    data = {'chat_id': CHANNEL_ID, 'text': message, 'parse_mode': 'HTML'}
    response = requests.post(url, data=data)
    return response.json()

def estrai_viaggi():
    print("Scarico la pagina...")
    r = requests.get(URL)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    # Tutti i blocchi viaggio, anche sold-out
    viaggi = soup.find_all("div", attrs={"data-cw--calendar-date": True})

    risultati = []

    for viaggio in viaggi:
        data_iso = viaggio["data-cw--calendar-date"]  # esempio "2025-11-29"
        data = datetime.strptime(data_iso, "%Y-%m-%d")

        # Durata (es. "9gg")
        durata_el = viaggio.find("span", class_="color-h")
        durata = durata_el.get_text(strip=True) if durata_el else "N/A"

        # Città di partenza
        citta_el = viaggio.find("div", class_="text-small")
        citta = citta_el.get_text(" ", strip=True).split(" In viaggio")[0] if citta_el else "N/A"

        # Sold out?
        soldout = viaggio.find(string=lambda x: x and "Sold out" in x)
        is_soldout = bool(soldout)

        risultati.append({
            "data": data,
            "data_iso": data_iso,
            "durata": durata,
            "partenza": citta,
            "soldout": is_soldout
        })

    # Ordina per data reale
    risultati.sort(key=lambda x: x["data"])

    # Raggruppa per anno/mese già ordinati
    schema = OrderedDict()
    for v in risultati:
        mese = v["data"].strftime("%B %Y")  # es. "November 2025"
        schema.setdefault(mese, []).append(v)

    return schema


if __name__ == "__main__":
    schema = estrai_viaggi()

    print("\n=== SCHEMA VIAGGI (TUTTI, ORDINATI) ===\n")
    for mese, viaggi in schema.items():
        print(f"{mese}")
        for v in viaggi:
            stato = "Sold out" if v["soldout"] else "Disponibile"
            print(f"  - {v['data_iso']} | {v['durata']} | {v['partenza']} | {stato}")
        print()
    
    print(f"Ricerca per {TARGET_MONTH}")
     # Cerca il mese target in schema
    for mese, viaggi in schema.items():
        if TARGET_MONTH in mese:
            # Prendo solo le date nuove
            nuovi_viaggi = [
                v for v in viaggi
                if v["data_iso"] not in KNOWN_DATES
            ]

            if not nuovi_viaggi:
                print("Nessuna nuova data trovata. Nessun messaggio inviato.")
                break

            righe = [f"🆕 <b>Nuove date trovate per {mese}</b>:\n"]

            for v in nuovi_viaggi:
                icona = "❌ Sold out" if v["soldout"] else "🟢 Disponibile"
                righe.append(
                    f"- <b>{v['data_iso']}</b> | {v['durata']} | {v['partenza']} | {icona}"
                )

            messaggio = "\n".join(righe)

            print("Invio messaggio Telegram...")
            send_message(messaggio)
            break

    else:
        print("Nessun viaggio trovato per il mese target. Nessun messaggio inviato.")
