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
        "affiliate_cta": "🛡️ Master Your Mindset & Build Unshakeable Discipline Here 👉",
        "style_guide": "Marcus Aurelius, Seneca, Epictetus quotes and practical modern stoic discipline advice. Ultra-engaging, emotionally powerful.",
        "call_to_action_audio": "Check the pinned comment below to get your discipline guide and transform your life today."
    },
    "bible": {
        "niche_name": "Catholic & Bible Faith Devotional",
        "affiliate_link": "https://www.digistore24.com/redir/651840/gurkankose/",
        "affiliate_cta": "🕊️ Claim Your Spiritual Growth & Devotional Guide Here 👉",
        "style_guide": "Inspiring Bible verses, divine strength, faith in difficult times, prayer. Uplifting and sacred.",
        "call_to_action_audio": "Check the pinned comment below to get your devotional guide and transform your spiritual life today."
    },
    "health": {
        "niche_name": "Keto Diet & Rapid Fat Loss Health Hacks",
        "affiliate_link": "https://www.digistore24.com/redir/283755/gurkankose/",
        "affiliate_cta": "🥑 Get Your Custom Keto Diet Plan & Weight Loss Guide Here 👉",
        "style_guide": "Fast metabolism secrets, intermittent fasting tips, low carb superfoods, body transformation. Science-backed, punchy.",
        "call_to_action_audio": "Check the pinned comment below to get your custom keto plan and change your life today."
    },
    "kids": {
        "niche_name": "Bedtime Stories & Magical Fairy Tales for Kids",
        "affiliate_link": "https://www.checkout-ds24.com/redir/698913/gurkankose/",
        "affiliate_cta": "🌙 Explore Beautiful Children Storybooks & Activity Guides 👉",
        "style_guide": "Cozy, cute, educational bedtime stories about brave little animals and twinkling stars. Warm and magical tone.",
        "call_to_action_audio": "Check the pinned comment below for magical storybooks and fun activity guides for your kids."
    }
}

def generate_ai_topic_and_script(niche_key="stoic", posted_history=None):
    if posted_history is None:
        posted_history = []

    config = PROMPT_SYSTEM_TEMPLATES.get(niche_key, PROMPT_SYSTEM_TEMPLATES["stoic"])
    history_str = ", ".join(posted_history[-20:]) if posted_history else "None yet"

    prompt = f"""You are an expert YouTube Shorts creator for the '{config['niche_name']}' niche.
Generate a completely UNIQUE, highly viral 30-35 second video script.

PREVIOUSLY USED TOPICS (DO NOT REPEAT THESE):
{history_str}

Style: {config['style_guide']}

CRITICAL RULES:
- script_body MUST be 75-95 words (~30-35 seconds of voiceover).
- Start with a powerful emotional hook in the first sentence.
- Build tension, wisdom or curiosity in the middle.
- The VERY LAST SENTENCE of script_body MUST be a call to action directing viewers to check the pinned comment to get the guide/book and transform their life (e.g., "{config['call_to_action_audio']}").
- video_search_query should be 3-4 words describing a dramatic visual scene matching the script for Pexels search.

Return ONLY a valid JSON object with exactly these 7 fields (no markdown, no code blocks):
{{
  "id": "{niche_key}_ai_{int(time.time())}_{random.randint(100,999)}",
  "title": "A viral YouTube Shorts title with emojis and #shorts hashtag",
  "caption_title": "3-5 WORD UPPERCASE BANNER",
  "script_body": "75-95 WORDS. Emotionally gripping script ending with the pinned comment call-to-action.",
  "video_search_query": "3-4 word Pexels video search query matching the scene",
  "pinned_comment": "{config['affiliate_cta']} {config['affiliate_link']}",
  "image_prompt": "Hyper-realistic cinematic 8K vertical 9:16 image prompt matching the script"
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
                
                # CTA kontrolü — eğer sonda CTA cümlesi yoksa ekle
                body = script_data.get("script_body", "").strip()
                if "pinned comment" not in body.lower() and "comment" not in body.lower():
                    body += " " + config["call_to_action_audio"]
                    script_data["script_body"] = body

                # Pinned comment linkini garantile
                script_data["pinned_comment"] = f"{config['affiliate_cta']} {config['affiliate_link']}"

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

    fallback_scripts = {
        "stoic": "The ancient stoics knew one truth above all others. Your mind is the only thing truly yours. Every morning you wake up, you have a choice — to react like a slave to emotion, or to respond like a master of reason. Control what you can. Release what you cannot. That is the stoic way. " + config["call_to_action_audio"],
        "bible": "In your darkest hour, when you feel lost and alone, remember this. You are never truly abandoned. The same God who created the stars and the oceans knows your name. He counts every tear you cry. Every storm you face has a purpose. Hold on to your faith. " + config["call_to_action_audio"],
        "health": "Most people spend years trying every diet and failing. Here is the truth the food industry hides from you. Your body is not broken. Your metabolism is not your enemy. When you cut the sugar and fuel yourself with real whole foods, your body heals. " + config["call_to_action_audio"],
        "kids": "Once upon a time, in a forest full of glowing fireflies and whispering trees, there lived a little fox named Ember who discovered that the darkness was just where the stars come out to play. " + config["call_to_action_audio"]
    }

    return {
        "id": fallback_id,
        "title": f"The Ultimate {niche_key.capitalize()} Secret #shorts",
        "caption_title": f"{niche_key.upper()} WISDOM",
        "script_body": fallback_scripts.get(niche_key, fallback_scripts["stoic"]),
        "video_search_query": "dramatic nature landscape",
        "pinned_comment": f"{config['affiliate_cta']} {config['affiliate_link']}",
        "image_prompt": f"Cinematic dramatic photorealistic 8k vertical 9:16 image representing {niche_key} mindset, moody atmospheric lighting, ultra detailed"
    }

if __name__ == "__main__":
    result = generate_ai_topic_and_script("stoic")
    print(json.dumps(result, indent=2, ensure_ascii=False))
