from pydantic import BaseModel
from typing import List, Dict, Any, Optional
# 1. The Input Schema (What the user sends us)
class ScriptRequest(BaseModel):
    script_text: str

# 2. The Output Schema (What we send back)
class ShotInference(BaseModel):
    shot_type: str
    reason: str
    confidence: float

class SceneAnalysis(BaseModel):
    scene_header: str
    characters: List[str]
    inferred_data: List[ShotInference]

class APIResponse(BaseModel):
    status: str
    total_scenes: int
    analysis: List[Any]  # Using Any to allow for flexible data structures in the analysis
    metrics: Optional[Dict[str, Any]] = None  # For future analytics data