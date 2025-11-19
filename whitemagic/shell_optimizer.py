"""Shell Technique Library - Systematized emergent behaviors"""

import subprocess
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ShellTechnique:
    name: str
    command_template: str
    use_case: str
    confidence: float
    emerged_from: str  # Where was this discovered?

class ShellOptimizer:
    """Collection of shell techniques that emerged during development"""
    
    TECHNIQUES = {
        "fast_large_write": ShellTechnique(
            name="Fast Large File Write",
            command_template="cat > {file} << 'EOF'\n{content}\nEOF",
            use_case="Write large files without tool timeouts",
            confidence=0.95,
            emerged_from="v2.3.2 development - bypassed multi_edit timeouts"
        ),
        
        "parallel_batch": ShellTechnique(
            name="Parallel Batch Processing",
            command_template="find {dir} -name '{pattern}' | xargs -P {jobs} -n 1 {cmd}",
            use_case="Process multiple files in parallel",
            confidence=0.90,
            emerged_from="Standard Unix pattern"
        ),
        
        "stream_grep": ShellTechnique(
            name="Stream Processing with Grep",
            command_template="tail -f {file} | grep '{pattern}' | while read line; do {action}; done",
            use_case="Real-time log monitoring and filtering",
            confidence=0.85,
            emerged_from="DevOps best practices"
        ),
        
        "fast_search": ShellTechnique(
            name="Ripgrep JSON Output",
            command_template="rg --json '{pattern}' | jq '.data.lines.text'",
            use_case="Fast search with structured output",
            confidence=0.88,
            emerged_from="Modern CLI tools"
        ),
        
        "named_pipes": ShellTechnique(
            name="Named Pipes for IPC",
            command_template="mkfifo /tmp/pipe && {cmd1} > /tmp/pipe & {cmd2} < /tmp/pipe",
            use_case="Inter-process communication without files",
            confidence=0.75,
            emerged_from="Unix IPC patterns"
        ),
        
        "process_substitution": ShellTechnique(
            name="Process Substitution",
            command_template="diff <({cmd1}) <({cmd2})",
            use_case="Compare outputs without temporary files",
            confidence=0.82,
            emerged_from="Bash advanced features"
        ),
        
        "background_jobs": ShellTechnique(
            name="Background Job Control",
            command_template="{job1} & {job2} & {job3} &\nwait",
            use_case="Run multiple jobs concurrently",
            confidence=0.90,
            emerged_from="Shell scripting fundamentals"
        ),
        
        "memory_efficient": ShellTechnique(
            name="Memory-Efficient Line Extraction",
            command_template="sed -n '{start},{end}p' {file}",
            use_case="Extract lines without loading entire file",
            confidence=0.92,
            emerged_from="Stream processing patterns"
        ),
        
        "one_liner_update": ShellTechnique(
            name="One-Liner File Update",
            command_template="sed -i 's/{old}/{new}/g' {file}",
            use_case="Quick find-and-replace without loading file",
            confidence=0.88,
            emerged_from="Text processing patterns"
        ),
        
        "conditional_chain": ShellTechnique(
            name="Conditional Execution Chain",
            command_template="{cmd1} && {cmd2} || {cmd3}",
            use_case="If cmd1 succeeds run cmd2, else cmd3",
            confidence=0.95,
            emerged_from="Shell scripting fundamentals"
        )
    }
    
    @classmethod
    def fast_write(cls, file_path: Path, content: str) -> bool:
        """Use shell for large file writes - bypasses tool timeouts"""
        try:
            cmd = f"cat > {file_path} << 'EOF'\n{content}\nEOF"
            subprocess.run(cmd, shell=True, check=True)
            return True
        except Exception as e:
            print(f"Shell write failed: {e}")
            return False
    
    @classmethod
    def parallel_process(cls, files: List[Path], command: str, jobs: int = 4) -> bool:
        """Process files in parallel"""
        try:
            file_list = "\n".join(str(f) for f in files)
            cmd = f"echo '{file_list}' | xargs -P {jobs} -n 1 {command}"
            subprocess.run(cmd, shell=True, check=True)
            return True
        except Exception as e:
            print(f"Parallel processing failed: {e}")
            return False
    
    @classmethod
    def get_technique(cls, name: str) -> Optional[ShellTechnique]:
        """Get technique by name"""
        return cls.TECHNIQUES.get(name)
    
    @classmethod
    def all_techniques(cls) -> List[ShellTechnique]:
        """Get all techniques"""
        return list(cls.TECHNIQUES.values())

# Export
__all__ = ['ShellOptimizer', 'ShellTechnique']
