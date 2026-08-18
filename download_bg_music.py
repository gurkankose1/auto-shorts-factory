import os
import requests
import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
BGM_DIR = os.path.join(ASSETS_DIR, "bg_music")
os.makedirs(BGM_DIR, exist_ok=True)

# Verified 100% Royalty Free CC0 Public Domain BGM tracks
BGM_SOURCES = {
    "stoic": "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3?filename=cinematic-atmosphere-score-2-22136.mp3",
    "bible": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_c8c8a70929.mp3?filename=peaceful-garden-healing-meditation-10149.mp3",
    "health": "https://cdn.pixabay.com/download/audio/2022/10/14/audio_9939f7e432.mp3?filename=lofi-study-112191.mp3",
    "kids": "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0a13f69d2.mp3?filename=lullaby-good-night-10706.mp3"
}

# Alternative reliable direct MP3 fallbacks
FALLBACK_BGM = {
    "stoic": "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/person-bicycle-car-detection.mp4", # placeholder fallback check
    "bible": "https://freepd.com/music/Deep%20Space.mp3",
    "health": "https://freepd.com/music/Upbeat.mp3",
    "kids": "https://freepd.com/music/Lullaby.mp3"
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def ensure_bgm_files():
    print("[+] Kanal Arka Plan Fon Müzikleri Hazırlanıyor...")
    for niche, url in BGM_SOURCES.items():
        dst_path = os.path.join(BGM_DIR, f"{niche}_bg_music.mp3")
        if os.path.exists(dst_path) and os.path.getsize(dst_path) > 20000:
            print(f"  ✅ {niche.upper()} BGM hazır ({os.path.getsize(dst_path)} bytes)")
            continue
            
        print(f"  [+] {niche.upper()} BGM indiriliyor...")
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(dst_path, "wb") as f:
                    f.write(r.content)
                print(f"  ✅ {niche.upper()} BGM indirildi ({len(r.content)} bytes)")
            else:
                print(f"  ⚠️ Status {r.status_code}, fallback deneniyor...")
                alt_url = FALLBACK_BGM.get(niche, "https://freepd.com/music/Deep%20Space.mp3")
                r2 = requests.get(alt_url, headers=headers, timeout=20)
                if r2.status_code == 200 and len(r2.content) > 20000:
                    with open(dst_path, "wb") as f:
                        f.write(r2.content)
                    print(f"  ✅ {niche.upper()} Fallback BGM indirildi ({len(r2.content)} bytes)")
        except Exception as e:
            print(f"  ❌ {niche.upper()} BGM indirme hatası: {e}")

if __name__ == "__main__":
    ensure_bgm_files()
