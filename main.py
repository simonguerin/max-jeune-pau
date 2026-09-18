import os
import requests
import json

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
HISTORY_FILE = "history.json"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def main():
    print("Lecture du fichier config.json...")
    if not os.path.exists("config.json"):
        print("❌ ERREUR : Le fichier config.json est introuvable !")
        return

    with open("config.json", "r") as f:
        trajets = json.load(f)
        
    print(f"✅ {len(trajets)} trajet(s) chargé(s) avec succès.")
    
    history = load_history()
    nouveaux_trouves = False

    for t in trajets:
        origine = t["origine"]
        dest = t["destination"]
        date = t["date"]
        h_min = t.get("heure_min", "00:00")
        h_max = t.get("heure_max", "23:59")

        print(f"Recherche directe pour : {origine} ➔ {dest} le {date}...")

        # API open data officielle SNCF (dataset "tgvmax", Opendatasoft, sans clé requise)
        url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/records"

        where = f'date={date} and origine="{origine}" and destination="{dest}"'
        params = {
            "where": where,
            "limit": 100,
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            print(f"Code HTTP reçu : {resp.status_code}")

            if resp.status_code != 200:
                print(f"❌ Erreur API : {resp.text}")
                continue

            data = resp.json()
            trains = data.get("results", [])
            print(f"📊 Résultats : {len(trains)} trains trouvés.")

            for record in trains:
                heure_dep = record.get("heure_depart", "00:00")
                # Champ officiel du dataset : "OUI" si des places Max Jeune/Senior sont dispo
                is_free = record.get("od_happy_card") == "OUI"

                if not is_free:
                    continue

                if h_min <= heure_dep <= h_max:
                    train_id = f"test_{date}_{origine}_{dest}_{heure_dep}"
                    
                    if train_id not in history:
                        train_no = record.get("train_no", "?")
                        msg = f"🚆 TRAIN MAX DISPONIBLE\n📍 {origine} ➔ {dest}\n📅 {date}\n⏰ Départ : {heure_dep}\n🚄 Train n°{train_no}"
                        send_telegram(msg)
                        history.append(train_id)
                        nouveaux_trouves = True
                        
        except Exception as e:
            print(f"❌ Erreur lors de la requête : {e}")

    if nouveaux_trouves:
        save_history(history)
        
    print("Fin du script.")

if __name__ == "__main__":
    main()
