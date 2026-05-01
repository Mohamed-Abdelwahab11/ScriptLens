import re

class ScriptSanitizer:
    def __init__(self):
        # We define rules to catch scene headers, even if they are typed weirdly
        self.scene_patterns = [
            r'^(?:INT\.|EXT\.|INT/EXT\.|I/E)[\.\s]*.*$', # Standard English
            r'^(?:داخلي|خارجي)[\.\s\-]*.*$'               # Standard Arabic
        ]
        
    def normalize_text(self, raw_text: str) -> str:
        """Cleans up raw PDF text into a standardized format."""
        # Remove multiple blank lines
        clean_text = re.sub(r'\n{3,}', '\n\n', raw_text)
        
        # Strip trailing/leading whitespaces on every line
        lines = [line.strip() for line in clean_text.split('\n')]
        return '\n'.join(lines)

    def identify_scenes(self, text: str) -> list:
        """Mines the text to find structural scene headers."""
        lines = text.split('\n')
        scenes = []
        for line in lines:
            for pattern in self.scene_patterns:
                # Using regex to find pattern matches ignoring case
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    scenes.append(line.strip().upper())
                    break
        return scenes