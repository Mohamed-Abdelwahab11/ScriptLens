class CinematicIntelligence:
    def __init__(self):
        self.matrix = {
            "WIDE SHOT": {
                "keys": ["horizon", "landscape", "vast", "exterior", "الأفق", "واسعة", "صحراء", "خارجي"],
                "weight": 1.0
            },
            "CLOSE UP": {
                "keys": ["eyes", "trembling", "whisper", "clutches", "flicker", "عيناها", "ترتجف", "تلمس", "همس", "وجهها", "ثقاب"],
                "weight": 1.7 
            },
            "MEDIUM SHOT": {
                "keys": ["stands", "walks", "sits", "talks", "تقف", "تمشي", "يجلس"],
                "weight": 0.8
            }
        }

    def infer_cinematography(self, action_text: str):
        normalized = action_text.lower()
        scores = {shot: 0.0 for shot in self.matrix.keys()}

        for shot_type, data in self.matrix.items():
            for key in data["keys"]:
                if key in normalized:
                    scores[shot_type] += data["weight"]

        winning_shot = max(scores, key=scores.get)
        if scores[winning_shot] == 0: winning_shot = "MEDIUM SHOT"

        return {
            "inferred_data": [{
                "shot_type": winning_shot,
                "confidence": 0.8 if scores[winning_shot] > 0 else 0.5,
                "reason": f"Heuristic density favors {winning_shot.lower()} patterns."
            }]
        }