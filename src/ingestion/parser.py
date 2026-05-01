import fitz
import re

class ScriptParser:
    def __init__(self):
        self.scene_pattern = re.compile(r'^(INT\.|EXT\.)\s+.*', re.IGNORECASE | re.MULTILINE)
        self.character_pattern = re.compile(r'^\s*([A-Z][A-Z\s\d]+)$', re.MULTILINE)
        
        # Expanded pattern to catch variations like "CLOSE", "CU", "WIDE", etc.
        self.visual_cues_pattern = re.compile(
            r'(WIDE SHOT|CLOSE UP|CLOSE|WIDE|CU|EYE LEVEL|TRACKING SHOT|SLOW MOTION|ZOOM IN|PAN|TILT|ESTABLISHING SHOT)', 
            re.IGNORECASE
        )

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text("text")
        return text

    def parse(self, pdf_path):
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        scenes = self.scene_pattern.findall(raw_text)
        raw_characters = self.character_pattern.findall(raw_text)
        visual_cues = self.visual_cues_pattern.findall(raw_text)
        
        characters = sorted(list(set([m.strip() for m in raw_characters if len(m.strip()) > 1])))
        
        return {
            "stats": {
                "scene_count": len(scenes),
                "character_count": len(characters),
                "visual_cues_count": len(visual_cues)
            },
            "details": {
                "scenes": [s.strip() for s in scenes],
                "characters": characters,
                "detected_visual_cues": sorted(list(set(visual_cues)))
            }
        }