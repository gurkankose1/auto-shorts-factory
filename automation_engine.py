import os
import json
import random
import webbrowser
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.json")
TEMPLATES_FILE = os.path.join(BASE_DIR, "templates.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"digistore_id": "demo_user", "auto_open_browser": True}

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

def run_full_automation(digistore_id=None):
    config = load_config()
    if digistore_id:
        config["digistore_id"] = digistore_id
        save_config(config)
    else:
        digistore_id = config.get("digistore_id", "demo_user")

    # 1. Select Product for Today
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)
    
    today_product = random.choice(products)
    affiliate_link = f"https://www.digistore24.com/redir/{today_product['digistore_product_id']}/{digistore_id}/"
    print(f"[+] Bugünün Seçilen Ürünü: {today_product['name']}")
    print(f"[+] Özel Dolar Linkin: {affiliate_link}")

    # 2. Update templates with current affiliate link
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        templates = json.load(f)

    for t in templates:
        t['pinned_comment'] = f"🛡️ {today_product['name']} - Get your guide here 👉 {affiliate_link}"

    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)

    # 3. Run Video Generator Engine
    print("[+] Video Otomasyonu Çalıştırılıyor...")
    generator_script = os.path.join(BASE_DIR, "generator.py")
    subprocess.run([sys.executable, generator_script], check=True)

    # 4. Auto-Open Upload Pages in Browser
    if config.get("auto_open_browser", True):
        print("[+] Otomatik Yayınlama Sekmeleri Açılıyor...")
        webbrowser.open("https://studio.youtube.com")
        webbrowser.open("https://www.tiktok.com/creator-center/upload")

    return {
        "status": "success",
        "product": today_product['name'],
        "affiliate_link": affiliate_link,
        "message": "3 Adet Video Üretildi ve Yayınlama Sekmeleri Açıldı!"
    }

if __name__ == "__main__":
    run_full_automation()
