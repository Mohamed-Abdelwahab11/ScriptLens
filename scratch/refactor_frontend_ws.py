import re

with open("frontend/script.js", "r") as f:
    content = f.read()

# Locate the exact bounds of `runAnalysis`
start_idx = content.find("async function runAnalysis() {")
end_idx = content.find("\n// ============================================================\n// SHOOTING SCHEDULE OPTIMIZER")

if start_idx != -1 and end_idx != -1:
    new_func = """async function runAnalysis() {
    const scriptInput = document.getElementById('scriptInput');
    const loglineInput = document.getElementById('loglineInput');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const loading = document.getElementById('loading');
    const analyticsSection = document.getElementById('analyticsSection');
    const resultsContainer = document.getElementById('resultsContainer');

    if (!scriptInput.value.trim()) return alert("Please paste the script first!");

    // Reset UI
    analyzeBtn.disabled = true;
    loading.classList.remove('hidden');
    analyticsSection.classList.add('hidden');
    resultsContainer.classList.add('hidden');
    resultsContainer.innerHTML = '';
    
    const loadingProgressBar = document.getElementById('loadingProgressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressEstimate = document.getElementById('progressEstimate');
    
    loadingProgressBar.style.width = '0%';
    progressPercent.innerText = '0%';
    progressEstimate.innerText = 'CONNECTING TO CINEMATIC ENGINE...';

    // Set up WebSocket
    const wsUrl = `ws://127.0.0.1:8000/ws/analyze`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        progressEstimate.innerText = 'ANALYZING SCRIPT TOPOLOGY...';
        ws.send(JSON.stringify({ 
            script_text: scriptInput.value, 
            logline: loglineInput.value
        }));
    };

    ws.onmessage = async (event) => {
        try {
            const msg = JSON.parse(event.data);
            
            if (msg.type === "progress") {
                const percent = Math.floor((msg.current_chunk / msg.total_chunks) * 100);
                loadingProgressBar.style.width = `${percent}%`;
                progressPercent.innerText = `${percent}%`;
                progressEstimate.innerText = msg.message.toUpperCase();
            } else if (msg.type === "complete") {
                loadingProgressBar.style.width = '100%';
                progressPercent.innerText = '100%';
                progressEstimate.innerText = 'ANALYSIS COMPLETE. RENDERING...';
                
                await new Promise(r => setTimeout(r, 400)); // Small pause for UX
                
                const data = msg.data;
                if (data.analysis && data.analysis.length > 0) {
                    document.getElementById('totalDurationText').innerText = "Calculating...";
                    window.currentAnalysisData = data;
                    renderDashboard(data);
                    analyticsSection.classList.remove('hidden');
                    resultsContainer.classList.remove('hidden');
                    document.getElementById('exportPdfBtn').classList.remove('hidden');
                } else if (data.error) {
                    throw new Error(data.error);
                } else {
                    alert("Analysis failed. The AI returned empty data, likely due to API rate limits.");
                }
                
                analyzeBtn.disabled = false;
                loading.classList.add('hidden');
                ws.close();
            } else if (msg.type === "error") {
                throw new Error(msg.message);
            }
        } catch (err) {
            console.error("WS Error:", err);
            progressEstimate.innerText = 'ERROR: ' + err.message;
            progressEstimate.classList.add('text-red-500');
            alert("Error occurred: " + err.message);
            analyzeBtn.disabled = false;
            loading.classList.add('hidden');
            ws.close();
        }
    };

    ws.onerror = (error) => {
        console.error("WebSocket connection error:", error);
        progressEstimate.innerText = 'CONNECTION ERROR. IS BACKEND RUNNING?';
        progressEstimate.classList.add('text-red-500');
        analyzeBtn.disabled = false;
        loading.classList.add('hidden');
    };
    
    ws.onclose = () => {
        // If it closed unexpectedly
        if (analyzeBtn.disabled && !loading.classList.contains('hidden')) {
            analyzeBtn.disabled = false;
            loading.classList.add('hidden');
        }
    };
}
"""
    content = content[:start_idx] + new_func + content[end_idx:]
    with open("frontend/script.js", "w") as f:
        f.write(content)
    print("Successfully replaced runAnalysis")
else:
    print("Could not find bounds of runAnalysis")
