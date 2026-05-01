import os
import json
from groq import Groq
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

class LlamaIntelligence:
    def __init__(self):
        # Fetches the key from the .env file securely
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found. Check your .env file.")
        
        self.client = Groq(api_key=api_key)

    def analyze_scene(self, scene_text):
        prompt = f"""
        Analyze this screenplay scene:
        "{scene_text}"

        Instructions:
        1. Extract all unique character names. Do NOT include pronouns.
        2. Identify the shot type: WIDE SHOT, MEDIUM SHOT, or CLOSE UP.
        3. Write a professional cinematic reason for this choice.

        Return ONLY a JSON object with these keys: 
        "characters": [], "shot_type": "", "reason": ""
        """

        try:
            completion = self.client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            return {
                "characters": ["Error"],
                "shot_type": "MEDIUM SHOT",
                "reason": f"Connection error: {str(e)}"
            }