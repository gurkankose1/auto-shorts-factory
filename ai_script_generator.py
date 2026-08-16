import requests
import json
import os
import sys
import time
import random

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

# Groq API — %100 Ucretsiz, Llama 3.3 70B, Super Hizli
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

PROMPT_SYSTEM_TEMPLATES = {
    "stoic": {
        "niche_name": "Stoic Mindset & Philosophy",
        "affiliate_link": "https://www.digistore24.com/redir/474112/gurkankose/",
        "affiliate_cta": "Shield Master Your Mindset & Build Unshakeable Discipline Here ->",
        "style_guide": "Marcus Aurelius, Seneca, Epictetus quotes and practical modern stoic discipline advice. Ultra-engaging, emotionally powerful."
    },
    "bible": {
        "niche_name": "Catholic & Bible Faith Devotional",
        "affiliate_link": "https://www.digistore24.com/redir/474112/gurkankose/",
        "affiliate_cta": "Dove Claim Your Spiritual Growth & Devotional Guide Here ->",
        "style_guide": "Inspiring Bible verses, divine strength, faith in difficult times, prayer. Uplifting and sacred."
    },
    "health": {
        "niche_name": "Keto Diet & Rapid Fat Loss Health Hacks",
        "affiliate_link": "https://www.digistore24.com/redir/283755/gurkankose/",
        "affiliate_cta": "Avocado Get Your Custom Keto Diet Plan & Weight Loss Guide Here ->",
        "style_guide": "Fast metabolism secrets, intermittent fasting tips, low carb superfoods, body transformation. Science-backed, punchy."
    },
    "kids": {
        "niche_name": "Bedtime Stories & Magical Fairy Tales for Kids",
        "affiliate_link": "https://www.digistore24.com/redir/474112/gurkankose/",
        "affiliate_cta": "Moon Explore Beautiful Children Bedtime Storybooks & Activity Guides ->",
        "style_guide": "Cozy, cute, educational bedtime stories about brave little animals and twinkling stars. Warm and magical tone."
    }
}

def generate_ai_topic_and_script(niche_key="stoic", posted_history=None):
    if posted_history is None:
        posted_history = []

    config = PROMPT_SYSTEM_TEMPLATES.get(niche_key, PROMPT_SYSTEM_TEMPLATES["stoic"])
    history_str = ", ".join(posted_history[-20:]) if posted_history else "None yet"

    prompt = f"""You are an expert YouTube Shorts creator for the '{config['niche_name']}' niche.
Generate a completely UNIQUE, highly viral 30-second video script with an 8K AI image prompt.

PREVIOUSLY USED TOPICS (DO NOT REPEAT THESE):
{history_str}

Style: {config['style_guide']}

Return ONLY a valid JSON object with exactly these 6 fields (no markdown, no code blocks):
{{
  "id": "{niche_key}_ai_{int(time.time())}_{random.randint(100,999)}",
  "title": "A viral YouTube Shorts title with emojis and #shorts hashtag",
  "caption_title": "3-5 WORD UPPERCASE BANNER (e.g. STOIC MORNING RULES)",
  "script_body": "A compelling 55-65 word voiceover (~30 seconds) - emotionally gripping, starts with a hook",
  "pinned_comment": "{config['affiliate_cta']} {config['affiliate_link']}",
  "image_prompt": "Hyper-realistic cinematic 8K vertical 9:16 image prompt matching the script scene. Photorealistic, dramatic lighting, no text in image"
}}"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.9
    }

    for attempt in range(1, 4):
        try:
            print(f"[+] Groq LLM Denemesi {attempt}/3...")
            r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
            if r.status_code == 200:
                raw_text = r.json()['choices'][0]['message']['content'].strip()
                # Markdown temizle
                if "```" in raw_text:
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                raw_text = raw_text.strip()
                script_data = json.loads(raw_text)
                print(f"✅ GROQ AI SENARYO URETILDI [{niche_key.upper()}]: {script_data.get('title')}")
                return script_data
            else:
                print(f"❌ Groq Error ({r.status_code}) Deneme {attempt}: {r.text[:150]}")
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse hatasi (Deneme {attempt}): {e}")
        except Exception as e:
            print(f"❌ Groq Exception (Deneme {attempt}): {e}")
        if attempt < 3:
            time.sleep(attempt * 2)

    # Fallback
    fallback_id = f"{niche_key}_fb_{int(time.time())}"
    print(f"[!] Groq basarisiz, fallback kullaniliyor: {fallback_id}")
    return {
        "id": fallback_id,
        "title": f"The Ultimate {niche_key.capitalize()} Secret #shorts",
        "caption_title": f"{niche_key.upper()} SECRETS",
        "script_body": f"Discover the timeless wisdom of {niche_key}. Take control of your daily habits, focus on what matters, and unlock your true potential. The journey starts now.",
        "pinned_comment": f"{config['affiliate_cta']} {config['affiliate_link']}",
        "image_prompt": f"Cinematic dramatic photorealistic 8k vertical 9:16 image representing {niche_key} mindset, moody atmospheric lighting, ultra detailed"
    }

if __name__ == "__main__":
    result = generate_ai_topic_and_script("stoic")
    print(json.dumps(result, indent=2, ensure_ascii=False))
