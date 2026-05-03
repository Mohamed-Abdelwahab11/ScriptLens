import asyncio
import os
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

async def test():
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    prompt = """Return ONLY JSON: {}"""
    try:
        completion = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=8000
        )
        print("Success!")
    except Exception as e:
        print("Error:", type(e).__name__, str(e))

asyncio.run(test())
