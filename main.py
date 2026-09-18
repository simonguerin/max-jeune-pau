def main():
    with open("config.json", "r") as f:
        trajets = json.load(f)
        
    history = load_history()
    
    # --- LIGNE À AJOUTER ---
    send_telegram("🔔 Connexion Telegram OK ! Début de la recherche...")
    print("Test Telegram envoyé.")

data = resp.json()
    
    # --- LIGNE À AJOUTER ---
    print(f"Résultats pour {origine} ➔ {dest} : {data.get('total_count', 0)} trains analysés.")
