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
    with open("config.json", "r") as f:
        trajets = json.load(f)
        
    history = load_history()
    url = "https://data.sncf.com/api/explore/v2.1/catalog/datasets/tarifs-tgv-max/records"
    nouveaux_trouves = False

    print("Recherche de TOUS les trains en cours...")

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
        nb_trains = data.get("total_count", 0)
        print(f"Résultats pour {origine} ➔ {dest} : {nb_trains} trains analysés.")
        
        if nb_trains > 0:
            for record in data["results"]:
                heure_dep = record.get("heure_depart", "00:00")
                # On récupère le statut Max Jeune (OUI ou NON)
                statut_max = record.get("od_happy_card", "NON") 
                
                if h_min <= heure_dep <= h_max:
                    # J'ai rajouté "test_" pour ne pas polluer ton vrai historique
                    train_id = f"test_{date}_{origine}_{dest}_{heure_dep}"
                    
                    if train_id not in history:
                        msg = f"🚆 TEST TRAIN\n📍 {origine} ➔ {dest}\n📅 {date}\n⏰ Départ : {heure_dep}\n🎟️ Max Jeune dispo : {statut_max}"
                        send_telegram(msg)
                        history.append(train_id)
                        nouveaux_trouves = True

    if nouveaux_trouves:
        save_history(history)

if __name__ == "__main__":
    main()
