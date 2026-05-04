/** 
 * ScriptLens — Director's Cinematic Engine
 */

console.log("ScriptLens JS is LIVE!");
const API_BASE_URL = 'http://127.0.0.1:8000';
let shotChart = null, storyArcChart = null;
window.currentAnalysisData = null;
window.normalizationRatio = 1.0;


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
    
    const loadingProgressBar = document.getElementById('loadingProgressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressEstimate = document.getElementById('progressEstimate');
    
    loadingProgressBar.style.width = '0%';
    progressPercent.innerText = '0%';
    progressEstimate.innerText = 'CONNECTING TO CINEMATIC ENGINE...';

    // Set up WebSocket
    const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws/analyze';
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
            loadingProgressBar.classList.add('bg-red-500');
            loadingProgressBar.classList.remove('bg-gradient-to-r', 'from-blue-500', 'to-indigo-500');
            analyzeBtn.disabled = false;
            ws.close();
        }
    };

    ws.onerror = (error) => {
        console.error("WebSocket connection error:", error);
        progressEstimate.innerText = 'CONNECTION ERROR. PLEASE RESTART THE BACKEND SERVER.';
        progressEstimate.classList.add('text-red-500');
        loadingProgressBar.classList.add('bg-red-500');
        loadingProgressBar.classList.remove('bg-gradient-to-r', 'from-blue-500', 'to-indigo-500');
        analyzeBtn.disabled = false;
    };
    
    ws.onclose = () => {
        analyzeBtn.disabled = false;
    };
}

// ============================================================
// SHOOTING SCHEDULE OPTIMIZER
// Groups scenes by parsed location, estimates production days based on ML metrics
// ============================================================
function renderShootingSchedule(scenes, metrics) {
    const grid = document.getElementById('shootingScheduleGrid');
    const daysEl = document.getElementById('scheduleTotalDays');
    if (!grid || !scenes) return;
    grid.innerHTML = '';

    // Parse location from scene header (e.g. "INT. KITCHEN - DAY" → "KITCHEN")
    const locationMap = {};
    scenes.forEach((scene, idx) => {
        const header = (scene.scene_header || '').toUpperCase();
        // Remove INT./EXT./I/E, remove everything after a dash, remove content in parentheses
        let loc = header.replace(/^(INT\.|EXT\.|INT\/EXT\.|I\/E\.|INT|EXT)\s*/, '')
                        .replace(/\(.*?\)/g, '') // remove anything in parentheses
                        .split(/[\-–—]/)[0] // take everything before the first dash
                        .replace(/[^A-Z0-9\s]/g, '') // remove special characters
                        .trim();
        
        if (!loc) loc = 'UNKNOWN LOCATION';

        // Intelligent Grouping: if loc contains another loc or vice versa (e.g. "BEDROOM" and "JOHNS BEDROOM"), 
        // we keep them separate because they are physically different sets, but we normalize exact matches.
        if (!locationMap[loc]) {
            locationMap[loc] = { scenes: [], totalSeconds: 0, timeOfDay: [] };
        }
        const duration = scene.scene_duration_seconds || 0;
        locationMap[loc].scenes.push({ idx: idx + 1, header: scene.scene_header, duration, tension: scene.scene_tension_score || 5 });
        locationMap[loc].totalSeconds += duration;

        const tod = header.includes('NIGHT') || header.includes('DUSK') || header.includes('EVENING') ? 'NIGHT' : 'DAY';
        if (!locationMap[loc].timeOfDay.includes(tod)) locationMap[loc].timeOfDay.push(tod);
    });

    // Sort locations by total screen time desc
    const sorted = Object.entries(locationMap).sort((a,b) => b[1].totalSeconds - a[1].totalSeconds);

    // Production day estimate: Use ML metrics for pages per day, fallback to 5 (300s)
    const pagesPerDay = (metrics && metrics.pages_shot_per_day) ? metrics.pages_shot_per_day : 5.0;
    const SCREEN_TIME_PER_DAY = pagesPerDay * 60; // 1 page ≈ 60 seconds
    let totalDays = 0;

    const colorClasses = [
        { bg: 'rgba(59,130,246,0.12)', border: '#3b82f6', text: '#93c5fd', badge: 'bg-blue-500/20 text-blue-300 border-blue-500/30' },
        { bg: 'rgba(168,85,247,0.12)', border: '#a855f7', text: '#d8b4fe', badge: 'bg-purple-500/20 text-purple-300 border-purple-500/30' },
        { bg: 'rgba(245,158,11,0.12)', border: '#f59e0b', text: '#fcd34d', badge: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
        { bg: 'rgba(16,185,129,0.12)', border: '#10b981', text: '#6ee7b7', badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
        { bg: 'rgba(239,68,68,0.12)', border: '#ef4444', text: '#fca5a5', badge: 'bg-red-500/20 text-red-300 border-red-500/30' },
        { bg: 'rgba(20,184,166,0.12)', border: '#14b8a6', text: '#5eead4', badge: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
    ];

    sorted.forEach(([loc, info], colorIdx) => {
        const c = colorClasses[colorIdx % colorClasses.length];
        const days = Math.max(1, Math.ceil(info.totalSeconds / SCREEN_TIME_PER_DAY));
        totalDays += days;
        const avgTension = info.scenes.reduce((s,sc) => s + sc.tension, 0) / info.scenes.length;
        const todBadges = info.timeOfDay.map(t => `<span class="px-2 py-0.5 rounded text-[8px] font-black border ${t==='NIGHT' ? 'bg-slate-700 text-slate-300 border-slate-600' : 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'}">${t}</span>`).join('');

        grid.insertAdjacentHTML('beforeend', `
            <div class="rounded-2xl p-5 border-l-4 transition-all hover:scale-[1.01]" style="background:${c.bg}; border-color:${c.border};">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="text-[9px] font-black uppercase tracking-widest mb-1" style="color:${c.text}">📍 ${loc}</div>
                        <div class="flex gap-1 flex-wrap">${todBadges}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-black text-white">${days}</div>
                        <div class="text-[8px] text-slate-500 uppercase font-black tracking-widest">${days === 1 ? 'SHOOT DAY' : 'SHOOT DAYS'}</div>
                    </div>
                </div>
                <div class="border-t border-white/5 pt-3 mt-3 space-y-1.5">
                    ${info.scenes.slice(0, 3).map(sc => `
                        <div class="flex justify-between items-center">
                            <span class="text-[9px] text-slate-400 truncate max-w-[75%]">Scene ${sc.idx}: ${sc.header}</span>
                            <span class="text-[8px] font-black text-slate-500">${formatTime(sc.duration)}</span>
                        </div>`).join('')}
                    ${info.scenes.length > 3 ? `<div class="text-[9px] text-slate-600 font-black uppercase tracking-widest pt-1">+${info.scenes.length - 3} more scenes</div>` : ''}
                </div>
                <div class="mt-3 pt-3 border-t border-white/5 flex justify-between items-center">
                    <span class="text-[9px] font-black uppercase tracking-widest text-slate-500">${info.scenes.length} scenes · ${formatTime(info.totalSeconds)} screen time</span>
                    <span class="text-[9px] font-black px-2 py-0.5 rounded border ${avgTension >= 7 ? 'bg-red-500/20 text-red-400 border-red-500/30' : avgTension >= 4 ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' : 'bg-slate-500/20 text-slate-400 border-slate-500/30'}">TENSION ${avgTension.toFixed(1)}</span>
                </div>
            </div>
        `);
    });

    daysEl.innerText = `${totalDays} TOTAL SHOOT DAYS`;
}


// ============================================================
// MOOD & COLOR PALETTE BOARD
// Maps scene tension + context → cinematic color language
// ============================================================
function renderMoodBoard(scenes, metrics) {
    const grid = document.getElementById('moodPaletteGrid');
    if (!grid || !scenes) return;
    grid.innerHTML = '';

    // If ML metrics provided dynamic color palette, inject it as the main primary palette
    if (metrics && metrics.color_palette_hex && metrics.color_palette_hex.length > 0) {
        const mlColors = metrics.color_palette_hex;
        const moodLabel = (metrics.primary_mood || 'Cinematic Mood').toUpperCase();
        
        let colorSwatches = '';
        let gradientStops = mlColors.map((c, i) => `${c} ${(i / (mlColors.length - 1)) * 100}%`).join(', ');
        
        mlColors.forEach(c => {
            colorSwatches += `
                <div class="flex-1 group relative flex items-end p-2 transition-all duration-300 hover:flex-[1.5]" 
                     style="background-color: ${c};">
                     <div class="opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 backdrop-blur-sm text-white text-[8px] font-mono p-1 rounded">
                         ${c.toUpperCase()}
                     </div>
                </div>
            `;
        });

        grid.insertAdjacentHTML('beforeend', `
            <div class="col-span-full rounded-2xl bg-[#0f172a] p-6 border border-white/10 relative overflow-hidden mb-6 shadow-2xl">
                <!-- Ambient Glow Background -->
                <div class="absolute inset-0 opacity-20 blur-3xl" style="background: linear-gradient(90deg, ${gradientStops});"></div>
                
                <div class="absolute -right-4 -top-4 text-8xl opacity-[0.03]">🎨</div>
                
                <div class="flex justify-between items-end mb-6 relative z-10">
                    <div>
                        <div class="flex items-center gap-3 mb-2">
                            <span class="text-2xl">✨</span>
                            <h4 class="text-white font-black tracking-widest text-xs uppercase">ML Cinematic Master Palette</h4>
                        </div>
                        <p class="text-[10px] text-slate-400 uppercase tracking-widest bg-slate-800/50 inline-block px-3 py-1 rounded-full border border-white/5">
                            Mood: <span class="text-white font-bold">${moodLabel}</span> · Data: 500-Film ML Core
                        </p>
                    </div>
                </div>
                
                <div class="flex h-24 rounded-xl overflow-hidden shadow-2xl border border-white/10 relative z-10 ring-1 ring-black/50">
                    ${colorSwatches}
                </div>
                
                <div class="mt-4 pt-4 border-t border-white/5 flex gap-4 text-[9px] text-slate-500 uppercase tracking-widest font-bold">
                    <span>Generated via Genre Norms</span>
                    <span>•</span>
                    <span>Lighting: ${moodLabel.includes('TENSE') ? 'High Contrast / Hard Light' : moodLabel.includes('INTIMATE') ? 'Soft / Diffused' : 'Dynamic / Motivated'}</span>
                </div>
            </div>
        `);
    }

    // Cinematic mood → color palette mapping (based on film theory)
    const MOOD_PALETTES = [
        { // High tension / Conflict / Thriller (tension 8-10)
            minTension: 8, label: 'HIGH TENSION · CONFLICT', icon: '⚡',
            mood: 'Aggression · Fear · Urgency',
            colors: ['#1a0a0a','#3d1515','#8b1a1a','#c0392b','#e74c3c','#ff6b6b'],
            names: ['Shadow Black','Blood Dark','Crimson Deep','Cardinal Red','Alert Red','Danger Light'],
            lighting: 'High Contrast · Deep Shadows · Underexposed Highlights',
            reference: 'The Godfather (1972) · No Country for Old Men (2007)',
            director: 'Gordon Willis · Roger Deakins'
        },
        { // Drama / Emotional (tension 5-7)
            minTension: 5, maxTension: 7, label: 'EMOTIONAL DRAMA · INTIMACY', icon: '🎭',
            mood: 'Vulnerability · Longing · Connection',
            colors: ['#0d1b2a','#1b3a4b','#2d6a8a','#5b9bd5','#a8c8e8','#e8f4f8'],
            names: ['Deep Night','Ocean Dark','Steel Blue','Sky Reflect','Pale Ice','Breath White'],
            lighting: 'Soft Diffused · Motivated Practicals · Window Light',
            reference: 'Carol (2015) · Moonlight (2016)',
            director: 'Edward Lachman · James Laxton'
        },
        { // Family / Warmth / Hope (tension 1-4)
            minTension: 0, maxTension: 4, label: 'WARMTH · FAMILY · HOPE', icon: '🌅',
            mood: 'Safety · Nostalgia · Love',
            colors: ['#2c1810','#6b3a2a','#c07d45','#e8a857','#f5d08a','#fef3c7'],
            names: ['Hearth Dark','Amber Wood','Warm Copper','Golden Hour','Pale Honey','Soft Cream'],
            lighting: 'Golden Hour · Candlelight · Warm Practical Lamps',
            reference: 'Little Miss Sunshine (2006) · Once Upon a Time in Hollywood (2019)',
            director: 'Tim Suhrstedt · Robert Richardson'
        },
        { // Isolation / Melancholy (detected by keywords)
            label: 'ISOLATION · MELANCHOLY', icon: '🌫️',
            mood: 'Loneliness · Distance · Despair',
            colors: ['#0f0f0f','#1a1a2e','#2d3561','#4a5568','#718096','#a0aec0'],
            names: ['Void Black','Midnight Navy','Cold Indigo','Slate Storm','Grey Distance','Silver Mist'],
            lighting: 'Overcast · Desaturated · Flat Light with no warmth',
            reference: 'Lost in Translation (2003) · Her (2013)',
            director: 'Lance Acord · Hoyte van Hoytema'
        }
    ];

    // Classify each scene
    const tensionGroups = {};
    scenes.forEach((scene, idx) => {
        const t = scene.scene_tension_score || 5;
        const header = (scene.scene_header || '').toLowerCase();
        
        let paletteIdx = 1; // Default: drama
        if (t >= 8) paletteIdx = 0;
        else if (t <= 4) paletteIdx = 2;
        else paletteIdx = 1;
        
        // Override with isolation if keywords found
        const isolationKeywords = ['alone','empty','silence','void','dark','night','dream'];
        if (isolationKeywords.some(kw => header.includes(kw)) && t <= 6) paletteIdx = 3;

        if (!tensionGroups[paletteIdx]) tensionGroups[paletteIdx] = [];
        tensionGroups[paletteIdx].push({ idx: idx + 1, header: scene.scene_header, tension: t });
    });

    Object.entries(tensionGroups).forEach(([palIdx, sceneList]) => {
        const palette = MOOD_PALETTES[parseInt(palIdx)];
        if (!palette) return;

        const swatches = palette.colors.map((c, i) => `
            <div class="flex flex-col items-center gap-1.5 group cursor-pointer" title="${palette.names[i]}">
                <div class="w-12 h-12 rounded-xl shadow-lg transition-transform group-hover:scale-110 group-hover:-translate-y-1" style="background:${c}; box-shadow: 0 4px 15px ${c}66;"></div>
                <span class="text-[7px] font-black text-slate-600 uppercase tracking-widest text-center leading-tight group-hover:text-slate-400 transition-colors max-w-[48px]">${palette.names[i]}</span>
            </div>`).join('');

        const sceneChips = sceneList.slice(0, 5).map(s => `
            <span class="text-[8px] font-black px-2 py-0.5 rounded-lg bg-slate-800/80 border border-slate-700/50 text-slate-400 truncate max-w-[120px]">Sc.${s.idx}</span>`).join('');
        const moreScenes = sceneList.length > 5 ? `<span class="text-[8px] font-black text-slate-600">+${sceneList.length-5}</span>` : '';

        grid.insertAdjacentHTML('beforeend', `
            <div class="p-6 rounded-2xl border border-white/5 bg-slate-900/40 hover:bg-slate-900/60 transition-all">
                <div class="flex justify-between items-start mb-5">
                    <div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-lg">${palette.icon}</span>
                            <span class="text-[10px] font-black uppercase tracking-widest text-slate-300">${palette.label}</span>
                        </div>
                        <p class="text-[9px] text-slate-500 uppercase tracking-widest font-bold">${palette.mood}</p>
                    </div>
                    <div class="text-right">
                        <div class="text-2xl font-black text-white">${sceneList.length}</div>
                        <div class="text-[8px] text-slate-600 uppercase font-black tracking-widest">SCENES</div>
                    </div>
                </div>

                <!-- Color Swatches -->
                <div class="flex gap-3 mb-5 overflow-x-auto no-scrollbar pb-1">${swatches}</div>

                <!-- Lighting & References -->
                <div class="space-y-2 mb-4 p-4 rounded-xl bg-black/20 border border-white/5">
                    <div class="text-[8px] font-black uppercase tracking-widest text-slate-500 mb-1">💡 LIGHTING LANGUAGE</div>
                    <p class="text-[10px] text-slate-300 font-medium">${palette.lighting}</p>
                    <div class="pt-2 border-t border-white/5">
                        <div class="text-[8px] font-black text-blue-400/80 uppercase tracking-widest">🎥 ${palette.director}</div>
                        <div class="text-[8px] text-slate-500 mt-0.5 uppercase tracking-widest">${palette.reference}</div>
                    </div>
                </div>

                <!-- Scene Tags -->
                <div class="flex flex-wrap gap-1.5 items-center">
                    <span class="text-[8px] font-black text-slate-600 uppercase tracking-widest mr-1">APPLIES TO:</span>
                    ${sceneChips}${moreScenes}
                </div>
            </div>
        `);
    });
}
function exportToPDF() {
    const btn = document.getElementById('exportPdfBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ GENERATING PDF...';
    btn.disabled = true;

    // Temporarily hide the input section and the button itself
    const inputSection = document.getElementById('inputSection');
    if(inputSection) inputSection.style.display = 'none';
    btn.style.display = 'none';

    // Ensure Timeline is fully expanded for PDF without animations
    const wrapper = document.getElementById('timelineWrapper');
    const overlay = document.getElementById('timelineOverlay');
    const toggleBtn = document.getElementById('toggleTimelineBtn');
    let wasCollapsed = false;
    
    if (wrapper && toggleBtn && !toggleBtn.classList.contains('hidden')) {
        wasCollapsed = wrapper.style.maxHeight === '10rem' || wrapper.style.maxHeight === '';
        if (wasCollapsed) {
            wrapper.style.transition = 'none'; // Disable animation for instant expand
            wrapper.style.maxHeight = 'none';
            if (overlay) overlay.style.display = 'none';
        }
    }

    // Target the main container
    const element = document.querySelector('.max-w-7xl');

    const opt = {
        margin:       [10, 10, 10, 10],
        filename:     'ScriptLens_Cinematic_Report.pdf',
        image:        { type: 'jpeg', quality: 1.0 },
        html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#050505', scrollY: 0 },
        jsPDF:        { unit: 'mm', format: 'a3', orientation: 'landscape' }
    };

    // Wait 150ms for the DOM to reflow the expanded timeline before capturing
    setTimeout(() => {
        html2pdf().set(opt).from(element).save().then(() => {
            // Restore UI
            if(inputSection) inputSection.style.display = '';
            btn.style.display = '';
            btn.innerHTML = originalText;
            btn.disabled = false;
            if (wasCollapsed && wrapper) {
                wrapper.style.maxHeight = '10rem';
                if (overlay) overlay.style.display = '';
                setTimeout(() => wrapper.style.transition = '', 50); // Restore animation after
            }
        }).catch(err => {
            console.error(err);
            alert("PDF Generation Failed: " + err);
            if(inputSection) inputSection.style.display = '';
            btn.style.display = '';
            btn.innerHTML = originalText;
            btn.disabled = false;
            if (wasCollapsed && wrapper) {
                wrapper.style.maxHeight = '10rem';
                if (overlay) overlay.style.display = '';
                setTimeout(() => wrapper.style.transition = '', 50);
            }
        });
    }, 150);
}

function renderDashboard(data) {
    const container = document.getElementById('resultsContainer');
    container.innerHTML = ''; 
    let chartCounts = { WIDE: 0, MEDIUM: 0, "CLOSE UP": 0 }, tensionData = [], timelineHTML = '';
    let totalShots = 0, totalFilmSeconds = 0;
    
    // Character Network Data
    let characterOccurrences = {};
    let characterEdges = {};

    // ---------------------------------------------------------
    // CINEMATIC TIME NORMALIZATION ENGINE
    // ---------------------------------------------------------
    const scriptInput = document.getElementById('scriptInput').value;
    const charCount = scriptInput.length;
    // Standard Hollywood metric: 1500 chars ~ 1 minute (60 seconds)
    const baselineTotalSeconds = (charCount / 1500) * 60;
    
    let totalPacingMultiplier = 0;
    let rawTotalAiSeconds = 0;
    
    data.analysis.forEach(scene => {
        totalPacingMultiplier += (scene.pacing_multiplier || 1.0);
        (scene.shots || []).forEach(shot => {
            rawTotalAiSeconds += (shot.estimated_seconds || 5);
        });
    });
    
    const avgPacing = data.analysis.length > 0 ? totalPacingMultiplier / data.analysis.length : 1.0;
    const targetTotalSeconds = baselineTotalSeconds * avgPacing;
    const normalizationRatio = rawTotalAiSeconds > 0 ? targetTotalSeconds / rawTotalAiSeconds : 1;
    window.normalizationRatio = normalizationRatio;
    // ---------------------------------------------------------

    data.analysis.forEach((scene, sIdx) => {
        tensionData.push(scene?.scene_tension_score || 0);
        let shotsHTML = '';
        
        let sceneDuration = scene.scene_duration_seconds || 0;
        let shotSumSeconds = 0;
        
        // Process Characters for the Network
        let charsInScene = Array.isArray(scene.characters) ? scene.characters : [];
        charsInScene = charsInScene.map(c => typeof c === 'string' ? c.trim().toUpperCase() : '').filter(c => c.length > 1);
        
        charsInScene.forEach(c => {
            characterOccurrences[c] = (characterOccurrences[c] || 0) + 1;
        });
        
        for (let i = 0; i < charsInScene.length; i++) {
            for (let j = i + 1; j < charsInScene.length; j++) {
                let c1 = charsInScene[i];
                let c2 = charsInScene[j];
                // sort to ensure unique edge key
                if (c1 > c2) { let temp = c1; c1 = c2; c2 = temp; }
                let edgeKey = `${c1}::${c2}`;
                characterEdges[edgeKey] = (characterEdges[edgeKey] || 0) + 1;
            }
        }

        let sceneShotsTimelineHTML = '';
        const shotsArray = Array.isArray(scene.shots) ? scene.shots : [];
        shotsArray.forEach((shotObj, i) => {
            totalShots++;
            const rawDuration = shotObj.estimated_seconds || 5;
            // Apply normalization ratio so the sum perfectly matches cinematic theory
            const duration = Math.max(1, Math.round(rawDuration * normalizationRatio));
            
            shotSumSeconds += duration;
            
            // Extract suggestions correctly from new schema
            const primary = shotObj;
            const alts = Array.isArray(shotObj.alternatives) ? shotObj.alternatives : [];
            const type = (primary.shot_type || "MEDIUM").toUpperCase();
            
            const colorClass = type.includes("WIDE") ? "emerald" : type.includes("CLOSE") ? "orange" : "blue";
            
            // Lens Mapping System
            const getLens = (shotType) => {
                if(shotType.includes("WIDE")) return "14mm-24mm";
                if(shotType.includes("CLOSE")) return "85mm-100mm";
                return "35mm-50mm";
            };
            const lens = getLens(type);
            
            if (type.includes("WIDE")) chartCounts.WIDE++;
            else if (type.includes("CLOSE")) chartCounts["CLOSE UP"]++;
            else chartCounts.MEDIUM++;

            sceneShotsTimelineHTML += `<div title="Shot ${totalShots}: ${type} (${duration}s)" class="shot-block bg-${colorClass}-500 h-8 rounded-[4px] shadow-sm flex-shrink-0 hover:scale-[1.3] hover:-translate-y-1 hover:z-10 transition-transform origin-bottom cursor-pointer relative group" style="min-width: ${Math.max(duration * 3, 4)}px"></div>`;

            shotsHTML += generateShotCardHTML(sIdx, i, totalShots);
        });

        if (!sceneShotsTimelineHTML) {
            // Fallback for scenes with no explicit shots to ensure they are counted and visible
            sceneShotsTimelineHTML = `<div title="Empty Scene (No Shots AI generated)" class="shot-block bg-slate-500 h-8 rounded-[4px] shadow-sm flex-shrink-0 hover:scale-[1.3] hover:-translate-y-1 hover:z-10 transition-transform origin-bottom cursor-pointer relative group" style="min-width: 10px"></div>`;
        }
        
        timelineHTML += `
            <div class="flex flex-col gap-2 items-start cursor-pointer hover:bg-slate-800/80 hover:shadow-lg p-3 rounded-2xl transition-all flex-shrink-0 group border border-transparent hover:border-slate-700/50" onclick="document.getElementById('scene-block-${sIdx}').scrollIntoView({behavior: 'smooth'})" title="Go to ${scene.scene_header}">
                <div class="text-[10px] font-black text-slate-500 group-hover:text-blue-400 uppercase tracking-[0.2em] px-1 transition-colors">Scene ${sIdx + 1}</div>
                <div class="flex gap-[2px] flex-wrap max-w-[200px] sm:max-w-[300px] md:max-w-[400px]">
                    ${sceneShotsTimelineHTML}
                </div>
            </div>
        `;

        const pm = scene.pacing_multiplier || 1.0;
        const pacingBadge = pm < 0.9 ? '<span class="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-[9px] font-black border border-red-500/30 tracking-widest uppercase">Fast Pace</span>' 
                            : pm > 1.5 ? '<span class="bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded text-[9px] font-black border border-purple-500/30 tracking-widest uppercase">Slow Pace</span>'
                            : '<span class="bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded text-[9px] font-black border border-slate-500/30 tracking-widest uppercase">Normal Pace</span>';

        container.insertAdjacentHTML('beforeend', `
            <div id="scene-block-${sIdx}" class="glass-card p-10 rounded-[4rem] mb-12 border border-white/5 shadow-2xl scroll-mt-8">
                <div class="grid grid-cols-1 lg:grid-cols-4 gap-12 mb-6">
                    <div class="space-y-6">
                        <div class="flex gap-2 items-center flex-wrap">
                            <div class="inline-block px-4 py-1 bg-blue-500/10 rounded-full border border-blue-500/20 text-[10px] font-black text-blue-400 uppercase tracking-widest">Scene ${sIdx + 1}</div>
                            ${pacingBadge}
                        </div>
                        <div class="mt-2 flex items-center gap-3 bg-black/20 p-2 rounded-lg border border-white/5 inline-flex">
                            <span class="text-[9px] font-black text-slate-500 uppercase tracking-widest">Director Pacing Override:</span>
                            <input type="range" min="0.3" max="4.0" step="0.1" value="${pm}" 
                                   oninput="document.getElementById('pacingVal-${sIdx}').innerText = this.value + 'x'"
                                   onchange="updateScenePacing(${sIdx}, this.value)" 
                                   class="w-24 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer">
                            <span id="pacingVal-${sIdx}" class="text-[10px] font-mono text-blue-400 font-bold w-6">${pm}x</span>
                        </div>
                        <h3 class="text-3xl font-black text-white leading-none tracking-tighter">${scene.scene_header}</h3>
                        <p class="text-xs text-blue-400 font-bold uppercase tracking-widest">${(scene.characters || []).join(' • ')}</p>
                        <div class=\"pt-4 border-t border-slate-700/50\">
                            <p class=\"text-[10px] text-slate-400 uppercase tracking-widest font-black mb-1\">Estimated Duration</p>
                            <p id=\"sceneDurLabel-${sIdx}\" class=\"text-xl font-mono text-white font-black\">${Math.floor((scene.scene_duration_seconds || 0)/60)}m ${(scene.scene_duration_seconds || 0)%60}s</p>
                        </div>
                    </div>
                    <div class="lg:col-span-3 relative">
                        <div id="sceneShotsWrapper-${sIdx}" class="relative max-h-[30rem] overflow-hidden transition-[max-height] duration-700 ease-in-out">
                            ${shotsHTML}
                            <div id="sceneShotsOverlay-${sIdx}" class="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-[#111118] to-transparent pointer-events-none hidden"></div>
                        </div>
                        <div class="flex justify-center mt-6">
                            <button id="toggleSceneBtn-${sIdx}" onclick="toggleSection('sceneShotsWrapper-${sIdx}', 'sceneShotsOverlay-${sIdx}', 'toggleSceneText-${sIdx}', 'sceneChevron-${sIdx}', 'Expand Shots', 'Collapse Shots', '30rem')" class="hidden flex items-center gap-2 text-slate-400 hover:text-white transition-colors bg-slate-800/80 hover:bg-slate-700 px-6 py-2 rounded-full text-[10px] font-black uppercase tracking-widest border border-white/5 shadow-lg">
                                <span id="toggleSceneText-${sIdx}">Expand Shots</span>
                                <svg id="sceneChevron-${sIdx}" class="w-4 h-4 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>`);
            
        // If AI didn't provide scene duration, fallback to sum of shots
        if (sceneDuration === 0) sceneDuration = shotSumSeconds;
        totalFilmSeconds += sceneDuration;
    });

    let totalScenePacing = 0;
    let validScenesCount = 0;
    data.analysis.forEach(scene => {
        const sceneShots = (scene.shots || []).length;
        const sceneDur = scene.scene_duration_seconds || 0;
        if (sceneDur > 0 && sceneShots > 0) {
            totalScenePacing += sceneShots / (sceneDur / 60);
            validScenesCount++;
        }
    });
    const pacingValue = validScenesCount > 0 ? parseFloat((totalScenePacing / validScenesCount).toFixed(1)) : 0;
    document.getElementById('pacingText').innerText = pacingValue;
    
    // Dynamic color and Interpretation for pacing bar based on intensity
    let pacingColor = "bg-blue-500";
    let pacingTextValue = "Moderate Rhythm";
    let textColor = "text-blue-400";
    
    if (pacingValue > 15) {
        pacingColor = "bg-red-500";
        pacingTextValue = "Frenetic / Fast-Paced (Action/Thriller)";
        textColor = "text-red-400";
    } else if (pacingValue > 10) {
        pacingColor = "bg-orange-500";
        pacingTextValue = "Brisk / Energetic Rhythm";
        textColor = "text-orange-400";
    } else if (pacingValue < 5) {
        pacingColor = "bg-emerald-500";
        pacingTextValue = "Deliberate / Slow-Burn (Drama)";
        textColor = "text-emerald-400";
    }
    
    const interpretationEl = document.getElementById('pacingInterpretation');
    interpretationEl.innerText = pacingTextValue;
    interpretationEl.className = `text-[10px] font-black uppercase mt-4 tracking-widest ${textColor}`;
    
    const pacingBar = document.getElementById('pacingBar');
    pacingBar.className = `${pacingColor} h-full transition-all duration-1000 shadow-[0_0_15px_rgba(0,0,0,0.5)]`;
    // Max visual bar width mapping
    pacingBar.style.width = `${Math.min(pacingValue * 4, 100)}%`;
    pacingBar.style.boxShadow = `0 0 10px var(--tw-ring-color, currentColor)`; // Add glow

    document.getElementById('visualRhythmTimeline').innerHTML = timelineHTML;
    document.getElementById('timelineStats').innerText = `${data.analysis.length} SCENES • ${totalShots} SHOTS`;

    const rangeText = data.estimated_runtime_range ? `EST: ${data.estimated_runtime_range}` : 'Calculating...';
    document.getElementById('totalDurationText').innerHTML = `${rangeText} <span class="text-lg text-slate-500 ml-2">(${formatTime(totalFilmSeconds)})</span>`;
    
    // Runtime Breakdown
    const breakdownEl = document.getElementById('runtimeBreakdown');
    if (data.runtime_breakdown && breakdownEl) {
        breakdownEl.classList.remove('hidden');
        document.getElementById('bdDialogue').innerText = data.runtime_breakdown.dialogue_minutes + 'm';
        document.getElementById('bdAction').innerText = data.runtime_breakdown.action_minutes + 'm';
        document.getElementById('bdOverhead').innerText = data.runtime_breakdown.overhead_minutes + 'm';
    } else if (breakdownEl) {
        breakdownEl.classList.add('hidden');
    }


    updateCharts(chartCounts, tensionData);
    renderCharacterNetwork(characterOccurrences, characterEdges);
    renderShootingSchedule(data.analysis, data.metrics);
    renderMoodBoard(data.analysis, data.metrics);
    
    // Integrity & Confidence Rendering
    const integritySection = document.getElementById('integritySection');
    if (data.confidence_score !== undefined) {
        integritySection.classList.remove('hidden');
        
        // Circular Progress for Confidence
        const circle = document.getElementById('confidenceCircle');
        const text = document.getElementById('confidenceText');
        const score = data.confidence_score;
        
        // 351.8 is the circumference (2 * pi * 56)
        const offset = 351.8 - (score / 100) * 351.8;
        circle.style.strokeDashoffset = offset;
        text.innerText = `${score}%`;
        
        // Color based on score
        circle.classList.remove('text-emerald-500', 'text-amber-500', 'text-red-500');
        if (score >= 80) circle.classList.add('text-emerald-500');
        else if (score >= 50) circle.classList.add('text-amber-500');
        else circle.classList.add('text-red-500');
        
        // Logic Conflicts
        const conflictsContainer = document.getElementById('logicConflictsContainer');
        conflictsContainer.innerHTML = '';
        if (data.logic_conflicts && data.logic_conflicts.length > 0) {
            data.logic_conflicts.forEach(conflict => {
                conflictsContainer.innerHTML += `
                    <div class="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex gap-3 items-start">
                        <span class="text-red-500 mt-0.5">⚠️</span>
                        <div>
                            <p class="text-red-400 font-black text-[10px] uppercase tracking-widest">${conflict.type}</p>
                            <p class="text-slate-300 text-xs mt-1 leading-relaxed">${conflict.message}</p>
                        </div>
                    </div>
                `;
            });
        } else {
            conflictsContainer.innerHTML = `
                <div class="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex gap-3 items-start">
                    <span class="text-emerald-500 mt-0.5">✅</span>
                    <div>
                        <p class="text-emerald-400 font-black text-[10px] uppercase tracking-widest">No Logic Conflicts Detected</p>
                        <p class="text-slate-300 text-xs mt-1 leading-relaxed">The visual rhythm and scene durations are mathematically sound and align with genre expectations.</p>
                    </div>
                </div>
            `;
        }
        
        // ASL Metrics
        const metricsContainer = document.getElementById('aslMetricsContainer');
        if (data.metrics) {
            metricsContainer.innerHTML = `
                <span>Total Shots: <span class="text-white">${data.metrics.total_shots}</span></span>
                <span>•</span>
                <span>Computed ASL: <span class="text-white">${data.metrics.computed_asl}s</span></span>
                <span>•</span>
                <span>Expected ASL: <span class="text-white">${data.metrics.expected_asl}s</span></span>
            `;
        }
    } else {
        integritySection.classList.add('hidden');
    }
    
    // Helper to check and enable toggle buttons for elements that overflow their default max-height
    setTimeout(() => {
        const sectionsToCheck = [
            { wrapper: 'timelineWrapper', btn: 'toggleTimelineBtn', overlay: 'timelineOverlay', threshold: 160 }, // 10rem
            { wrapper: 'networkWrapper', btn: 'toggleNetworkBtn', overlay: 'networkOverlay', threshold: 400 }, // 25rem
            { wrapper: 'scheduleWrapper', btn: 'toggleScheduleBtn', overlay: 'scheduleOverlay', threshold: 320 }, // 20rem
            { wrapper: 'moodWrapper', btn: 'toggleMoodBtn', overlay: 'moodOverlay', threshold: 320 } // 20rem
        ];
        
        // Add dynamic scene blocks
        data.analysis.forEach((_, sIdx) => {
            sectionsToCheck.push({
                wrapper: `sceneShotsWrapper-${sIdx}`,
                btn: `toggleSceneBtn-${sIdx}`,
                overlay: `sceneShotsOverlay-${sIdx}`,
                threshold: 480 // 30rem
            });
        });

        sectionsToCheck.forEach(sec => {
            const wrapperEl = document.getElementById(sec.wrapper);
            const btnEl = document.getElementById(sec.btn);
            const overlayEl = document.getElementById(sec.overlay);
            
            if (wrapperEl && btnEl && overlayEl) {
                if (wrapperEl.scrollHeight > sec.threshold) {
                    btnEl.classList.remove('hidden');
                    overlayEl.classList.remove('hidden');
                } else {
                    btnEl.classList.add('hidden');
                    overlayEl.classList.add('hidden');
                }
            }
        });
    }, 200);
}

window.toggleSection = function(wrapperId, overlayId, textId, chevronId, expandText, collapseText, collapsedHeight) {
    const wrapper = document.getElementById(wrapperId);
    const chevron = document.getElementById(chevronId);
    const text = document.getElementById(textId);
    const overlay = document.getElementById(overlayId);
    
    if (wrapper.style.maxHeight === collapsedHeight || wrapper.style.maxHeight === '') {
        wrapper.style.maxHeight = wrapper.scrollHeight + 'px'; // Expand fully
        chevron.style.transform = 'rotate(180deg)';
        text.innerText = collapseText;
        overlay.style.opacity = '0';
        setTimeout(() => overlay.style.display = 'none', 300);
    } else {
        wrapper.style.maxHeight = collapsedHeight;
        chevron.style.transform = 'rotate(0deg)';
        text.innerText = expandText;
        overlay.style.display = '';
        setTimeout(() => overlay.style.opacity = '1', 10);
    }
};

function renderCharacterNetwork(occurrences, edges) {
    const nodes = [];
    const edgesList = [];
    
    // Find main character for styling
    const maxOccur = Math.max(...Object.values(occurrences), 1);

    Object.keys(occurrences).forEach((charName) => {
        const isMain = occurrences[charName] === maxOccur;
        nodes.push({
            id: charName,
            label: charName,
            value: occurrences[charName], // Size depends on occurrences
            color: isMain ? {
                background: 'rgba(245, 158, 11, 0.9)', 
                border: '#fcd34d',
                highlight: { background: '#d97706', border: '#fde68a' },
                hover: { background: '#b45309', border: '#fef3c7' }
            } : { 
                background: 'rgba(139, 92, 246, 0.8)', 
                border: '#a78bfa',
                highlight: { background: '#8b5cf6', border: '#c4b5fd' },
                hover: { background: '#7c3aed', border: '#ddd6fe' }
            },
            font: { color: '#ffffff', size: 14, face: 'Inter', strokeWidth: 3, strokeColor: '#0f172a' },
            shadow: { enabled: true, color: isMain ? 'rgba(245, 158, 11, 0.6)' : 'rgba(139, 92, 246, 0.4)', size: 15, x: 0, y: 0 }
        });
    });

    Object.keys(edges).forEach(edgeKey => {
        const [c1, c2] = edgeKey.split('::');
        edgesList.push({
            from: c1,
            to: c2,
            value: edges[edgeKey], // Thickness depends on interactions
            color: { color: 'rgba(148, 163, 184, 0.4)', highlight: '#cbd5e1', hover: '#cbd5e1' },
            smooth: { type: 'continuous' }
        });
    });

    const container = document.getElementById('characterNetwork');
    const data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edgesList) };
    const options = {
        nodes: { 
            shape: 'dot', 
            scaling: { min: 20, max: 50, label: { enabled: true, min: 14, max: 24 } }
        },
        interaction: { hover: true, tooltipDelay: 200, zoomView: true, dragView: true },
        physics: {
            solver: 'repulsion',
            repulsion: {
                centralGravity: 0.1,
                springLength: 250,
                springConstant: 0.05,
                nodeDistance: 200,
                damping: 0.09
            },
            stabilization: { enabled: true, iterations: 150 }
        }
    };
    const network = new vis.Network(container, data, options);
    
    // Stop nodes from moving endlessly after initial layout
    network.on("stabilizationIterationsDone", function () {
        network.setOptions( { physics: false } );
    });
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
    
    // Calculate 3-Act Structure points
    const numScenes = d.length;
    const act1End = Math.floor(numScenes * 0.25);
    const act2End = Math.floor(numScenes * 0.75);
    
    const labels = d.map((_, i) => {
        if (i === 0) return "ACT I (Setup)";
        if (i === act1End) return "ACT II (Confrontation)";
        if (i === act2End) return "ACT III (Resolution)";
        return `Sc ${i+1}`;
    });

    const gradient = ctx2.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(245, 158, 11, 0.4)');
    gradient.addColorStop(1, 'rgba(245, 158, 11, 0.0)');

    storyArcChart = new Chart(ctx2, {
        type: 'line',
        data: { 
            labels: labels, 
            datasets: [{ 
                label: 'Narrative Tension', 
                data: d, 
                borderColor: '#f59e0b', 
                tension: 0.4, 
                fill: true, 
                backgroundColor: gradient,
                pointBackgroundColor: '#0f172a',
                pointBorderColor: '#f59e0b',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }] 
        },
        options: { 
            ...chartOptions, 
            scales: { 
                y: { min: 0, max: 10, ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }, 
                x: { ticks: { color: '#94a3b8', font: { weight: 'bold' } }, grid: { color: 'rgba(255,255,255,0.05)' } } 
            } 
        }
    });
}

function swapAlternative(sceneIdx, shotIdx, altIdx) {
    if(!window.currentAnalysisData) return;
    
    const scene = window.currentAnalysisData.analysis[sceneIdx];
    const shot = scene.shots[shotIdx];
    
    if (shot.isLocked) {
        alert("This shot is locked by the director. Unlock it to swap alternatives.");
        return;
    }
    
    if(!shot.alternatives || shot.alternatives.length <= altIdx) return;
    
    const currentPrimary = JSON.parse(JSON.stringify(shot));
    delete currentPrimary.alternatives;
    currentPrimary.percentage = currentPrimary.primary_percentage || 50;
    
    const selectedAlt = shot.alternatives[altIdx];
    
    shot.shot_type = selectedAlt.shot_type;
    shot.angle = selectedAlt.angle;
    shot.movement = selectedAlt.movement;
    shot.primary_percentage = selectedAlt.percentage;
    shot.cinematic_reasoning = selectedAlt.cinematic_reasoning || shot.cinematic_reasoning;
    shot.director_reference = selectedAlt.director_reference || shot.director_reference;
    shot.movie_reference = selectedAlt.movie_reference || shot.movie_reference;
    
    shot.alternatives[altIdx] = currentPrimary;
    
    // Partial Re-render instead of full dashboard
    const cardDiv = document.getElementById(`shotCard-${sceneIdx}-${shotIdx}`);
    if (cardDiv) {
        const globalShotIndex = cardDiv.getAttribute('data-globalidx') || "X";
        cardDiv.outerHTML = generateShotCardHTML(sceneIdx, shotIdx, globalShotIndex);
    }
}

function lockShot(btnElement, sceneIdx, shotIdx) {
    const shot = window.currentAnalysisData.analysis[sceneIdx].shots[shotIdx];
    shot.isLocked = !shot.isLocked;
    
    if(shot.isLocked) {
        btnElement.classList.remove('text-slate-500');
        btnElement.classList.add('text-amber-400');
        btnElement.innerText = '🔐';
    } else {
        btnElement.classList.remove('text-amber-400');
        btnElement.classList.add('text-slate-500');
        btnElement.innerText = '🔒';
    }
}



function generateShotCardHTML(sceneIdx, shotIdx, globalShotIndex) {
    const scene = window.currentAnalysisData.analysis[sceneIdx];
    const shotObj = scene.shots[shotIdx];
    const rawDuration = shotObj.estimated_seconds || 5;
    const duration = Math.max(1, Math.round(rawDuration * window.normalizationRatio));
    
    const primary = shotObj;
    const alts = Array.isArray(shotObj.alternatives) ? shotObj.alternatives : [];
    const type = (primary.shot_type || "MEDIUM").toUpperCase();
    
    const colorClass = type.includes("WIDE") ? "emerald" : type.includes("CLOSE") ? "orange" : "blue";
    
    const getLens = (shotType) => {
        if(shotType.includes("WIDE")) return "14mm-24mm";
        if(shotType.includes("CLOSE")) return "85mm-100mm";
        return "35mm-50mm";
    };
    const lens = getLens(type);
    
    const primaryPercent = primary.primary_percentage ? `<span class="bg-${colorClass}-500/10 text-${colorClass}-400 px-2 py-0.5 rounded ml-3 border border-${colorClass}-500/30 font-mono tracking-wider" title="Algorithmic Confidence Match for this Genre">${primary.primary_percentage}% ML CONFIDENCE</span>` : '';
    
    let alternativesHTML = '';
    if (alts.length > 0) {
        let altList = alts.map((alt, altIdx) => {
            const altType = (alt.shot_type || "MEDIUM").toUpperCase();
            const altColor = altType.includes("WIDE") ? "emerald" : altType.includes("CLOSE") ? "orange" : "blue";
            const altLens = getLens(altType);
            
            return `
            <div onclick="swapAlternative(${sceneIdx}, ${shotIdx}, ${altIdx})" class="bg-slate-800/80 p-5 rounded-[1.5rem] border-l-4 border-${altColor}-500 shadow-md flex flex-col justify-between cursor-pointer hover:scale-[1.02] hover:bg-slate-700/80 transition-all group">
                <div>
                    <div class="flex justify-between items-start mb-3">
                        <div>
                            <span class="text-[9px] font-black uppercase tracking-[0.2em] text-${altColor}-400 flex items-center mb-2 group-hover:text-white transition-colors">Alt ${altIdx + 1} • ${altType} <span class="bg-slate-700/50 text-slate-300 px-1.5 py-0.5 rounded ml-2 border border-slate-600 font-mono" title="Machine Learning Probability Score">${alt.percentage || 0}% PROBABILITY</span></span>
                            <div class="flex gap-2 flex-wrap">
                                <span class="badge-tag badge-angle text-[8px] px-2 py-0.5">🎥 ${alt.angle || 'Standard'}</span>
                                <span class="badge-tag badge-movement text-[8px] px-2 py-0.5">🎬 ${alt.movement || 'Static'}</span>
                                <span class="badge-tag text-[8px] px-2 py-0.5 bg-slate-800 text-slate-300 border border-slate-600">👁️ ${altLens}</span>
                            </div>
                        </div>
                        <button class="text-slate-500 group-hover:text-blue-400 hover:scale-110 transition-all bg-slate-800 p-2 rounded-full border border-slate-700/50" title="Swap this direction to Primary">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
                        </button>
                    </div>
                    <p class="text-slate-300 text-xs leading-relaxed mb-3 font-medium italic border-l-2 border-slate-600 pl-3 py-0.5">"${alt.cinematic_reasoning || ''}"</p>
                </div>
                <div class="pt-3 border-t border-white/5 text-[7px] font-black text-blue-400/80 uppercase tracking-widest mt-auto">
                    🎥 REF: ${alt.director_reference || 'N/A'}
                </div>
            </div>
            `;
        }).join('');
        
        alternativesHTML = `
        <div class="mt-6 pt-5 border-t border-slate-700/50">
            <div class="text-[10px] font-black uppercase text-slate-500 mb-4 tracking-widest flex items-center gap-2">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                Alternative Directions (Click to Swap)
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                ${altList}
            </div>
        </div>
        `;
    }
    
    const lockBtnClass = shotObj.isLocked ? "text-amber-400" : "text-slate-500";
    const lockBtnIcon = shotObj.isLocked ? "🔐" : "🔒";

    return `
        <div class="bg-slate-900/60 p-6 rounded-[2.5rem] border-l-8 border-${colorClass}-500 mb-6 shadow-2xl relative shot-card" id="shotCard-${sceneIdx}-${shotIdx}" data-globalidx="${globalShotIndex}">
            <div class="flex justify-between items-start mb-4">
                <div>
                    <div class="text-[11px] font-black uppercase tracking-[0.2em] text-${colorClass}-400 flex items-center">Shot ${globalShotIndex} • ${type} ${primaryPercent}</div>
                    <div class="flex gap-2 mt-3">
                        <span class="badge-tag badge-angle">🎥 ANGLE: ${primary.angle || 'Eye Level'}</span>
                        <span class="badge-tag badge-movement">🎬 MOVE: ${primary.movement || 'Static'}</span>
                        <span class="badge-tag text-[8px] px-2 py-0.5 bg-slate-800 text-slate-300 border border-slate-600">👁️ LENS: ${lens}</span>
                    </div>
                </div>
                <div class=\"flex gap-3 items-center\">
                    <div class=\"flex items-center gap-2 bg-black/40 px-3 py-1 rounded-full border border-white/5 mr-2\">
                         <span class=\"text-[8px] font-black text-slate-500 uppercase tracking-widest\">Pace:</span>
                         <input type=\"range\" min=\"0.3\" max=\"4.0\" step=\"0.1\" value=\"${shotObj.pacing_multiplier || 1.0}\" 
                                oninput=\"this.nextElementSibling.innerText = this.value + 'x'\"
                                onchange=\"updateShotPacing(${sceneIdx}, ${shotIdx}, this.value)\" 
                                class=\"w-16 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer\">
                         <span class=\"text-[9px] font-mono text-blue-400 font-bold w-6\">${shotObj.pacing_multiplier || 1.0}x</span>
                    </div>
                    <button onclick=\"lockShot(this, ${sceneIdx}, ${shotIdx})\" class=\"${lockBtnClass} hover:text-amber-400 transition-colors\" title=\"Director's Lock\">${lockBtnIcon}</button>
                    <span id=\"shotDur-${sceneIdx}-${shotIdx}\" class=\"text-xs font-mono text-slate-400 font-black bg-slate-800 px-3 py-1 rounded-lg\">${duration}S</span>
                </div>
            </div>
            <p class=\"text-slate-200 text-sm leading-relaxed mb-4 font-medium italic border-l-2 border-slate-700 pl-4 py-1\">\"${primary.cinematic_reasoning || ''}\"</p>
            <div class=\"pt-4 border-t border-white/5 text-[9px] font-black text-blue-400 uppercase tracking-widest\">
                🎥 REF: ${primary.director_reference || ''} • ${primary.movie_reference || ''}
            </div>
            ${alternativesHTML}
        </div>`;
}




function updateScenePacing(sceneIdx, newPacing) {
    if(!window.currentAnalysisData) return;
    const scene = window.currentAnalysisData.analysis[sceneIdx];
    const oldPacing = scene.pacing_multiplier || 1.0;
    scene.pacing_multiplier = parseFloat(newPacing);
    
    // Approximate new duration (only action changes, but we scale overall for instant feedback)
    const ratio = scene.pacing_multiplier / oldPacing;
    scene.scene_duration_seconds = Math.max(5, Math.round((scene.scene_duration_seconds || 0) * ratio));
    
    // Capture state of expanded scenes before re-rendering
    const expandedScenes = [];
    window.currentAnalysisData.analysis.forEach((_, idx) => {
        const wrapper = document.getElementById(`sceneShotsWrapper-${idx}`);
        if (wrapper && (wrapper.style.maxHeight !== '30rem' && wrapper.style.maxHeight !== '')) {
            expandedScenes.push(idx);
        }
    });

    renderDashboard(window.currentAnalysisData);
    
    // Restore expanded state
    setTimeout(() => {
        expandedScenes.forEach(idx => {
            const wrapper = document.getElementById(`sceneShotsWrapper-${idx}`);
            const chevron = document.getElementById(`sceneChevron-${idx}`);
            const text = document.getElementById(`toggleSceneText-${idx}`);
            const overlay = document.getElementById(`sceneShotsOverlay-${idx}`);
            
            if (wrapper && chevron && text && overlay) {
                wrapper.style.maxHeight = wrapper.scrollHeight + 'px';
                wrapper.style.transition = 'none'; // Snap open immediately
                chevron.style.transform = 'rotate(180deg)';
                text.innerText = 'Collapse Shots';
                overlay.style.opacity = '0';
                overlay.style.display = 'none';
                
                setTimeout(() => { wrapper.style.transition = 'max-height 700ms ease-in-out'; }, 50);
            }
        });
    }, 10);
}
