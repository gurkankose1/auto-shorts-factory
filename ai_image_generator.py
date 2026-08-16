import requests
import urllib.parse
import os
import sys
import io
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
AI_IMAGE_DIR = os.path.join(ASSETS_DIR, "ai_generated_images")
os.makedirs(AI_IMAGE_DIR, exist_ok=True)

def generate_flux_8k_image(prompt, output_filename=None, seed=None):
    if seed is None:
        seed = int(time.time() * 1000) % 100000
        
    print(f"[+] Pollinations FLUX.1 Motoru İle 8K AI Görseli Üretiliyor...")
    print(f"[+] Prompt: {prompt[:80]}...")
    
    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&model=flux&seed={seed}&nologo=true"
    
    if output_filename is None:
        output_filename = os.path.join(AI_IMAGE_DIR, f"flux_{seed}.jpg")
        
    try:
        r = requests.get(url, timeout=35)
        if r.status_code == 200 and len(r.content) > 20000:
            with open(output_filename, "wb") as f:
                f.write(r.content)
            print(f"🎉 8K FLUX AI GÖRSELİ BAŞARIYLA OLUŞTURULDU: {output_filename} ({len(r.content)} bytes)")
            return output_filename
        else:
            print(f"❌ Pollinations Response Status: {r.status_code}, Size: {len(r.content)}")
    except Exception as e:
        print(f"❌ FLUX Image Generation Error: {e}")
        
    return None

if __name__ == "__main__":
    test_prompt = "Cinematic vertical 9:16 shot of a steaming ceramic mug of rich keto bulletproof coffee on a rustic dark slate kitchen counter, 8k resolution, photorealistic"
    generate_flux_8k_image(test_prompt, "test_flux_result.jpg")
