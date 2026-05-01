class ScriptAnalytics:
    def __init__(self):
        self.categories = ["WIDE SHOT", "MEDIUM SHOT", "CLOSE UP"]

    def calculate_visual_pace(self, analysis_data):
        total_shots = len(analysis_data)
        
        # SAFETY CHECK: If no scenes are found, return empty metrics instead of crashing
        if total_shots == 0:
            return {
                "shot_distribution": {"WIDE SHOT": 0, "MEDIUM SHOT": 0, "CLOSE UP": 0},
                "pacing_score": 0.0
            }

        distribution = {"WIDE SHOT": 0, "MEDIUM SHOT": 0, "CLOSE UP": 0}
        
        for scene in analysis_data:
            # Handle list of dictionaries (from our latest app.py)
            inferred = scene.get("inferred_data", [])
            for shot in inferred:
                # Use .get() to prevent KeyErrors
                shot_type = shot.get("shot_type")
                if shot_type in distribution:
                    distribution[shot_type] += 1

        metrics = {
            "shot_distribution": {k: (v / total_shots) * 100 for k, v in distribution.items()},
            "pacing_score": round((distribution["CLOSE UP"] - distribution["WIDE SHOT"]) / total_shots, 2)
        }
        return metrics

    def _calculate_pacing(self, dist, total):
        # A simple weight: Close Ups (Fast) vs Wides (Slow)
        # Result > 0 is "Intense", < 0 is "Atmospheric"
        score = (dist["CLOSE UP"] - dist["WIDE SHOT"]) / total
        return round(score, 2)