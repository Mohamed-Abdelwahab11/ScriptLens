import re

class EntityExtractor:
    def __init__(self):
        # Structural Stop-Words (Technical script markers)
        self.technical_markers = {
            "EXT", "INT", "DAY", "NIGHT", "CONTINUOUS", "MOMENTS", "LATER",
            "على", "إلى", "في", "من", "عن", "مع", "هذا", "بعد", "نحو", "خارجي", "داخلي"
        }
        
        # Action Verbs (Triggers to identify a character subject)
        self.action_triggers_en = r'\b(walks|runs|stands|looks|stares|whispers|screams|holds|clutches|turns)\b'
        self.action_triggers_ar = r'\b(يمشي|يركض|يقف|ينظر|يحدق|يهمس|يصرخ|يمسك|يلتفت)\b'

    def detect_language(self, text: str) -> str:
        return "ARABIC" if re.search(r'[\u0600-\u06FF]', text) else "ENGLISH"

    def _clean_and_verify(self, candidates, text, lang):
        final_chars = set()
        triggers = self.action_triggers_ar if lang == "ARABIC" else self.action_triggers_en
        
        for name in candidates:
            if name.upper() in self.technical_markers or name in self.technical_markers:
                continue
            
            # Contextual Intelligence: Is the name near an action verb?
            name_pattern = re.escape(name)
            if re.search(fr'{name_pattern}.{{0,25}}{triggers}|{triggers}.{{0,25}}{name_pattern}', text, re.IGNORECASE):
                final_chars.add(name.capitalize() if lang == "ENGLISH" else name)
            
            # Positional Intelligence: Is it the first word of the block?
            elif text.strip().startswith(name):
                final_chars.add(name.capitalize() if lang == "ENGLISH" else name)

        return list(final_chars)

    def _extract_arabic(self, text: str) -> list:
        potential = re.findall(r'\b[\u0621-\u064A]{3,10}(?:\s+[\u0621-\u064A]{3,10})?\b', text)
        return self._clean_and_verify(potential, text, "ARABIC")

    def _extract_english(self, text: str) -> list:
        all_caps = re.findall(r'\b[A-Z]{3,12}\b', text)
        title_case = re.findall(r'^[A-Z][a-z]{2,10}\b|\. [A-Z][a-z]{2,10}\b', text)
        title_case = [n.replace(". ", "").strip() for n in title_case]
        return self._clean_and_verify(set(all_caps + title_case), text, "ENGLISH")

    def extract_characters(self, text: str) -> list:
        lang = self.detect_language(text)
        results = self._extract_arabic(text) if lang == "ARABIC" else self._extract_english(text)
        return results if results else ["None detected"]