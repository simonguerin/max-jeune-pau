import os
import requests
import json
import csv
import io
from datetime import time as dtime, date as ddate

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SHEET_CSV_URL = os.getenv("GOOGLE_SHEET_CSV_URL")
HISTORY_FILE = "history.json"

# Correspondances "nom tapé sur le téléphone" -> "nom exact attendu par le dataset SNCF".
# Complète cette liste au fur et à mesure des villes que tu utilises.
STATION_ALIASES = {
    "paris": "PARIS (intramuros)",
    "pau": "PAU",
}


def resolve_station(nom):
    """Normalise un nom de gare tapé librement vers le nom exact attendu par l'API."""
    if not nom:
        return nom
    cle = nom.strip().lower()
    if cle in STATION_ALIASES:
        return STATION_ALIASES[cle]
    # Nom inconnu de la table : on tente une majuscule simple, sans garantie.
    return nom.strip().upper()


def parse_heure(h):
    """Convertit une heure quel que soit son format ('6:5', '06:05:00'...) en objet time."""
    if not h:
        return None
    h = h.strip()
    parts = h.split(":")
    try:
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        return dtime(hour=hh, minute=mm)
    except (ValueError, IndexError):
        return None


def parse_date(d):
    """Ne garde que la partie AAAA-MM-JJ, même si le champ contient un horodatage complet."""
    if not d:
        return None
    return d.strip()[:10]


def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("❌ TELEGRAM_TOKEN ou CHAT_ID manquant (variable d'environnement vide) — notification non envoyée.")
        return False
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text})
    if resp.status_code != 200:
        print(f"❌ Échec envoi Telegram (HTTP {resp.status_code}) : {resp.text}")
        return False
    print("✅ Notification Telegram envoyée avec succès.")
    return True


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


def load_trajets():
    """Récupère les trajets depuis le Google Sheet (colonnes : origine, destination, date, heure_min, heure_max)."""
    if not SHEET_CSV_URL:
        print("❌ ERREUR : la variable GOOGLE_SHEET_CSV_URL n'est pas définie.")
        return []

    resp = requests.get(SHEET_CSV_URL, timeout=10)
    if resp.status_code != 200:
        print(f"❌ Impossible de lire le Google Sheet (HTTP {resp.status_code}).")
        return []

    reader = csv.DictReader(io.StringIO(resp.text))
    trajets = []
    today = ddate.today().isoformat()

    for row in reader:
        origine_brut = row.get("origine", "")
        dest_brut = row.get("destination", "")
        date_brut = parse_date(row.get("date", ""))

        if not origine_brut or not dest_brut or not date_brut:
            continue

        # Trajet dans le passé : on l'ignore, plus la peine de le vérifier.
        if date_brut < today:
            print(f"🗑️ Trajet du {date_brut} ignoré (date déjà passée).")
            continue

        trajets.append({
            "origine": resolve_station(origine_brut),
            "destination": resolve_station(dest_brut),
            "date": date_brut,
            "heure_min": row.get("heure_min", "00:00"),
            "heure_max": row.get("heure_max", "23:59"),
        })

    return trajets


def main():
    print("Lecture des trajets depuis le Google Sheet...")
    trajets = load_trajets()

    if not trajets:
        print("❌ Aucun trajet valide à traiter.")
        return

    print(f"✅ {len(trajets)} trajet(s) à vérifier (dates passées déjà exclues).")

    history = load_history()
    nouveaux_trouves = False

    for t in trajets:
        origine = t["origine"]
        dest = t["destination"]
        date = t["date"]
        h_min_t = parse_heure(t.get("heure_min", "00:00")) or dtime(0, 0)
        h_max_t = parse_heure(t.get("heure_max", "23:59")) or dtime(23, 59)

        print(f"Recherche directe pour : {origine} ➔ {dest} le {date}...")

        # API open data officielle SNCF (dataset "tgvmax", Opendatasoft, sans clé requise)
        url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/records"

        where = f'origine="{origine}" and destination="{dest}"'
        limit = 100
        offset = 0
        trains = []
        trains_ce_jour = 0

        try:
            while True:
                params = {"where": where, "limit": limit, "offset": offset}
                resp = requests.get(url, params=params, timeout=10)
                print(f"Code HTTP reçu : {resp.status_code}")

                if resp.status_code != 200:
                    print(f"❌ Erreur API : {resp.text}")
                    break

                data = resp.json()
                page = data.get("results", [])
                trains.extend(page)

                if len(page) < limit or offset > 1000:
                    break
                offset += limit

            print(f"📊 Résultats : {len(trains)} trains trouvés.")
            if trains:
                print(f"🔍 DEBUG premier train brut : {json.dumps(trains[0], ensure_ascii=False)}")

            for record in trains:
                record_date = parse_date(record.get("date"))
                if record_date != date:
                    continue
                trains_ce_jour += 1
                print(f"📋 Train du jour ({trains_ce_jour}) : {json.dumps(record, ensure_ascii=False)}")

                is_free = record.get("od_happy_card") == "OUI"
                if not is_free:
                    print(f"ℹ️ Train {record.get('train_no', '?')} le {record_date} à {record.get('heure_depart', '?')} : od_happy_card={record.get('od_happy_card')!r} (pas Max)")
                    continue

                heure_dep_t = parse_heure(record.get("heure_depart"))
                if heure_dep_t is None:
                    print(f"⚠️ Heure de départ illisible, train ignoré : {record.get('heure_depart')!r} — {record}")
                    continue

                if not (h_min_t <= heure_dep_t <= h_max_t):
                    print(f"ℹ️ Train Max dispo mais hors fenêtre horaire ({h_min_t}-{h_max_t}) : départ {heure_dep_t}")
                    continue

                heure_dep = heure_dep_t.strftime("%H:%M")
                train_id = f"test_{date}_{origine}_{dest}_{heure_dep}"

                if train_id in history:
                    print(f"🔁 Train Max déjà notifié précédemment (dans history.json) : {train_id}")
                    continue

                print(f"🎯 Nouveau train Max trouvé : départ {heure_dep}, train n°{record.get('train_no', '?')}")
                train_no = record.get("train_no", "?")
                msg = f"🚆 TRAIN MAX DISPONIBLE\n📍 {origine} ➔ {dest}\n📅 {date}\n⏰ Départ : {heure_dep}\n🚄 Train n°{train_no}"
                if send_telegram(msg):
                    history.append(train_id)
                    nouveaux_trouves = True

        except Exception as e:
            print(f"❌ Erreur lors de la requête : {e}")
        else:
            print(f"📅 Dont {trains_ce_jour} train(s) correspondant à la date {date}.")

    if nouveaux_trouves:
        save_history(history)

    print("Fin du script.")


if __name__ == "__main__":
    main()
