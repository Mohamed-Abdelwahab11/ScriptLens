import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# --- CRITICAL PATH SYNC ---
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_PATH)

if BASE_PATH not in sys.path:
    sys.path.append(BASE_PATH)

FRONTEND_PATH = os.path.join(PROJECT_ROOT, "frontend")

# Imports
from ingestion.sanitizer import ScriptSanitizer
from intelligence.reasoning import CinematicIntelligence
from intelligence.nlp_engine import EntityExtractor
from intelligence.analytics import ScriptAnalytics
from api.schemas import ScriptRequest, APIResponse

app = FastAPI(title="ScriptLens Cinematic AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

@app.get("/")
def serve_ui():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))

# Initialize Engines once for performance
sanitizer = ScriptSanitizer()
ai_director = CinematicIntelligence()
nlp_extractor = EntityExtractor()
analytics_engine = ScriptAnalytics()

@app.post("/analyze")
def analyze_script(request: ScriptRequest):
    if not request.script_text.strip():
        raise HTTPException(status_code=400, detail="Script text cannot be empty.")
        
    try:
        # 1. Normalization
        clean_data = sanitizer.normalize_text(request.script_text)
        detected_scenes = set(sanitizer.identify_scenes(clean_data)) # Use set for O(1) lookup
        
        # 2. ISOLATED PARSING LOOP (Prevents Data Leaks)
        lines = clean_data.split('\n')
        structured_scenes = []
        current_header = None
        current_action_buffer = []

        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line in detected_scenes:
                # Before starting a new scene, flush the previous buffer
                if current_header and current_action_buffer:
                    structured_scenes.append({
                        "header": current_header,
                        "text": " ".join(current_action_buffer)
                    })
                
                # Reset for the new scene
                current_header = line
                current_action_buffer = [] 
            else:
                # Only collect text if we have a valid header context
                if current_header:
                    current_action_buffer.append(line)

        # Final flush for the last scene in the buffer
        if current_header and current_action_buffer:
            structured_scenes.append({
                "header": current_header, 
                "text": " ".join(current_action_buffer)
            })

        # 3. INTELLIGENCE PROCESSING
        final_analysis = []
        for scene in structured_scenes:
            # AI Inference on the isolated block
            intelligence_result = ai_director.infer_cinematography(scene["text"])
            
            # NLP Character extraction
            chars = nlp_extractor.extract_characters(scene["text"])
            
            final_analysis.append({
                "scene_header": scene["header"],
                "characters": chars,
                "inferred_data": intelligence_result["inferred_data"]
            })
            
        # 4. ANALYTICS (The Chart Data)
        metrics = analytics_engine.calculate_visual_pace(final_analysis)

        return {
            "status": "success",
            "total_scenes": len(final_analysis),
            "analysis": final_analysis,
            "metrics": metrics
        }
        
    except Exception as e:
        # Log the full error to the terminal for developer visibility
        print(f"[CRITICAL ERROR]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI Processing Error: {str(e)}")