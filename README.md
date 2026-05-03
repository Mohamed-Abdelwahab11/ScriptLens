<div align="center">
  
# 🎥 ScriptLens
**The Professional AI-Driven Cinematic Screenplay Engine**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)
[![LLM](https://img.shields.io/badge/LLM-Llama%_3-orange.svg)](https://ai.meta.com/llama/)

</div>

---

**ScriptLens** is a next-generation AI tool designed to bridge the gap between creative screenwriting and technical film production. By analyzing screenplays, ScriptLens autonomously generates professional cinematic data, translating raw text into actionable directorial insights.

## ✨ Core Features

* **Dual-Track Cinematic Math Algorithm:** Accurately estimates film runtime by organically separating dialogue and action tracks, ensuring a realistic, industry-standard pacing.
* **Auto-Calibration Engine:** Self-corrects its runtime estimates by continuously learning from a built-in database of 100+ analyzed films across various genres.
* **Semantic Shot Breakdown:** Translates narrative memory into camera movements, angles, and shot sizes (e.g., Extreme Close Up for emotional beats, Tracking Wide for action).
* **Cinematic Heuristics:** Automatically detects genres and estimates color palettes, tension scores, and average shot lengths (ASL) for directors.

## 🏗 Architecture

- **`src/`**: The core AI analysis engine, built with FastAPI, executing Llama 3 via Groq for high-speed inference.
- **`frontend/`**: The dashboard interface (HTML/JS/CSS) visualizing the data, tension graphs, and color palettes.
- **`data/` & `models/`**: Stores raw scripts, processed metadata, and the auto-calibrating runtime multipliers.

## 🚀 Getting Started

ScriptLens is containerized for seamless execution across platforms (optimized for Apple Silicon & Linux).

### Prerequisites
- Docker & Docker Compose
- API Key from Groq (`GROQ_API_KEY`)
- API Key from TMDb (`TMDB_API_KEY`)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Mohamed-Abdelwahab11/ScriptLens.git
   cd ScriptLens
   ```

2. **Configure your environment:**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key
   TMDB_API_KEY=your_tmdb_api_key
   ```

3. **Deploy via Docker Compose:**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the application:**
   - Frontend Dashboard: `http://localhost:3000`
   - Backend API: `http://localhost:8000`

## ⚙️ How It Works (The Math)

ScriptLens abandons archaic "one page equals one minute" heuristics. Instead, it relies on our proprietary **Dual-Track Math**:
1. It physically isolates actionable words from non-actionable elements (Scene Headers, Transitions).
2. It processes *Dialogue* at human speech limits (~2.3 Words Per Second).
3. It processes *Action* via genre-specific elastic pacing multipliers dictated by the AI's tension analysis.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Mohamed-Abdelwahab11/ScriptLens/issues).

---
<div align="center">
  <i>Built for filmmakers and engineers.</i>
</div>