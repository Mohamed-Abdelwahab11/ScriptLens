import re

with open("frontend/script.js", "r") as f:
    content = f.read()

# 1. Add pacing slider UI
search = """                        <div class="flex gap-2 items-center flex-wrap">
                            <div class="inline-block px-4 py-1 bg-blue-500/10 rounded-full border border-blue-500/20 text-[10px] font-black text-blue-400 uppercase tracking-widest">Scene ${sIdx + 1}</div>
                            ${pacingBadge}
                        </div>"""

replace = """                        <div class="flex gap-2 items-center flex-wrap">
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
                        </div>"""

content = content.replace(search, replace)

# 2. Add updateScenePacing function
func = """
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
"""

content = content + "\n\n" + func

with open("frontend/script.js", "w") as f:
    f.write(content)

print("Added pacing slider successfully")
