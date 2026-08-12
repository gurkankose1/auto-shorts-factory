import sys
import io
import os
import json
import webbrowser

# Force UTF-8 encoding on Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from flask import Flask, render_template, request, jsonify
import automation_engine

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")

@app.route("/")
def index():
    config = automation_engine.load_config()
    digistore_id = config.get("digistore_id", "")
    
    videos = []
    if os.path.exists(OUTPUT_DIR):
        for f in os.listdir(OUTPUT_DIR):
            if f.endswith("_METADATA.txt"):
                video_name = f.replace("_METADATA.txt", ".mp4")
                meta_path = os.path.join(OUTPUT_DIR, f)
                with open(meta_path, "r", encoding="utf-8") as m_file:
                    content = m_file.read()
                videos.append({
                    "name": video_name,
                    "metadata": content,
                    "youtube_url": "https://studio.youtube.com"
                })

    return render_template("index.html", digistore_id=digistore_id, videos=videos)

@app.route("/save_config", methods=["POST"])
def save_config():
    data = request.json
    config = automation_engine.load_config()
    config["digistore_id"] = data.get("digistore_id", "")
    automation_engine.save_config(config)
    return jsonify({"status": "success"})

@app.route("/start_automation", methods=["POST"])
def start_automation():
    data = request.json
    digistore_id = data.get("digistore_id", "demo_user")
    result = automation_engine.run_full_automation(digistore_id)
    return jsonify(result)

if __name__ == "__main__":
    print("[+] TEK TIKLA DOLAR KAZANMA PANELI BASLATILIYOR...")
    print("[+] Tarayicin otomatik aciliyor -> http://localhost:5000")
    webbrowser.open("http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
