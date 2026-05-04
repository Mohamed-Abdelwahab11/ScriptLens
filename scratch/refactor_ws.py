import re

with open("src/main.py", "r") as f:
    content = f.read()

# 1. Import WebSocket
content = content.replace(
    "from fastapi import FastAPI",
    "from fastapi import FastAPI, WebSocket, WebSocketDisconnect"
)

# 2. Refactor analyze_script to run_analysis_logic
content = content.replace(
    "async def analyze_script(data: dict):",
    "async def analyze_script(data: dict):\n    return await run_analysis_logic(data)\n\nasync def run_analysis_logic(data: dict, websocket: WebSocket = None):"
)

# 3. Inject websocket progress in loop
search_loop = """            res = await process_chunk(chunk, logline, current_memory, pacing_bias, model_name)
            raw_results.append(res)"""
            
replace_loop = """            if websocket:
                await websocket.send_json({
                    "type": "progress", 
                    "current_chunk": len(raw_results) + 1, 
                    "total_chunks": len(chunks_with_context), 
                    "message": f"Processing script block {len(raw_results) + 1} of {len(chunks_with_context)}..."
                })
            res = await process_chunk(chunk, logline, current_memory, pacing_bias, model_name)
            raw_results.append(res)"""

content = content.replace(search_loop, replace_loop)

# 4. Add websocket endpoint
ws_endpoint = """
@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        result = await run_analysis_logic(data, websocket)
        await websocket.send_json({"type": "complete", "data": result})
    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
"""

content = content + ws_endpoint

with open("src/main.py", "w") as f:
    f.write(content)

print("Updated main.py")
