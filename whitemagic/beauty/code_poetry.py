"""
Code Poetry - Structure as Art

Code is not just instructions. Code is EXPRESSION.

Leo (creative expression) + Pisces (artistic synthesis)
"""


class CodePoetry:
    """
    See code as poetry.
    
    Rhythm, flow, elegance - all present in beautiful code.
    """
    
    def analyze_rhythm(self, code: str) -> dict:
        """Analyze the rhythm of code"""
        lines = code.split('\n')
        
        return {
            "line_count": len(lines),
            "avg_line_length": sum(len(l) for l in lines) / max(1, len(lines)),
            "rhythm": "varies" if len(set(len(l) for l in lines)) > 5 else "consistent"
        }
        
    def poetic_interpretation(self, code: str) -> str:
        """Interpret code poetically"""
        return "Like a haiku - brief, clear, complete.\nEach line necessary.\nNothing wasted."
