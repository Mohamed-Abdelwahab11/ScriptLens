# ScriptLens 

**ScriptLens** is a professional AI-driven tool designed to bridge the gap between creative screenwriting and technical film production.

##  Tech Stack
* **Language:** Python 3.12
* **AI/NLP:** Llama 3 / Transformers
* **Environment:** Docker
* **Operating System:** macOS (Apple Silicon Optimized)

##  Project Structure
- `src/core`: Internal logic and NLP processing.
- `src/api`: Interface and communication layer.
- `docker/`: Deployment configurations.
- `data/`: Raw scripts and processed metadata.

##  Getting Started
1. Build the Docker image: `docker build -t scriptlens .`
2. Run the container: `docker run scriptlens`