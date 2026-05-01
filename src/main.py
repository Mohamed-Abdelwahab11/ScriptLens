from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

# سحب المفتاح بأمان من نظام التشغيل
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

@app.post("/analyze")
async def analyze_script(data: dict):
    script_text = data.get("script_text", "")
    
    prompt = f"""
    Act as a Master Cinematographer (expert in Russian, Iranian, and International Festival Cinema).
    Deconstruct this script into a high-end Shot List:
    "{script_text}"

    For EACH scene, return a JSON object containing:
    1. "scene_header": The exact header from text.
    2. "estimated_duration": Total time in seconds.
    3. "characters": Character names.
    4. "shots": A list of specific shots. Each shot MUST have:
       - "shot_type": (e.g., Extreme Close Up, Long Take).
       - "angle_movement": (e.g., Low Angle Static, Tracking Shot).
       - "duration": Shot length in seconds.
       - "references": A list of 2-3 SPECIFIC movie references (e.g., "The slow, poetic pans of Andrei Tarkovsky in 'Stalker'", "The static deep-focus frames of Abbas Kiarostami").

    Return ONLY this JSON format: {{"analysis": [{{ "scene_header": "", "shots": [] }}]}}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}