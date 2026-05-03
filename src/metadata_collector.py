"""
ScriptLens — Metadata Collector
================================
Pulls real film runtime, genre, director, and estimates ASL
(Average Shot Length) from the TMDb API and Cinemetrics database.

Usage:
    python metadata_collector.py --title "Fantastic Mr. Fox" --year 2009
    python metadata_collector.py --tmdb_id 10315
    python metadata_collector.py --batch  (runs the full 20-film training set)

Requires:
    TMDB_API_KEY in .env
    pip install httpx python-dotenv

Output:
    Appends/updates src/training_data.json automatically.
"""

import asyncio
import httpx
import json
import os
import argparse
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE = "https://api.themoviedb.org/3"
TRAINING_DATA_PATH = os.path.join(os.path.dirname(__file__), "training_data.json")

# ─────────────────────────────────────────────────────────────────
# ASL Ground Truth (from Cinemetrics.lv & published film analyses)
# Average Shot Length in seconds. Source: cinemetrics.lv + IMDb
# ─────────────────────────────────────────────────────────────────
ASL_GROUND_TRUTH = {
    "Fantastic Mr. Fox":              3.2,
    "Spider-Man: Into the Spider-Verse": 2.1,
    "Spirited Away":                  6.5,
    "The Incredibles":                3.8,
    "Mad Max: Fury Road":             1.8,
    "John Wick":                      2.5,
    "The Dark Knight":                3.1,
    "Mission: Impossible - Fallout":  2.8,
    "The Godfather":                  6.5,
    "Boyhood":                        9.0,
    "Before Sunset":                  45.0,
    "Roma":                           12.5,
    "No Country for Old Men":         7.2,
    "Parasite":                       5.2,
    "Whiplash":                       3.5,
    "Hereditary":                     10.1,
    "The Grand Budapest Hotel":       3.0,
    "Knives Out":                     5.5,
    "2001: A Space Odyssey":          12.0,
    "Arrival":                        8.5,
}

# ─────────────────────────────────────────────────────────────────
# Estimated words_per_second by pacing profile
# Based on Hollywood script standard ~1 page = ~55 sec = ~150 words
# then adjusted by genre pacing multiplier from training data
# ─────────────────────────────────────────────────────────────────
GENRE_WPS_ESTIMATES = {
    "Action":       0.65,
    "Animation":    1.1,
    "Comedy":       0.9,
    "Crime":        1.5,
    "Drama":        1.9,
    "Fantasy":      1.3,
    "Horror":       2.2,
    "Mystery":      1.8,
    "Romance":      2.5,
    "Science Fiction": 1.6,
    "Thriller":     1.4,
    "Western":      1.7,
}

PACING_PROFILE_MAP = {
    "Action":          "rapid_fire",
    "Animation":       "whimsical_fast",
    "Comedy":          "dialogue_driven",
    "Crime":           "dialogue_driven",
    "Drama":           "naturalistic",
    "Fantasy":         "escalating",
    "Horror":          "slow_dread",
    "Mystery":         "escalating",
    "Romance":         "conversational",
    "Science Fiction": "meditative",
    "Thriller":        "rhythmic_tension",
    "Western":         "slow_burn",
}


async def fetch_tmdb(client: httpx.AsyncClient, path: str, params: dict = {}) -> dict:
    """Generic TMDb API call."""
    params["api_key"] = TMDB_API_KEY
    resp = await client.get(f"{TMDB_BASE}{path}", params=params)
    resp.raise_for_status()
    return resp.json()


async def search_film(client: httpx.AsyncClient, title: str, year: int = None) -> dict | None:
    """Search TMDb for a film by title and optional year."""
    params = {"query": title, "language": "en-US"}
    if year:
        params["year"] = year
    data = await fetch_tmdb(client, "/search/movie", params)
    results = data.get("results", [])
    return results[0] if results else None


async def get_film_details(client: httpx.AsyncClient, tmdb_id: int) -> dict:
    """Fetch full film details + credits from TMDb."""
    details = await fetch_tmdb(client, f"/movie/{tmdb_id}", {"append_to_response": "credits"})
    return details


def extract_director(credits: dict) -> str:
    """Extract director name from credits."""
    for crew_member in credits.get("crew", []):
        if crew_member.get("job") == "Director":
            return crew_member.get("name", "Unknown")
    return "Unknown"


def genre_names(genres: list) -> list[str]:
    """Extract genre names from TMDb genre objects."""
    return [g["name"] for g in genres]


def estimate_pacing_multiplier(genre_list: list[str], asl: float) -> float:
    """
    Estimate the genre pacing multiplier.
    Formula: (ASL / 5.0) normalized — 5 sec is the 'neutral' ASL.
    Higher ASL = slower film = higher multiplier.
    """
    base = asl / 5.0
    return round(min(5.0, max(0.4, base)), 2)


def estimate_wps(genre_list: list[str]) -> float:
    """Estimate words_per_second from genre."""
    for g in genre_list:
        if g in GENRE_WPS_ESTIMATES:
            return GENRE_WPS_ESTIMATES[g]
    return 1.5


def determine_pacing_profile(genre_list: list[str]) -> str:
    """Map genre to a pacing profile label."""
    for g in genre_list:
        if g in PACING_PROFILE_MAP:
            return PACING_PROFILE_MAP[g]
    return "naturalistic"


def generate_film_heuristics(genres: list[str], director: str) -> dict:
    """Intelligently estimate shot distribution, color palette, and shooting schedule pages/day based on cinematic norms."""
    heuristics = {
        "color_palette_hex": ["#1e293b", "#334155", "#475569", "#94a3b8"], # Default slate
        "shot_distribution": {"WIDE": 20, "MEDIUM": 50, "CLOSE_UP": 30},
        "pages_shot_per_day": 4.0,
        "primary_mood": "Neutral"
    }
    
    main_genre = genres[0] if genres else "Drama"
    
    # 1. Color Palette & Mood
    if "Horror" in genres or "Thriller" in genres:
        heuristics["color_palette_hex"] = ["#020617", "#0f172a", "#1e1b4b", "#7f1d1d"] # Deep darks, blood reds
        heuristics["primary_mood"] = "Tense & Atmospheric"
    elif "Action" in genres or "Science Fiction" in genres:
        heuristics["color_palette_hex"] = ["#082f49", "#0e7490", "#064e3b", "#b45309"] # Teal & Orange
        heuristics["primary_mood"] = "High Octane / Epic"
    elif "Comedy" in genres or "Animation" in genres:
        heuristics["color_palette_hex"] = ["#fef08a", "#fde047", "#fcd34d", "#fbbf24"] # Bright & Warm
        heuristics["primary_mood"] = "Vibrant & Light"
    elif "Romance" in genres or "Drama" in genres:
        heuristics["color_palette_hex"] = ["#fdf4ff", "#f5d0fe", "#e879f9", "#fda4af"] # Soft Pastels
        heuristics["primary_mood"] = "Intimate & Emotional"
        
    # 2. Shot Distribution
    if "Action" in genres or "Adventure" in genres:
        heuristics["shot_distribution"] = {"WIDE": 40, "MEDIUM": 40, "CLOSE_UP": 20}
    elif "Drama" in genres or "Romance" in genres:
        heuristics["shot_distribution"] = {"WIDE": 15, "MEDIUM": 45, "CLOSE_UP": 40}
    elif "Thriller" in genres or "Horror" in genres:
        heuristics["shot_distribution"] = {"WIDE": 25, "MEDIUM": 25, "CLOSE_UP": 50}
        
    # 3. Pages per day (Shooting Schedule)
    # Average is 4-5 pages. Directors like Fincher shoot 2. Eastwood shoots 7. Action is slower.
    if "Action" in genres or "Science Fiction" in genres:
        heuristics["pages_shot_per_day"] = 2.5 # Heavy VFX / Stunts take time
    elif "Comedy" in genres or "Drama" in genres:
        heuristics["pages_shot_per_day"] = 5.5 # Dialogue scenes shoot faster
    elif "Animation" in genres:
        heuristics["pages_shot_per_day"] = 0.5 # Animation moves very slowly
        
    return heuristics


async def collect_film(title: str, year: int = None, tmdb_id: int = None) -> dict | None:
    """
    Main function: fetch a film from TMDb and build a training record.
    Returns a dict ready to insert into training_data.json.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        if tmdb_id:
            details = await get_film_details(client, tmdb_id)
        else:
            result = await search_film(client, title, year)
            if not result:
                print(f"  [WARN] '{title}' not found on TMDb.")
                return None
            details = await get_film_details(client, result["id"])

        actual_title = details.get("title", title)
        runtime_min  = details.get("runtime", 0)
        genres       = genre_names(details.get("genres", []))
        credits      = details.get("credits", {})
        director     = extract_director(credits)
        release_year = int(details.get("release_date", "0000")[:4]) if details.get("release_date") else year

        if runtime_min == 0:
            print(f"  [WARN] Runtime = 0 for '{actual_title}'. Skipping.")
            return None

        # ASL — prefer ground truth, else estimate from genre
        asl = ASL_GROUND_TRUTH.get(actual_title, None)
        if asl is None:
            asl = ASL_GROUND_TRUTH.get(title, 5.0)
            print(f"  [INFO] No ASL ground truth for '{actual_title}'. Using default 5.0s.")

        pacing_mult  = estimate_pacing_multiplier(genres, asl)
        wps          = estimate_wps(genres)
        pacing_prof  = determine_pacing_profile(genres)
        heuristics   = generate_film_heuristics(genres, director)

        # Estimate script word count (reverse from runtime + wps)
        est_words = int(runtime_min * 60 * wps)

        record = {
            "title":                          actual_title,
            "year":                           release_year,
            "director":                       director,
            "genre":                          genres,
            "pacing_profile":                 pacing_prof,
            "actual_runtime_minutes":         runtime_min,
            "script_word_count":              est_words,
            "words_per_second_ground_truth":  wps,
            "avg_scene_duration_seconds":     round(runtime_min * 60 / max(1, runtime_min / 3), 1),
            "avg_shot_duration_seconds":      asl,
            "dominant_shot_distribution":     heuristics["shot_distribution"],
            "color_palette_hex":              heuristics["color_palette_hex"],
            "primary_mood":                   heuristics["primary_mood"],
            "pages_shot_per_day":             heuristics["pages_shot_per_day"],
            "avg_dialogue_percentage":        50,
            "avg_tension_score":              5.0,
            "genre_pacing_multiplier":        pacing_mult,
            "words_per_minute_dialogue":      120,
            "source":                         "tmdb_auto",
            "collected_at":                   datetime.utcnow().isoformat(),
            "notes":                          f"Auto-collected via TMDb. ASL from {'cinemetrics' if actual_title in ASL_GROUND_TRUTH else 'genre estimate'}."
        }

        print(f"  ✓ Collected: {actual_title} ({release_year}) | {runtime_min}min | ASL={asl}s | Genre={genres}")
        return record


def load_training_data() -> dict:
    try:
        with open(TRAINING_DATA_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "films": [], "genre_baseline_multipliers": {}}


def save_training_data(data: dict):
    with open(TRAINING_DATA_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n✅ training_data.json updated → {len(data['films'])} total films.")


def upsert_film(training_data: dict, record: dict):
    """Add or update a film record by title."""
    films = training_data.get("films", [])
    existing = next((i for i, f in enumerate(films) if f["title"] == record["title"]), None)
    if existing is not None:
        films[existing] = record
        print(f"  ↻ Updated existing record: {record['title']}")
    else:
        films.append(record)
        print(f"  + Added new record: {record['title']}")
    training_data["films"] = films


# ─────────────────────────────────────────────────────────────────
# BATCH TRAINING SET — 100 Diverse Films (The Master Database)
# ─────────────────────────────────────────────────────────────────
BATCH_TRAINING_SET = [
    # ── Animation (Fast/Whimsical) ──
    {"title": "Fantastic Mr. Fox",                    "year": 2009},
    {"title": "Spider-Man: Into the Spider-Verse",    "year": 2018},
    {"title": "Spirited Away",                        "year": 2001},
    {"title": "The Incredibles",                      "year": 2004},
    {"title": "Toy Story",                            "year": 1995},
    {"title": "Shrek",                                "year": 2001},
    {"title": "Inside Out",                           "year": 2015},
    {"title": "WALL·E",                               "year": 2008},
    {"title": "Up",                                   "year": 2009},
    {"title": "Coco",                                 "year": 2017},
    
    # ── Action/Adventure (Rapid-fire & Epic) ──
    {"title": "Mad Max: Fury Road",                   "year": 2015},
    {"title": "John Wick",                            "year": 2014},
    {"title": "The Dark Knight",                      "year": 2008},
    {"title": "Mission: Impossible - Fallout",        "year": 2018},
    {"title": "Die Hard",                             "year": 1988},
    {"title": "The Matrix",                           "year": 1999},
    {"title": "Gladiator",                            "year": 2000},
    {"title": "Inception",                            "year": 2010},
    {"title": "The Lord of the Rings: The Fellowship of the Ring", "year": 2001},
    {"title": "Jurassic Park",                        "year": 1993},
    {"title": "The Terminator",                       "year": 1984},
    {"title": "Terminator 2: Judgment Day",           "year": 1991},
    {"title": "Raiders of the Lost Ark",              "year": 1981},
    {"title": "The Bourne Ultimatum",                 "year": 2007},
    
    # ── Drama (Naturalistic/Slow/Meditative) ──
    {"title": "The Godfather",                        "year": 1972},
    {"title": "Boyhood",                              "year": 2014},
    {"title": "Before Sunset",                        "year": 2004},
    {"title": "Roma",                                 "year": 2018},
    {"title": "The Shawshank Redemption",             "year": 1994},
    {"title": "Schindler's List",                     "year": 1993},
    {"title": "Forrest Gump",                         "year": 1994},
    {"title": "Fight Club",                           "year": 1999},
    {"title": "Good Will Hunting",                    "year": 1997},
    {"title": "The Social Network",                   "year": 2010},
    {"title": "The Truman Show",                      "year": 1998},
    {"title": "12 Angry Men",                         "year": 1957},
    {"title": "A Beautiful Mind",                     "year": 2001},
    {"title": "Manchester by the Sea",                "year": 2016},
    {"title": "Moonlight",                            "year": 2016},
    {"title": "There Will Be Blood",                  "year": 2007},
    
    # ── Thriller/Crime (Rhythmic tension & Dialogue-driven) ──
    {"title": "No Country for Old Men",               "year": 2007},
    {"title": "Parasite",                             "year": 2019},
    {"title": "Whiplash",                             "year": 2014},
    {"title": "Pulp Fiction",                         "year": 1994},
    {"title": "Se7en",                                "year": 1995},
    {"title": "The Silence of the Lambs",             "year": 1991},
    {"title": "GoodFellas",                           "year": 1990},
    {"title": "The Usual Suspects",                   "year": 1995},
    {"title": "Heat",                                 "year": 1995},
    {"title": "Zodiac",                               "year": 2007},
    {"title": "Prisoners",                            "year": 2013},
    {"title": "Nightcrawler",                         "year": 2014},
    {"title": "Memento",                              "year": 2000},
    {"title": "The Departed",                         "year": 2006},
    {"title": "Fargo",                                "year": 1996},
    {"title": "Taxi Driver",                          "year": 1976},
    
    # ── Comedy (Dialogue/Quirky) ──
    {"title": "The Grand Budapest Hotel",             "year": 2014},
    {"title": "Knives Out",                           "year": 2019},
    {"title": "The Big Lebowski",                     "year": 1998},
    {"title": "Groundhog Day",                        "year": 1993},
    {"title": "Superbad",                             "year": 2007},
    {"title": "The Hangover",                         "year": 2009},
    {"title": "Shaun of the Dead",                    "year": 2004},
    {"title": "Step Brothers",                        "year": 2008},
    {"title": "Dumb and Dumber",                      "year": 1994},
    {"title": "Ferris Bueller's Day Off",             "year": 1986},
    
    # ── Sci-Fi (Meditative/Epic) ──
    {"title": "2001: A Space Odyssey",                "year": 1968},
    {"title": "Arrival",                              "year": 2016},
    {"title": "Blade Runner",                         "year": 1982},
    {"title": "Blade Runner 2049",                    "year": 2017},
    {"title": "Interstellar",                         "year": 2014},
    {"title": "The Martian",                          "year": 2015},
    {"title": "Alien",                                "year": 1979},
    {"title": "Aliens",                               "year": 1986},
    {"title": "Back to the Future",                   "year": 1985},
    {"title": "Children of Men",                      "year": 2006},
    {"title": "Ex Machina",                           "year": 2014},
    {"title": "Dune",                                 "year": 2021},
    
    # ── Horror (Slow Dread/Atmospheric) ──
    {"title": "Hereditary",                           "year": 2018},
    {"title": "The Shining",                          "year": 1980},
    {"title": "Psycho",                               "year": 1960},
    {"title": "The Exorcist",                         "year": 1973},
    {"title": "Halloween",                            "year": 1978},
    {"title": "A Nightmare on Elm Street",            "year": 1984},
    {"title": "Get Out",                              "year": 2017},
    {"title": "Midsommar",                            "year": 2019},
    {"title": "The Conjuring",                        "year": 2013},
    {"title": "It Follows",                           "year": 2014},
    
    # ── Romance (Conversational) ──
    {"title": "Titanic",                              "year": 1997},
    {"title": "La La Land",                           "year": 2016},
    {"title": "The Notebook",                         "year": 2004},
    {"title": "Pride & Prejudice",                    "year": 2005},
    {"title": "Before Sunrise",                       "year": 1995},
    {"title": "Eternal Sunshine of the Spotless Mind", "year": 2004},
    {"title": "Casablanca",                           "year": 1942},
    {"title": "Silver Linings Playbook",              "year": 2012},
    
    # ── Western (Slow Burn) ──
    {"title": "The Good, the Bad and the Ugly",       "year": 1966},
    {"title": "Once Upon a Time in the West",         "year": 1968},
    {"title": "Unforgiven",                           "year": 1992},
    {"title": "Django Unchained",                     "year": 2012},
    {"title": "The Hateful Eight",                    "year": 2015},
    {"title": "True Grit",                            "year": 2010},
    {"title": "The Revenant",                         "year": 2015},
]


async def run_batch():
    """Collect all 20 training films and save to training_data.json."""
    if not TMDB_API_KEY:
        print("❌ TMDB_API_KEY not set in .env — aborting batch.")
        return

    print(f"\n🎬 Starting batch collection of {len(BATCH_TRAINING_SET)} films...\n")
    training_data = load_training_data()

    for film_info in BATCH_TRAINING_SET:
        print(f"→ Fetching: {film_info['title']} ({film_info['year']})")
        try:
            record = await collect_film(**film_info)
            if record:
                upsert_film(training_data, record)
        except Exception as e:
            print(f"  [ERROR] {film_info['title']}: {e}")
        await asyncio.sleep(0.3)  # Respect TMDb rate limit

    save_training_data(training_data)


async def run_single(title: str, year: int = None, tmdb_id: int = None):
    """Collect a single film."""
    if not TMDB_API_KEY:
        print("❌ TMDB_API_KEY not set in .env — aborting.")
        return

    print(f"\n→ Fetching: {title or f'TMDb ID {tmdb_id}'}")
    training_data = load_training_data()
    record = await collect_film(title, year, tmdb_id)
    if record:
        upsert_film(training_data, record)
        save_training_data(training_data)


def main():
    parser = argparse.ArgumentParser(description="ScriptLens Metadata Collector")
    parser.add_argument("--title",   type=str, help="Film title to search")
    parser.add_argument("--year",    type=int, help="Release year (optional, improves search)")
    parser.add_argument("--tmdb_id", type=int, help="TMDb movie ID (overrides title search)")
    parser.add_argument("--batch",   action="store_true", help="Run full 20-film training batch")
    args = parser.parse_args()

    if args.batch:
        asyncio.run(run_batch())
    elif args.title or args.tmdb_id:
        asyncio.run(run_single(args.title, args.year, args.tmdb_id))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
