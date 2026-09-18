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
    # Charger les paramètres depuis config.json
    with open("config.json", "r") as f:
        trajets = json.load(f)
        
    history = load_history()
    url = "https://data.sncf.com/api/explore/v2.1/catalog/datasets/tarifs-tgv-max/records"
    nouveaux_trouves = False

    # Message de test
    send_telegram("🔔 Connexion Telegram OK ! Début de la recherche...")
    print("Test Telegram envoyé.")

    for t in trajets:
        origine = t["origine"]
        dest = t["destination"]
        date = t["date"]
        h_min = t.get("heure_min", "00:00")
        h_max = t.get("heure_max", "23:59")

        params = {
            "where": f"origine='{origine}' and destination='{dest}' and date='{date}'",
            "limit": 100
        }
        
        resp = requests.get(url, params=params)
        if resp.status_code != 200: continue
        
        data = resp.json()
        
        # Log de vérification (correctement aligné)
        print(f"Résultats pour {origine} ➔ {dest} : {data.get('total_count', 0)} trains analysés.")
        
        if data.get("total_count", 0) > 0:
            for record in data["results"]:
                # Vérifier si la place est à 0€
                if record.get("od_happy_card") == "OUI":
                    heure_dep = record.get("heure_depart", "00:00")
                    
                    # Vérifier la tranche horaire
                    if h_min <= heure_dep <= h_max:
                        train_id = f"{date}_{origine}_{dest}_{heure_dep}"
                        
                        # Si on ne l'a pas déjà notifié
                        if train_id not in history:
                            msg = f"🚄 MAX JEUNE DISPO !\n📍 {origine} ➔ {dest}\n📅 {date}\n⏰ Départ : {heure_dep}"
                            send_telegram(msg)
                            history.append(train_id)
                            nouveaux_trouves = True

    if nouveaux_trouves:
        save_history(history)

if __name__ == "__main__":
    main()
