import os
import requests
from datetime import datetime

# Récupération des secrets depuis GitHub Actions
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def check_trains():
    # L'API Open Data SNCF pour les TGV Max
    url = "https://data.sncf.com/api/explore/v2.1/catalog/datasets/tarifs-tgv-max/records"
    
    # Exemple pour un vendredi spécifique
    date_recherche = "2026-10-09"
    
    params = {
        "where": f"origine='PARIS (INTRAMUROS)' and destination='PAU' and date='{date_recherche}'",
        "limit": 20
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("total_count", 0) > 0:
            # Filtrer les trains où des places à 0€ sont effectivement ouvertes ("OUI")
            places_dispo = [t for t in data["results"] if t["od_happy_card"] == "OUI"]
            
            for place in places_dispo:
                msg = f"🚂 Max Jeune Dispo !\nTrajet : Paris -> Pau\nDate : {place['date']}\nDépart : {place['heure_depart']}"
                send_telegram_message(msg)
                
    except Exception as e:
        print(f"Erreur d'API : {e}")

if __name__ == "__main__":
    check_trains()
