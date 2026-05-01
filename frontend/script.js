/** 
 * ScriptLens v2.0 - Final Production Controller 
 * Refactored Logic for Pacing, Range, and World Cinema Refs
 */

console.log("ScriptLens JS is LIVE!");
const API_BASE_URL = 'http://127.0.0.1:8000';
let shotChart = null, storyArcChart = null;

// Initialize PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

function formatTime(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = Math.floor(seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('pdfUpload').addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        if (file.type !== 'application/pdf') return alert("Please upload a PDF file.");
        
        const loading = document.getElementById('loading');
        loading.classList.remove('hidden');
        document.getElementById('scriptInput').value = "Extracting text from PDF, please wait...";
        
        try {
            const arrayBuffer = await file.arrayBuffer();
            const pdf = await pdfjsLib.getDocument(arrayBuffer).promise;
            let fullText = "";
            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                const pageText = textContent.items.map(item => item.str).join(" ");
                fullText += pageText + "\n\n";
            }
            document.getElementById('scriptInput').value = fullText;
        } catch (err) {
            console.error("PDF Extraction error:", err);
            document.getElementById('scriptInput').value = "";
            alert("Error reading PDF file.");
        } finally {
            loading.classList.add('hidden');
        }
    });
});

async function runAnalysis() {
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

    try {
        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                script_text: scriptInput.value, 
                logline: loglineInput.value 
            })
        });

        const data = await response.json();
        
        if (data.analysis && data.analysis.length > 0) {
            document.getElementById('totalDurationText').innerText = "Calculating...";
            
            renderDashboard(data);
            analyticsSection.classList.remove('hidden');
            resultsContainer.classList.remove('hidden');
        }
    } catch (err) {
        alert("Backend not responding. Check Uvicorn!");
    } finally {
        analyzeBtn.disabled = false;
        loading.classList.add('hidden');
    }
}

function renderDashboard(data) {
    const container = document.getElementById('resultsContainer');
    container.innerHTML = ''; 
    let chartCounts = { WIDE: 0, MEDIUM: 0, "CLOSE UP": 0 }, tensionData = [], timelineHTML = '';
    let totalShots = 0, totalFilmSeconds = 0;

    data.analysis.forEach((scene, sIdx) => {
        tensionData.push(scene?.scene_tension_score || 0);
        let shotsHTML = '';
        
        let sceneDuration = scene.scene_duration_seconds || 0;
        let shotSumSeconds = 0;

        (scene.shots || []).forEach((shot, i) => {
            totalShots++;
            const type = (shot.shot_type || "MEDIUM").toUpperCase();
            const duration = shot.estimated_seconds || 5;
            shotSumSeconds += duration;
            
            const colorClass = type.includes("WIDE") ? "emerald" : type.includes("CLOSE") ? "orange" : "blue";
            
            if (type.includes("WIDE")) chartCounts.WIDE++;
            else if (type.includes("CLOSE")) chartCounts["CLOSE UP"]++;
            else chartCounts.MEDIUM++;

            timelineHTML += `<div class="shot-block bg-${colorClass}-500 h-8 rounded-sm mr-1 shadow-lg" style="min-width: ${duration * 15}px"></div>`;

            shotsHTML += `
                <div class="bg-slate-900/60 p-6 rounded-[2.5rem] border-l-8 border-${colorClass}-500 mb-6 shadow-2xl">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <span class="text-[11px] font-black uppercase tracking-[0.2em] text-${colorClass}-400">Shot ${totalShots} • ${type}</span>
                            <div class="flex gap-2 mt-2">
                                <span class="badge-tag badge-angle">🎥 ANGLE: ${shot.angle || 'Eye Level'}</span>
                                <span class="badge-tag badge-movement">🎬 MOVE: ${shot.movement || 'Static'}</span>
                            </div>
                        </div>
                        <span class="text-xs font-mono text-slate-400 font-black">${duration}S</span>
                    </div>
                    <p class="text-slate-200 text-sm leading-relaxed mb-4 font-medium italic border-l border-slate-700 pl-3">"${shot.cinematic_reasoning}"</p>
                    <div class="pt-4 border-t border-white/5 text-[9px] font-black text-blue-400 uppercase tracking-widest">
                        🎥 REF: ${shot.director_reference} • ${shot.movie_reference}
                    </div>
                </div>`;
        });

        container.insertAdjacentHTML('beforeend', `
            <div class="glass-card p-10 rounded-[4rem] mb-12 border border-white/5 shadow-2xl">
                <div class="grid grid-cols-1 lg:grid-cols-4 gap-12">
                    <div class="space-y-6">
                        <div class="inline-block px-4 py-1 bg-blue-500/10 rounded-full border border-blue-500/20 text-[10px] font-black text-blue-400 uppercase tracking-widest">Scene ${sIdx + 1}</div>
                        <h3 class="text-3xl font-black text-white leading-none tracking-tighter">${scene.scene_header}</h3>
                        <p class="text-xs text-blue-400 font-bold uppercase tracking-widest">${(scene.characters || []).join(' • ')}</p>
                    </div>
                    <div class="lg:col-span-3">${shotsHTML}</div>
                </div>
            </div>`);
            
        // If AI didn't provide scene duration, fallback to sum of shots
        if (sceneDuration === 0) sceneDuration = shotSumSeconds;
        totalFilmSeconds += sceneDuration;
    });

    const totalMinutes = totalFilmSeconds / 60;
    const pacingValue = parseFloat((totalShots / (totalMinutes || 1)).toFixed(1));
    document.getElementById('pacingText').innerText = pacingValue;
    
    // Dynamic color for pacing bar based on intensity
    let pacingColor = "bg-blue-500";
    if (pacingValue > 15) pacingColor = "bg-red-500";
    else if (pacingValue > 10) pacingColor = "bg-orange-500";
    else if (pacingValue < 5) pacingColor = "bg-emerald-500";
    
    const pacingBar = document.getElementById('pacingBar');
    pacingBar.className = `${pacingColor} h-full transition-all duration-1000 shadow-[0_0_15px_rgba(0,0,0,0.5)]`;
    // Max visual bar width mapping
    pacingBar.style.width = `${Math.min(pacingValue * 4, 100)}%`;
    pacingBar.style.boxShadow = `0 0 10px var(--tw-ring-color, currentColor)`; // Add glow

    document.getElementById('visualRhythmTimeline').innerHTML = timelineHTML;

    const rangeText = data.estimated_runtime_range ? `EST: ${data.estimated_runtime_range}` : 'Calculating...';
    document.getElementById('totalDurationText').innerHTML = `${rangeText} <span class="text-lg text-slate-500 ml-2">(${formatTime(totalFilmSeconds)})</span>`;

    updateCharts(chartCounts, tensionData);
}

function updateCharts(c, d) {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                position: 'bottom', 
                labels: { boxWidth: 8, font: { size: 8 }, color: '#94a3b8', padding: 10 } 
            }
        }
    };

    const ctx1 = document.getElementById('shotChart').getContext('2d');
    if (shotChart) shotChart.destroy();
    shotChart = new Chart(ctx1, {
        type: 'doughnut',
        data: { 
            labels: ['Wide', 'Medium', 'Close-Up'], 
            datasets: [{ data: [c.WIDE, c.MEDIUM, c["CLOSE UP"]], backgroundColor: ['#10b981', '#3b82f6', '#f59e0b'], borderWidth: 0 }] 
        },
        options: { ...chartOptions, cutout: '75%' }
    });

    const ctx2 = document.getElementById('storyArcChart').getContext('2d');
    if (storyArcChart) storyArcChart.destroy();
    storyArcChart = new Chart(ctx2, {
        type: 'line',
        data: { 
            labels: d.map((_,i)=>`Sc ${i+1}`), 
            datasets: [{ label: 'Tension', data: d, borderColor: '#3b82f6', tension: 0.4, fill: true, backgroundColor: 'rgba(59, 130, 246, 0.1)' }] 
        },
        options: { ...chartOptions, scales: { y: { min: 0, max: 10, ticks: { color: '#475569' } }, x: { ticks: { color: '#475569' } } } }
    });
}
