import re

with open("frontend/script.js", "r") as f:
    content = f.read()

# 1. Bug F1: numChunks / 5 -> numChunks
content = re.sub(
    r"const numRounds = Math.ceil\(numChunks / 5\); // Semaphore\(5\) on backend",
    r"const numRounds = numChunks; // Sequential processing",
    content
)

# 2. Add window.normalizationRatio globally
content = re.sub(
    r"let shotChart = null, storyArcChart = null;",
    r"let shotChart = null, storyArcChart = null;\nwindow.currentAnalysisData = null;\nwindow.normalizationRatio = 1.0;\n",
    content
)

# 3. Store normalizationRatio
content = re.sub(
    r"const normalizationRatio = rawTotalAiSeconds > 0 \? targetTotalSeconds / rawTotalAiSeconds : 1;",
    r"const normalizationRatio = rawTotalAiSeconds > 0 ? targetTotalSeconds / rawTotalAiSeconds : 1;\n    window.normalizationRatio = normalizationRatio;",
    content
)

# 4. Runtime Breakdown
content = re.sub(
    r"document\.getElementById\('totalDurationText'\)\.innerHTML = `\$\{rangeText\} <span class=\"text-lg text-slate-500 ml-2\">\(\$\{formatTime\(totalFilmSeconds\)\}\)</span>`;",
    r"""document.getElementById('totalDurationText').innerHTML = `${rangeText} <span class="text-lg text-slate-500 ml-2">(${formatTime(totalFilmSeconds)})</span>`;
    
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
""",
    content
)

# 5. Extract generateShotCardHTML and modify render loop
shot_generation_logic = """
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
                <div class="flex gap-3 items-center">
                    <button onclick="lockShot(this, ${sceneIdx}, ${shotIdx})" class="${lockBtnClass} hover:text-amber-400 transition-colors" title="Director's Lock">${lockBtnIcon}</button>
                    <span class="text-xs font-mono text-slate-400 font-black bg-slate-800 px-3 py-1 rounded-lg">${duration}S</span>
                </div>
            </div>
            <p class="text-slate-200 text-sm leading-relaxed mb-4 font-medium italic border-l-2 border-slate-700 pl-4 py-1">"${primary.cinematic_reasoning || ''}"</p>
            <div class="pt-4 border-t border-white/5 text-[9px] font-black text-blue-400 uppercase tracking-widest">
                🎥 REF: ${primary.director_reference || ''} • ${primary.movie_reference || ''}
            </div>
            ${alternativesHTML}
        </div>`;
}

"""

# Replace the giant shotsHTML generation inside renderDashboard
search_block = """            const primaryPercent = primary.primary_percentage ? `<span class="bg-${colorClass}-500/10 text-${colorClass}-400 px-2 py-0.5 rounded ml-3 border border-${colorClass}-500/30 font-mono tracking-wider" title="Algorithmic Confidence Match for this Genre">${primary.primary_percentage}% ML CONFIDENCE</span>` : '';
            
            let alternativesHTML = '';
            // Render alternatives as interactive cards
            if (alts.length > 0) {
                let altList = alts.map((alt, altIdx) => {
                    const altType = (alt.shot_type || "MEDIUM").toUpperCase();
                    const altColor = altType.includes("WIDE") ? "emerald" : altType.includes("CLOSE") ? "orange" : "blue";
                    const altLens = getLens(altType);
                    
                    // JSON serialize to escape quotes properly for onclick
                    return `
                    <div onclick="swapAlternative(${sIdx}, ${i}, ${altIdx})" class="bg-slate-800/80 p-5 rounded-[1.5rem] border-l-4 border-${altColor}-500 shadow-md flex flex-col justify-between cursor-pointer hover:scale-[1.02] hover:bg-slate-700/80 transition-all group">
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
            shotsHTML += `
                <div class="bg-slate-900/60 p-6 rounded-[2.5rem] border-l-8 border-${colorClass}-500 mb-6 shadow-2xl relative">
                    <div class="flex justify-between items-start mb-4">
                        <div>
                            <div class="text-[11px] font-black uppercase tracking-[0.2em] text-${colorClass}-400 flex items-center">Shot ${totalShots} • ${type} ${primaryPercent}</div>
                            <div class="flex gap-2 mt-3">
                                <span class="badge-tag badge-angle">🎥 ANGLE: ${primary.angle || 'Eye Level'}</span>
                                <span class="badge-tag badge-movement">🎬 MOVE: ${primary.movement || 'Static'}</span>
                                <span class="badge-tag text-[8px] px-2 py-0.5 bg-slate-800 text-slate-300 border border-slate-600">👁️ LENS: ${lens}</span>
                            </div>
                        </div>
                        <div class="flex gap-3 items-center">
                            <button onclick="lockShot(this)" class="text-slate-500 hover:text-amber-400 transition-colors" title="Director's Lock">🔒</button>
                            <span class="text-xs font-mono text-slate-400 font-black bg-slate-800 px-3 py-1 rounded-lg">${duration}S</span>
                        </div>
                    </div>
                    <p class="text-slate-200 text-sm leading-relaxed mb-4 font-medium italic border-l-2 border-slate-700 pl-4 py-1">"${primary.cinematic_reasoning || ''}"</p>
                    <div class="pt-4 border-t border-white/5 text-[9px] font-black text-blue-400 uppercase tracking-widest">
                        🎥 REF: ${primary.director_reference || ''} • ${primary.movie_reference || ''}
                    </div>
                    ${alternativesHTML}
                </div>`;"""

replace_block = """            shotsHTML += generateShotCardHTML(sIdx, i, totalShots);"""

content = content.replace(search_block, replace_block)
content = content + "\n\n" + shot_generation_logic

# 6. Rewrite swapAlternative
swap_old = """function swapAlternative(sceneIdx, shotIdx, altIdx) {
    if(!window.currentAnalysisData) return;
    
    const scene = window.currentAnalysisData.analysis[sceneIdx];
    const shot = scene.shots[shotIdx];
    
    if(!shot.alternatives || shot.alternatives.length <= altIdx) return;
    
    // Deep clone to swap
    const currentPrimary = JSON.parse(JSON.stringify(shot));
    delete currentPrimary.alternatives; // Remove alternatives from the clone to avoid nesting
    currentPrimary.percentage = currentPrimary.primary_percentage || 50; // Ensure it has a percentage for the alt array
    
    const selectedAlt = shot.alternatives[altIdx];
    
    // Move alt properties to primary
    shot.shot_type = selectedAlt.shot_type;
    shot.angle = selectedAlt.angle;
    shot.movement = selectedAlt.movement;
    shot.primary_percentage = selectedAlt.percentage;
    shot.cinematic_reasoning = selectedAlt.cinematic_reasoning || shot.cinematic_reasoning;
    shot.director_reference = selectedAlt.director_reference || shot.director_reference;
    shot.movie_reference = selectedAlt.movie_reference || shot.movie_reference;
    
    // Move old primary into the alternatives array
    shot.alternatives[altIdx] = currentPrimary;
    
    // Capture state of expanded scenes before re-rendering
    const expandedScenes = [];
    window.currentAnalysisData.analysis.forEach((_, idx) => {
        const wrapper = document.getElementById(`sceneShotsWrapper-${idx}`);
        if (wrapper && (wrapper.style.maxHeight !== '30rem' && wrapper.style.maxHeight !== '')) {
            expandedScenes.push(idx);
        }
    });

    // Re-render dashboard
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
                
                // Re-enable transition after snap
                setTimeout(() => { wrapper.style.transition = 'max-height 700ms ease-in-out'; }, 50);
            }
        });
    }, 10); // Short delay to allow DOM to settle
}"""

swap_new = """function swapAlternative(sceneIdx, shotIdx, altIdx) {
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
}"""

content = content.replace(swap_old, swap_new)

# 7. Rewrite lockShot
lock_old = """function lockShot(btnElement) {
    if(btnElement.classList.contains('text-amber-400')) {
        btnElement.classList.remove('text-amber-400');
        btnElement.classList.add('text-slate-500');
        btnElement.innerText = '🔒';
    } else {
        btnElement.classList.remove('text-slate-500');
        btnElement.classList.add('text-amber-400');
        btnElement.innerText = '🔐';
    }
}"""

lock_new = """function lockShot(btnElement, sceneIdx, shotIdx) {
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
}"""

content = content.replace(lock_old, lock_new)


with open("frontend/script.js", "w") as f:
    f.write(content)

print("Updated script.js successfully")
