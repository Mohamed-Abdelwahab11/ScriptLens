from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from groq import AsyncGroq
import json
import os
import math
import asyncio
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# ─── File Paths ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
CALIBRATION_PATH = os.path.join(BASE_DIR, "calibration.json")
TRAINING_DATA_PATH = os.path.join(BASE_DIR, "training_data.json")

def load_calibration() -> dict:
    """Load the learned genre multipliers from calibration.json."""
    try:
        with open(CALIBRATION_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"genre_multipliers": {}, "words_per_second_by_genre": {}, "error_history": []}

def save_calibration(data: dict):
    """Persist updated calibration data."""
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(CALIBRATION_PATH, "w") as f:
        json.dump(data, f, indent=2)

def load_training_data() -> dict:
    """Load ground truth film metrics."""
    try:
        with open(TRAINING_DATA_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"films": [], "genre_baseline_multipliers": {}}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

async def process_chunk(chunk_text: str, logline: str, previous_memory: str, pacing_bias: float = 1.0):
    prompt = f"""
    Act as a Master Cinematographer and Cinema Scholar. Analyze this part of the script:
    LOGLINE: "{logline}"
    PREVIOUS NARRATIVE MEMORY: "{previous_memory}"
    GENRE PACING BIAS (from calibration engine): {pacing_bias:.2f}x — If this value is > 1.5, the film tends to linger on moments. If < 0.9, it is fast-cut. Use this to inform your `pacing_multiplier` estimates.
    (Use the previous memory to understand the emotional continuity. If a character was crying in the previous chunk, the lighting/angles here should reflect the aftermath).
    SCRIPT (Excerpt): "{chunk_text}"

    STRICT ANALYSIS REQUIREMENTS:
    0. SCENE PARSING (MANDATORY): EVERY SINGLE LINE in the script that starts with "INT." or "EXT." MUST be treated as an independent, separate scene in the JSON `analysis` array. Do NOT combine or group them under any circumstances. This strictly matches the physical production script breakdown.
    1. THEMATIC AUDIT: Pass/Fail based on logline consistency.
    2. GLOBAL & SCENE DURATION: 
       - Estimate the TOTAL film runtime as a RANGE (e.g., "95-115 Min") in `estimated_runtime_range`.
       - For each scene, calculate the exact duration in seconds (`scene_duration_seconds`).
    3. KEYWORD-BASED DIRECTING RULES (MANDATORY):
       - If the scene context involves "Emotions", "Tears", "Cry", or "Aside", you MUST exclusively use CLOSE UP or EXTREME CLOSE UP.
       - If the scene involves "Movement", "Chase", "Enter", or "Exit", you MUST use WIDE SHOT or TRACKING SHOT.
       - If the scene is two characters talking (Dialogue), you MUST use SHOT/REVERSE SHOT patterns (Over-the-shoulder cuts).
    4. CONTEXTUAL SHOT LOGIC & CONTINUITY (CRITICAL):
       - You must deeply analyze the emotional context and action of the scene, CONTINUING from the `PREVIOUS NARRATIVE MEMORY`.
       - Every camera angle, movement, and shot size MUST directly reflect the characters' psychological state.
    5. CHARACTERS, DIALOGUE, TENSION & PACING: 
       - You MUST populate the `characters` array for each scene with the exact names of the characters present.
       - Estimate the `dialogue_percentage` (0 to 100).
       - For `scene_tension_score`, provide an integer from 1 to 10 representing emotional intensity.
       - CRITICAL: Provide a `pacing_multiplier` (float). This is the secret to accurate duration. If the scene is a fast fight or chaotic argument (many words, short time), use 0.5 - 0.8. If it's normal dialogue, use 1.0. If it's a slow emotional beat, suspense, or staring (few words, long time), use 2.0 - 4.0.
    6. SHOT DATA: For EACH shot, you MUST provide its primary details (shot_type, angle, movement, estimated_seconds, cinematic_reasoning, director_reference, movie_reference) and an `alternatives` array.
       - The `alternatives` array MUST contain exactly 2 alternative ways to shoot the same narrative beat.
       - INTELLIGENT PROBABILITIES: Calculate the `primary_percentage` and the alternative `percentage`s dynamically based on cinematic theory. If a shot is a highly obvious choice (e.g., Close Up on a tear), give it 90% and the alternatives 5% each. If the scene is ambiguous, make it 50%, 30%, 20%. The sum of all 3 MUST equal 100%. DO NOT use fixed arbitrary numbers.
       - CRITICAL: ALL ALTERNATIVES MUST STRICTLY ADHERE TO THE KEYWORD-BASED DIRECTING RULES (Point 3). If the rule dictates a CLOSE UP, all alternatives MUST be variations of Close Up.
       - For EVERY alternative, provide the full data: shot_type, angle, movement, percentage, cinematic_reasoning, director_reference, and movie_reference.
       - CRITICAL: NO SHOT CAN EXCEED 60 SECONDS. You MUST break long actions into multiple shorter shots (Intercutting/Coverage).
    7. NARRATIVE MEMORY:
       - Write a brief summary of the emotional state and key events at the END of this excerpt in `narrative_memory`. This will be passed to the next chunk.

    Return ONLY JSON:
    {{
      "logline_audit": {{"status": "string", "feedback": "string"}},
      "estimated_runtime_range": "string",
      "narrative_memory": "string",
      "analysis": [
        {{
          "scene_header": "string",
          "scene_tension_score": 5,
          "dialogue_percentage": 50,
          "pacing_multiplier": 1.0,
          "scene_duration_seconds": 0,
          "characters": ["Name1", "Name2"],
          "shots": [
            {{
              "shot_type": "WIDE/MEDIUM/CLOSE UP",
              "primary_percentage": 70,
              "angle": "string",
              "movement": "string",
              "estimated_seconds": 0,
              "cinematic_reasoning": "string",
              "director_reference": "string",
              "movie_reference": "string",
              "alternatives": [
                {{
                  "shot_type": "string",
                  "angle": "string",
                  "movement": "string",
                  "percentage": 30,
                  "cinematic_reasoning": "string",
                  "director_reference": "string",
                  "movie_reference": "string"
                }}
              ]
            }}
          ]
        }}
      ]
    }}
    """
    max_retries = 3
    base_delay = 5.0
    
    for attempt in range(max_retries):
        try:
            completion = await client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            error_str = str(e).lower()
            if "rate_limit_exceeded" in error_str or "429" in error_str:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)
                    print(f"[ML] Rate limit reached (TPM limit). Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print("[ML] Rate limit failed after max retries.")
                    raise e
            else:
                    raise e

def count_actionable_words(text: str) -> int:
    """Strips non-actionable script formatting and returns the true word count."""
    lines = text.split('\n')
    actionable_words = 0
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        
        # Ignore Scene Headers
        if re.match(r'^(?:INT\.|EXT\.|INT/EXT\.|I/E|داخلي|خارجي)[\.\s\-]*.*$', stripped, re.IGNORECASE):
            continue
            
        # Ignore Transitions
        if stripped.upper().endswith("CUT TO:") or stripped.upper() in ["FADE IN:", "FADE OUT.", "DISSOLVE TO:"]:
            continue
            
        # Ignore Character Names (ALL CAPS, short, often centered)
        if stripped.isupper() and len(stripped.split()) <= 4:
            continue
            
        actionable_words += len(stripped.split())
        
    return max(1, actionable_words) # Prevent division by zero

@app.post("/analyze")
async def analyze_script(data: dict):
    script_text = data.get("script_text", "")
    logline = data.get("logline", "Not provided")
    
    if not script_text.strip():
        return {"error": "Empty script"}

    # ══════════════════════════════════════════════════════════
    # STEP 0: INVISIBLE AUTO-GENRE DETECTION
    # Scores the script against keyword vocabularies per genre.
    # No user interaction required. Fully transparent.
    # ══════════════════════════════════════════════════════════
    GENRE_KEYWORDS = {
        "Action":      ["chase", "shoot", "explosion", "fight", "punch", "gun", "blast", "attack", "crash", "run"],
        "Horror":      ["blood", "scream", "dark", "ghost", "monster", "fear", "death", "kill", "shadow", "creature"],
        "Comedy":      ["laugh", "funny", "joke", "silly", "awkward", "gag", "smile", "prank", "absurd", "ridiculous"],
        "Romance":     ["love", "kiss", "heart", "embrace", "couple", "wedding", "feelings", "romantic", "passion", "together"],
        "Sci-Fi":      ["spaceship", "alien", "robot", "future", "technology", "planet", "orbit", "android", "laser", "dimension"],
        "Thriller":    ["suspect", "trap", "danger", "escape", "spy", "secret", "betrayal", "murder", "clue", "threat"],
        "Drama":       ["family", "tears", "argue", "silent", "cry", "confession", "grief", "regret", "sacrifice", "truth"],
        "Crime":       ["detective", "crime", "police", "witness", "evidence", "guilty", "prison", "investigation", "suspect", "warrant"],
        "Fantasy":     ["magic", "dragon", "wizard", "kingdom", "spell", "enchanted", "quest", "mythical", "prophecy", "sword"],
        "Western":     ["cowboy", "saloon", "desert", "sheriff", "outlaw", "ranch", "frontier", "duel", "horse", "gold"],
        "Animation":   ["cartoon", "animated", "toy", "magic", "wonder", "adventure", "creature", "fantasy", "color", "imaginary"],
        "Mystery":     ["mystery", "clue", "investigate", "hidden", "secret", "disappear", "unknown", "puzzle", "reveal", "alibi"],
    }
    
    sample = script_text[:20000].lower()
    genre_scores = {}
    for g, keywords in GENRE_KEYWORDS.items():
        genre_scores[g] = sum(sample.count(kw) for kw in keywords)
    
    detected_genre = max(genre_scores, key=genre_scores.get)
    top_score = genre_scores[detected_genre]
    # If no strong signal, fall back to Drama (most common)
    genre = detected_genre if top_score >= 3 else "Drama"
    
    print(f"[ML] Auto-detected genre: {genre} (score={top_score})")

    # ── Load calibration pacing bias silently ─────────────────
    calibration = load_calibration()
    genre_multipliers = calibration.get("genre_multipliers", {})
    pacing_bias = genre_multipliers.get(genre, genre_multipliers.get("default", 1.5))
    print(f"[ML] Using pacing bias: {pacing_bias:.2f}x for genre: {genre}")

    # 1. Chunking
    chunk_size = 6000
    overlap_size = 500
    chunks_with_context = []
    
    for i in range(0, len(script_text), chunk_size):
        chunk_text = script_text[i:i+chunk_size]
        prev_context = script_text[max(0, i-overlap_size):i] if i > 0 else "None. This is the very beginning of the script."
        chunks_with_context.append((chunk_text, prev_context))

    results = []
    sem = asyncio.Semaphore(1) # Reduced to 1 to strictly respect free tier 6000 TPM limit
    
    async def process_chunk_with_semaphore(chunk, log, memory):
        async with sem:
            # Added a small delay between chunks to allow the rolling minute bucket to refill
            await asyncio.sleep(2.0)
            return await process_chunk(chunk, log, memory, pacing_bias)

    tasks = [process_chunk_with_semaphore(chunk, logline, ctx) for chunk, ctx in chunks_with_context]
    
    try:
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        results = [res for res in raw_results if not isinstance(res, Exception) and isinstance(res, dict)]
    except Exception as e:
        print(f"Parallel processing error: {str(e)}")

    final_analysis = []
    logline_audit = None

    for res in results:
        if not logline_audit and "logline_audit" in res:
            logline_audit = res["logline_audit"]
        for scene in res.get("analysis", []):
            final_analysis.append(scene)

    # 2. Dual-Track Cinematic Duration Math
    
    total_calculated_seconds = 0
    dampened_global_bias = 1.0 + ((pacing_bias - 1.0) * 0.15)
    
    genre_wps = calibration.get("words_per_second_by_genre", {}).get(genre, 1.5)
    
    if final_analysis:
        total_actionable_words = count_actionable_words(script_text)
        
        total_raw_ai_seconds = sum(
            sum(shot.get("estimated_seconds", 5) for shot in scene.get("shots", []))
            for scene in final_analysis
        )
        
        for scene in final_analysis:
            scene_raw_sec = sum(shot.get("estimated_seconds", 5) for shot in scene.get("shots", []))
            proportion = scene_raw_sec / max(1, total_raw_ai_seconds) if total_raw_ai_seconds > 0 else (1.0 / len(final_analysis))
            
            scene_words = total_actionable_words * proportion
            
            # Dual-Track Splitting
            dialogue_pct = float(scene.get("dialogue_percentage", 50)) / 100.0
            dialogue_words = scene_words * dialogue_pct
            action_words = scene_words * (1.0 - dialogue_pct)
            
            # 1. Dialogue Track (Human physical speed limit ~2.3 WPS)
            dialogue_seconds = dialogue_words / 2.3
            
            # 2. Action Track (Genre WPS influenced heavily by LLM pacing)
            scene_mult = float(scene.get("pacing_multiplier", 1.0))
            dampened_scene_mult = 1.0 + ((scene_mult - 1.0) * 0.4) 
            
            action_seconds = (action_words / genre_wps) * dampened_scene_mult
            
            # Combine and apply global bias
            exact_scene_duration = max(5, int((dialogue_seconds + action_seconds) * dampened_global_bias))
            
            scene["scene_duration_seconds"] = exact_scene_duration
            total_calculated_seconds += exact_scene_duration
            
            # Ensure the sum of the shots exactly matches the scene duration
            scene_shots = scene.get("shots", [])
            if scene_shots:
                shot_sum = sum(shot.get("estimated_seconds", 5) for shot in scene_shots)
                if shot_sum > 0:
                    shot_scale = exact_scene_duration / shot_sum
                    final_shots = []
                    
                    for shot in scene_shots:
                        shot_time = max(1, int(shot.get("estimated_seconds", 5) * shot_scale))
                        if shot_time > 10:
                            num_splits = math.ceil(shot_time / 8.0)
                            base_time = shot_time // num_splits
                            remainder = shot_time % num_splits
                            types = ["WIDE", "MEDIUM", "CLOSE UP"]
                            for i in range(num_splits):
                                split_shot = shot.copy()
                                split_shot["estimated_seconds"] = base_time + (1 if i < remainder else 0)
                                split_shot["shot_type"] = types[i % 3]
                                final_shots.append(split_shot)
                        else:
                            shot["estimated_seconds"] = shot_time
                            final_shots.append(shot)
                            
                    # Force exact match for scene duration to eliminate duration conflicts
                    final_sum = sum(s["estimated_seconds"] for s in final_shots)
                    diff = exact_scene_duration - final_sum
                    if diff != 0 and final_shots:
                        # Add or subtract difference from the last shot
                        final_shots[-1]["estimated_seconds"] = max(1, final_shots[-1]["estimated_seconds"] + diff)
                        
                    scene["shots"] = final_shots

    # ══════════════════════════════════════════════════════════
    # STEP 3: SILENT SELF-CALIBRATION
    # Compare our predicted runtime against closest film in
    # training data for this genre. Auto-correct multiplier.
    # Invisible to user — runs in background after analysis.
    # ══════════════════════════════════════════════════════════
    try:
        predicted_min = total_calculated_seconds / 60.0
        training = load_training_data()
        genre_films = [f for f in training.get("films", []) if genre in f.get("genre", [])]
        
        if genre_films and predicted_min > 0:
            word_count = count_actionable_words(script_text)
            
            # Find the closest film by word count ratio
            def closeness(f):
                ratio = word_count / max(1, f.get("script_word_count", 1))
                return abs(ratio - 1.0)
            
            closest_film = min(genre_films, key=closeness)
            
            # Scale expected runtime proportionally to our script size
            scale = word_count / max(1, closest_film.get("script_word_count", 1))
            expected_min = closest_film["actual_runtime_minutes"] * scale
            
            if expected_min > 0:
                mape = abs(predicted_min - expected_min) / expected_min * 100
                
                if mape > 15:  # Only self-correct if error > 15%
                    lr = 0.10  # Gentle learning rate — don't overcorrect
                    correction = expected_min / predicted_min
                    current_mult = calibration.get("genre_multipliers", {}).get(genre, 1.5)
                    new_mult = round(current_mult * (1 + lr * (correction - 1)), 3)
                    new_mult = max(0.3, min(6.0, new_mult))
                    
                    calibration["genre_multipliers"][genre] = new_mult
                    calibration["total_calibrations_run"] = calibration.get("total_calibrations_run", 0) + 1
                    
                    error_entry = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "film": "auto-calibration",
                        "genre": genre,
                        "predicted_min": round(predicted_min, 1),
                        "expected_min": round(expected_min, 1),
                        "mape_percent": round(mape, 2),
                        "old_multiplier": current_mult,
                        "new_multiplier": new_mult,
                        "reference_film": closest_film["title"]
                    }
                    history = calibration.get("error_history", [])
                    history.append(error_entry)
                    calibration["error_history"] = history[-50:]
                    save_calibration(calibration)
                    
                    print(f"[ML] Self-calibrated {genre}: {current_mult:.3f} → {new_mult:.3f} (MAPE={mape:.1f}%, ref={closest_film['title']})")
                else:
                    print(f"[ML] No correction needed for {genre} (MAPE={mape:.1f}% within 15% threshold)")
    except Exception as e:
        print(f"[ML] Silent calibration error (non-critical): {e}")

    # ══════════════════════════════════════════════════════════
    # STEP 4: CONFIDENCE SCORE & LOGIC CONFLICT ENGINE
    # ══════════════════════════════════════════════════════════
    total_shots = sum(len(scene.get("shots", [])) for scene in final_analysis)
    computed_asl = total_calculated_seconds / max(1, total_shots)
    
    # Load training data to find expected ASL for genre
    training = load_training_data()
    genre_films = [f for f in training.get("films", []) if genre in f.get("genre", [])]
    
    # Expected ASL Defaults if no films available
    ASL_DEFAULTS = {
        "Action": 2.5, "Animation": 3.0, "Comedy": 4.5, "Crime": 5.0,
        "Drama": 7.0, "Fantasy": 4.0, "Horror": 8.0, "Mystery": 6.0,
        "Romance": 6.0, "Sci-Fi": 6.5, "Thriller": 4.5, "Western": 6.0
    }
    
    default_asl = ASL_DEFAULTS.get(genre, 5.0)
    expected_asl = default_asl
    if genre_films:
        # Weighted average of ASL from similar films, but blended with default to avoid extreme outliers like "Before Sunset" (45s) from destroying the logic if we only have 1 film
        db_asl = sum(f.get("avg_shot_duration_seconds", default_asl) for f in genre_films) / len(genre_films)
        if len(genre_films) < 5:
            # Blend 50/50 with default if dataset for this genre is too small
            expected_asl = (db_asl + default_asl) / 2
        else:
            expected_asl = db_asl
        
    asl_deviation = abs(computed_asl - expected_asl) / expected_asl
    
    logic_conflicts = []
    # If ASL deviation is extreme (>40%), AI rhythm is misaligned with genre norms
    if asl_deviation > 0.4:
        direction = "faster" if computed_asl < expected_asl else "slower"
        logic_conflicts.append({
            "type": "ASL Mismatch",
            "message": f"Computed Average Shot Length ({computed_asl:.1f}s) is significantly {direction} than the {genre} norm ({expected_asl:.1f}s). The model may have misunderstood the visual rhythm."
        })

    # Mathematical Logic Conflict: Does Total Shots * ASL equal Runtime?
    # Also check if sum of shot seconds equals scene duration.
    shot_duration_mismatch = 0
    for scene in final_analysis:
        scene_dur = scene.get("scene_duration_seconds", 0)
        shot_sum = sum(shot.get("estimated_seconds", 0) for shot in scene.get("shots", []))
        if abs(scene_dur - shot_sum) > 2: # 2 seconds rounding allowance
            shot_duration_mismatch += 1
            
    if shot_duration_mismatch > 0:
        logic_conflicts.append({
            "type": "Duration Conflict",
            "message": f"{shot_duration_mismatch} scenes have a mismatch between Scene Duration and the sum of their Shots."
        })
    
    # Calculate Confidence Score (0-100)
    # Starts at 95, penalizes for ASL deviation and logic conflicts
    confidence_score = 95 - (asl_deviation * 30) - (len(logic_conflicts) * 15)
    
    # Bonus for having similar films in the training dataset
    if genre_films:
        confidence_score += min(10, len(genre_films) * 2) 
        
    confidence_score = max(10, min(99, int(confidence_score)))

    return {
        "logline_audit": logline_audit or {"status": "Complete", "feedback": "Processed full script."},
        "estimated_runtime_range": f"~{int(total_calculated_seconds/60)} Min" if final_analysis else "~0 Min",
        "analysis": final_analysis,
        "confidence_score": confidence_score,
        "logic_conflicts": logic_conflicts,
        "metrics": {
            "total_shots": total_shots,
            "computed_asl": round(computed_asl, 2),
            "expected_asl": round(expected_asl, 2)
        }
    }



# ================================================================
# ML CALIBRATION LAYER
# ================================================================

@app.get("/calibration")
async def get_calibration():
    """Return current learned calibration state to the frontend."""
    return load_calibration()


@app.post("/compare")
async def compare_to_ground_truth(data: dict):
    """
    Comparison Logic — called when a user uploads the script of a
    REAL EXISTING film. Compares ScriptLens output vs actual metrics,
    records directional Bias, and silently updates calibration.

    Body: {
      "film_title": "Fantastic Mr. Fox",
      "predicted_runtime_minutes": 135,
      "predicted_shot_count": 420,
      "script_word_count": 95000
    }

    Returns a detailed Bias Report + correction applied.
    """
    title          = data.get("film_title", "")
    predicted_min  = float(data.get("predicted_runtime_minutes", 0))
    pred_shots     = int(data.get("predicted_shot_count", 0))
    word_count     = int(data.get("script_word_count", 0))

    if not title or predicted_min <= 0:
        return {"error": "film_title and predicted_runtime_minutes are required."}

    # ── 1. Look up ground truth ───────────────────────────────
    training = load_training_data()
    ground = next(
        (f for f in training.get("films", []) if title.lower() in f["title"].lower()),
        None
    )

    if not ground:
        return {
            "error": f"'{title}' not found in training_data.json. Run metadata_collector.py first.",
            "hint":  "python src/metadata_collector.py --title \"Fantastic Mr. Fox\" --year 2009"
        }

    actual_min       = ground["actual_runtime_minutes"]
    actual_asl       = ground.get("avg_shot_duration_seconds", 5.0)
    genre            = ground.get("genre", ["Drama"])[0]

    # ── 2. Compute metrics ────────────────────────────────────
    # Runtime Bias (signed: + = over-predicted, - = under-predicted)
    runtime_gap_min  = round(predicted_min - actual_min, 1)
    runtime_mape     = round(abs(runtime_gap_min) / max(1, actual_min) * 100, 2)
    runtime_direction = "over" if runtime_gap_min > 0 else "under"

    # ASL Bias (if we have shot count and char count)
    asl_analysis = {}
    if pred_shots > 0 and predicted_min > 0:
        pred_asl = round((predicted_min * 60) / pred_shots, 2)
        asl_gap  = round(pred_asl - actual_asl, 2)
        asl_mape = round(abs(asl_gap) / max(0.1, actual_asl) * 100, 2)
        asl_analysis = {
            "predicted_asl_seconds": pred_asl,
            "actual_asl_seconds":    actual_asl,
            "asl_gap_seconds":       asl_gap,
            "asl_mape_percent":      asl_mape,
            "asl_verdict":           "✅ Accurate" if asl_mape < 20 else ("⚠️ Over-cut" if asl_gap < 0 else "⚠️ Under-cut")
        }

    # ── 3. Classify the Bias type ─────────────────────────────
    if runtime_mape <= 10:
        bias_class = "ACCURATE"
        bias_msg   = f"ScriptLens is within {runtime_mape:.1f}% of actual runtime. Engine is well-calibrated for this genre."
    elif runtime_direction == "over" and runtime_mape > 30:
        bias_class = "SEVERE_OVER_PREDICTION"
        bias_msg   = (
            f"Engine over-predicted by {abs(runtime_gap_min)} min ({runtime_mape:.1f}%). "
            "Likely cause: pacing_multiplier too high OR dialogue-heavy script treated as slow film. "
            "Correcting genre multiplier downward."
        )
    elif runtime_direction == "under" and runtime_mape > 30:
        bias_class = "SEVERE_UNDER_PREDICTION"
        bias_msg   = (
            f"Engine under-predicted by {abs(runtime_gap_min)} min ({runtime_mape:.1f}%). "
            "Likely cause: action-heavy script with sparse dialogue was over-compressed. "
            "Correcting genre multiplier upward."
        )
    else:
        bias_class = "MODERATE_BIAS"
        bias_msg   = f"Moderate {runtime_direction}-prediction of {abs(runtime_gap_min)} min. Applying gentle correction."

    # ── 4. Apply correction to calibration ────────────────────
    calibration    = load_calibration()
    genre_mults    = calibration.get("genre_multipliers", {})
    current_mult   = genre_mults.get(genre, 1.5)
    old_mult       = current_mult

    if runtime_mape > 10:
        lr = 0.15
        correction   = actual_min / max(1, predicted_min)
        new_mult     = round(current_mult * (1 + lr * (correction - 1)), 3)
        new_mult     = max(0.3, min(6.0, new_mult))
        genre_mults[genre] = new_mult

        # Also update words_per_second if word_count provided
        if word_count > 0:
            new_wps = word_count / max(1, actual_min * 60)
            words_sec = calibration.get("words_per_second_by_genre", {})
            old_wps   = words_sec.get(genre, 1.5)
            words_sec[genre] = round(0.75 * old_wps + 0.25 * new_wps, 3)
            calibration["words_per_second_by_genre"] = words_sec

        calibration["genre_multipliers"]      = genre_mults
        calibration["total_calibrations_run"] = calibration.get("total_calibrations_run", 0) + 1

        entry = {
            "timestamp":       datetime.utcnow().isoformat(),
            "film":            title,
            "genre":           genre,
            "predicted_min":   predicted_min,
            "actual_min":      actual_min,
            "mape_percent":    runtime_mape,
            "direction":       runtime_direction,
            "bias_class":      bias_class,
            "old_multiplier":  old_mult,
            "new_multiplier":  new_mult,
            "source":          "compare_endpoint"
        }
        history = calibration.get("error_history", [])
        history.append(entry)
        calibration["error_history"] = history[-50:]
        save_calibration(calibration)

        correction_applied = {
            "old_multiplier": old_mult,
            "new_multiplier": new_mult,
            "genre_updated":  genre
        }
    else:
        correction_applied = {"message": "No correction needed — within 10% threshold."}
        new_mult = current_mult

    return {
        "film":                 title,
        "genre":                genre,
        "bias_class":           bias_class,
        "bias_message":         bias_msg,
        "runtime_analysis": {
            "predicted_min":     predicted_min,
            "actual_min":        actual_min,
            "gap_minutes":       runtime_gap_min,
            "mape_percent":      runtime_mape,
            "direction":         runtime_direction
        },
        "asl_analysis":         asl_analysis,
        "correction_applied":   correction_applied,
        "director":             ground.get("director", ""),
        "reference_data": {
            "pacing_profile":    ground.get("pacing_profile", ""),
            "words_per_second":  ground.get("words_per_second_ground_truth", 1.5),
            "avg_asl_seconds":   actual_asl,
            "notes":             ground.get("notes", "")
        }
    }


@app.get("/training-data")
async def get_training_data():
    """Return all ground truth film data."""
    return load_training_data()

@app.post("/calibrate")
async def calibrate(data: dict):
    """
    Compare predicted runtime vs actual runtime for a known film,
    compute MAPE error, and update the genre multiplier using
    gradient-descent-style correction (learning rate = 0.15).

    Body: {
      "film_title": "The Godfather",
      "genre": "Drama",
      "predicted_runtime_minutes": 195,
      "actual_runtime_minutes": 175,
      "script_word_count": 42000
    }
    """
    genre         = data.get("genre", "default")
    predicted_min = float(data.get("predicted_runtime_minutes", 0))
    actual_min    = float(data.get("actual_runtime_minutes", 0))
    film_title    = data.get("film_title", "Unknown")
    word_count    = int(data.get("script_word_count", 0))

    if actual_min <= 0 or predicted_min <= 0:
        return {"error": "Both predicted and actual runtime must be > 0"}

    # ── 1. Compute MAPE (Mean Absolute Percentage Error) ──────
    mape = abs(predicted_min - actual_min) / actual_min * 100
    direction = "over" if predicted_min > actual_min else "under"

    # ── 2. Load current calibration ───────────────────────────
    calibration = load_calibration()
    genre_mults  = calibration.get("genre_multipliers", {})
    words_sec    = calibration.get("words_per_second_by_genre", {})

    current_mult = genre_mults.get(genre, genre_mults.get("default", 1.5))

    # ── 3. Gradient-descent correction (learning rate = 0.15) ─
    # If we over-predicted: lower the multiplier
    # If we under-predicted: raise the multiplier
    learning_rate = 0.15
    correction_factor = actual_min / predicted_min  # e.g. 175/195 = 0.897
    new_mult = current_mult * (1 + learning_rate * (correction_factor - 1))
    new_mult = round(max(0.3, min(6.0, new_mult)), 3)  # Clamp: [0.3, 6.0]

    # ── 4. Update words_per_second if word_count is provided ──
    if word_count > 0:
        actual_seconds = actual_min * 60
        new_wps = round(word_count / actual_seconds, 3)
        old_wps = words_sec.get(genre, words_sec.get("default", 1.5))
        # Smooth update: 80% old + 20% new (exponential moving average)
        words_sec[genre] = round(0.8 * old_wps + 0.2 * new_wps, 3)

    # ── 5. Persist ────────────────────────────────────────────
    genre_mults[genre] = new_mult
    calibration["genre_multipliers"]        = genre_mults
    calibration["words_per_second_by_genre"] = words_sec
    calibration["total_calibrations_run"]   = calibration.get("total_calibrations_run", 0) + 1

    # Keep last 50 error events
    error_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "film": film_title,
        "genre": genre,
        "predicted_min": predicted_min,
        "actual_min": actual_min,
        "mape_percent": round(mape, 2),
        "direction": direction,
        "old_multiplier": current_mult,
        "new_multiplier": new_mult
    }
    history = calibration.get("error_history", [])
    history.append(error_entry)
    calibration["error_history"] = history[-50:]

    save_calibration(calibration)

    return {
        "status": "calibrated",
        "film": film_title,
        "genre": genre,
        "error_rate_mape": round(mape, 2),
        "direction": direction,
        "old_multiplier": current_mult,
        "new_multiplier": new_mult,
        "message": f"Multiplier for '{genre}' adjusted {current_mult:.3f} → {new_mult:.3f} (Error was {mape:.1f}% {direction}-prediction)"
    }


@app.post("/calibrate/batch")
async def calibrate_batch(data: dict):
    """
    Run calibration against all matching films in training_data.json
    for a given genre. Returns aggregate error report.
    """
    genre = data.get("genre", "default")
    training = load_training_data()
    films_in_genre = [f for f in training.get("films", []) if genre in f.get("genre", [])]

    if not films_in_genre:
        return {"error": f"No training data found for genre: {genre}"}

    calibration = load_calibration()
    genre_mults  = calibration.get("genre_multipliers", {})
    current_mult = genre_mults.get(genre, genre_mults.get("default", 1.5))

    # Calculate average words_per_second across matching films
    avg_wps = sum(f.get("words_per_second_ground_truth", 1.5) for f in films_in_genre) / len(films_in_genre)
    avg_pacing = sum(f["genre_pacing_multiplier"] for f in films_in_genre) / len(films_in_genre)

    # Smooth update toward ground-truth average
    lr = 0.3
    new_mult = round(current_mult * (1 - lr) + avg_pacing * lr, 3)
    new_mult = max(0.3, min(6.0, new_mult))

    genre_mults[genre] = new_mult
    calibration["genre_multipliers"] = genre_mults
    calibration["words_per_second_by_genre"][genre] = round(avg_wps, 3)
    calibration["total_calibrations_run"] = calibration.get("total_calibrations_run", 0) + 1
    save_calibration(calibration)

    return {
        "status": "batch_calibrated",
        "genre": genre,
        "films_used": [f["title"] for f in films_in_genre],
        "avg_ground_truth_multiplier": round(avg_pacing, 3),
        "avg_words_per_second": round(avg_wps, 3),
        "old_multiplier": current_mult,
        "new_multiplier": new_mult
    }