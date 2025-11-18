"""Terminal-based reasoning - use terminal for free composite reasoning."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List


class TerminalReasoner:
    """Use terminal output as extended reasoning space (saves tokens!)."""

    def think_aloud(self, problem: str, steps: List[str]) -> Path:
        """Execute reasoning in terminal window."""
        script = f"""#!/bin/bash
echo "🧠 REASONING: {problem}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━"
"""
        for i, step in enumerate(steps, 1):
            script += f'echo "{i}. {step}"\n'

        script += 'echo ""\necho "✅ Complete!"\nread\n'

        # Use secure temp file creation
        fd, temp_path = tempfile.mkstemp(suffix=".sh")  # nosec B306
        path = Path(temp_path)
        os.close(fd)
        path.write_text(script)
        os.chmod(path, 0o700)  # User-only permissions
        subprocess.Popen(["/bin/bash", str(path)])  # nosec B603
        return path


class TerminalDocumentWriter:
    """Generate large documents in terminal (not in response)."""

    def write_document(self, title: str, sections: Dict[str, str], output: Path):
        """Write doc in terminal, save to file."""
        content = f"# {title}\n\n"
        for heading, text in sections.items():
            content += f"## {heading}\n\n{text}\n\n"

        output.write_text(content)
        print(f"📄 Generated: {output}")


class TerminalTestAnalyzer:
    """Run and analyze tests in terminal."""

    def analyze(self, test_path: str) -> Dict[str, Any]:
        """Run tests, show output in terminal."""
        result = subprocess.run(  # nosec B603
            ["/usr/bin/pytest", test_path, "-v"],
            capture_output=True,
            text=True,
            check=False,
        )

        return {
            "passed": result.returncode == 0,
            "output": result.stdout,
        }
