import os
import json
import automation_engine
import youtube_uploader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")

def execute_daily_pipeline():
    print("====================================================")
    print("🚀 GÜNLÜK BULUT DOLAR OTOMASYON MOTORU ÇALIŞTIRILIYOR")
    print("====================================================\n")

    # 1. Run full automation (generate 3 new videos & metadata)
    res = automation_engine.run_full_automation()
    print(f"[+] Otomasyon Sonucu: {res['message']}")

    # 2. Check if YouTube API tokens are available for auto upload
    token_file = os.path.join(BASE_DIR, "token.json")
    if os.path.exists(token_file):
        print("\n[+] YouTube API Token'ı Bulundu. Otomatik Yayınlama Başlatılıyor...")
        
        with open(os.path.join(BASE_DIR, "templates.json"), "r", encoding="utf-8") as f:
            templates = json.load(f)

        for i, t in enumerate(templates[:3]):
            video_id = f"video_{i+1}_{t['id']}"
            video_path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
            
            metadata = {
                "title": t["title"],
                "description": f"{t['script_body']}\n\n#stoicism #mindset #motivation #shorts #viral",
                "pinned_comment": t["pinned_comment"]
            }

            if os.path.exists(video_path):
                youtube_uploader.upload_video_and_comment(video_path, metadata)
    else:
        print("\n[!] BİLGİ: YouTube API Otomatik Yayınlayıcı için token.json bekleniyor.")
        print("[!] Yerel panel üzerinden veya tek tıkla yüklemeye devam edebilirsiniz.")

    print("\n🎉 GÜNLÜK OTOMASYON DÖNGÜSÜ TAMAMLANDI!")

if __name__ == "__main__":
    execute_daily_pipeline()
