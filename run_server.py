import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure the root directory is in the python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.append(current_dir)
        
    print(f"Starting ScriptLens Cinematic Engine on http://127.0.0.1:8000")
    print(f"WebSocket: ws://127.0.0.1:8000/ws/analyze")
    
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
