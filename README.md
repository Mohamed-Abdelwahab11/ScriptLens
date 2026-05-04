<div align="center">

# 🎥 ScriptLens
**The Professional AI-Driven Cinematic Screenplay Analysis Engine**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688.svg)](https://fastapi.tiangolo.com/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-brightgreen.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)
[![Groq](https://img.shields.io/badge/LLM-Llama_3_via_Groq-orange.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

---

**ScriptLens** is a next-generation AI-powered screenplay analysis platform that bridges the gap between creative screenwriting and technical film production. Upload a screenplay PDF or paste raw text, and ScriptLens autonomously generates professional cinematic data — translating raw script text into actionable directorial insights with surgical precision.

---

## ✨ Key Features

### 🧠 Intelligent Analysis Engine
- **State-Machine Script Parser:** A rule-based, context-aware parser separates Dialogue, Action, Character Names, and Parentheticals with high precision — eliminating misclassification errors.
- **Location Guard:** Strict `INT.`/`EXT.` header extraction prevents AI hallucinations. Only real scene headers are recognized as valid locations — dialogue mentions of locations are strictly ignored.
- **Auto Genre Detection:** Scores script content against 12 cinematic genre vocabularies to transparently identify the film's genre with no user input required.
- **Dual-Track Cinematic Math:** Abandons the outdated "1 page = 1 minute" rule. Calculates runtime by processing:
  - *Dialogue* at human speech limits (~2.3 Words Per Second)
  - *Action* via genre-specific elastic pacing multipliers, informed by AI tension analysis
- **Shot Density Control:** Drama scenes are capped at 1-3 high-impact shots per minute. Action sequences allow 6-10 shots per minute — aligned with the detected genre pacing bias.

### 🎬 Real-Time Director's Dashboard
- **Live WebSocket Streaming:** The backend streams progress events directly to the browser via WebSockets — no more blind polling or frozen UIs.
- **Multi-Level Pacing Synchronization:**
  - **Shot-Level Control:** Every individual shot has its own Pacing Slider for surgical adjustments.
  - **Bottom-Up Sync:** Adjusting a single shot's pacing instantly recalculates the Scene Duration and the Total Film Runtime at the top of the page.
  - **Top-Down Inheritance:** Setting a Scene's pacing multiplier proportionally scales all shots within it.
- **Runtime Breakdown Panel:** Visually separates Dialogue time, Action time, and Overhead time.
- **Director's Lock (🔐):** Lock a preferred shot direction to prevent it from being overwritten during re-analysis.
- **Alternative Shot Swapper:** Instantly swap any shot for one of its two AI-generated cinematic alternatives.

### ⚡ Performance & Reliability
- **MD5 Cache with Logic Versioning:** Analysis results are cached to disk using a content hash. The cache automatically invalidates when the engine's core logic is updated (`LOGIC_VERSION`), ensuring results are never stale.
- **Smart Model Switching:** Automatically switches between `llama-3.3-70b-versatile` (for quality) and `llama-3.1-8b-instant` (for speed/rate-limit compliance) based on script length.
- **Sequential Chunk Processing:** Processes script chunks sequentially with Narrative Memory context to preserve the emotional continuity of the story.
- **Exponential Backoff:** Gracefully handles Groq API rate limits with automatic retry logic.

---

## 🏗 Architecture

```
ScriptLens/
├── src/
│   ├── main.py                # FastAPI backend, WebSocket endpoint, analysis engine
│   ├── calibration.json       # Auto-learned genre pacing multipliers
│   └── training_data.json     # Historical film runtime training database
├── frontend/
│   ├── index.html             # Main dashboard UI
│   └── script.js              # WebSocket client, rendering & pacing logic
├── data/
│   └── cache/                 # MD5-versioned analysis cache (gitignored)
├── run_server.py              # Helper script to start the backend correctly
└── docker-compose.yml
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- API Key from [Groq](https://console.groq.com/) (`GROQ_API_KEY`)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Mohamed-Abdelwahab11/ScriptLens.git
   cd ScriptLens
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your environment:**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. **Start the backend server:**
   ```bash
   python3 run_server.py
   ```

5. **Open the frontend:**
   Open `frontend/index.html` directly in your browser.
   - Backend API: `http://127.0.0.1:8000`
   - WebSocket: `ws://127.0.0.1:8000/ws/analyze`

### Docker Deployment

```bash
docker-compose up -d --build
```
- Frontend Dashboard: `http://localhost:3000`
- Backend API: `http://localhost:8000`

---

## ⚙️ How It Works (The Math)

ScriptLens uses a proprietary **Dual-Track Cinematic Duration Model**:

| Track | Rate | Source |
|---|---|---|
| **Dialogue** | ~2.3 WPS (human speech ceiling) | State-Machine Parser |
| **Action** | Genre-specific WPS × AI Pacing Multiplier | Groq LLM + Calibration DB |
| **Overhead** | Excluded from duration | Parser (Headers, Transitions) |

The `pacing_multiplier` is the key variable — an AI-estimated float representing the ratio of *described time* to *real screen time*. A slow emotional close-up on a tear might have a multiplier of `3.0` (3 seconds of screen time per second of described action). A frenetic fight sequence might be `0.5`.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Check the [issues page](https://github.com/Mohamed-Abdelwahab11/ScriptLens/issues).

---

<div align="center">
  <i>Built for filmmakers, powered by engineers.</i>
</div>