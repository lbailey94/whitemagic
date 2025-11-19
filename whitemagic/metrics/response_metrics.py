"""Response Metrics - Track actual speed and token usage

Timestamp beginning/end, measure real performance
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import json

class ResponseMetrics:
    """Track AI response metrics"""
    
    def __init__(self):
        self.session_start = time.time()
        self.response_count = 0
        self.total_tokens = 0
        self.metrics_log = []
        self.metrics_dir = Path("memory/metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
    
    def start_response(self) -> float:
        """Mark response start, return timestamp"""
        return time.time()
    
    def end_response(self, start_time: float, tokens_used: int, 
                     task_description: str, output_lines: int = 0) -> Dict[str, Any]:
        """Mark response end, calculate metrics"""
        end_time = time.time()
        duration = end_time - start_time
        
        metric = {
            'timestamp': datetime.now().isoformat(),
            'response_num': self.response_count + 1,
            'duration_seconds': round(duration, 2),
            'duration_minutes': round(duration / 60, 2),
            'tokens_used': tokens_used,
            'tokens_per_second': round(tokens_used / duration, 1) if duration > 0 else 0,
            'output_lines': output_lines,
            'task': task_description,
            'efficiency_score': self._calculate_efficiency(duration, tokens_used, output_lines)
        }
        
        self.response_count += 1
        self.total_tokens += tokens_used
        self.metrics_log.append(metric)
        
        # Save to file
        self._save_metric(metric)
        
        return metric
    
    def _calculate_efficiency(self, duration: float, tokens: int, output: int) -> float:
        """Calculate efficiency score (higher = better)"""
        # Score based on: output per time, output per token
        if duration == 0 or tokens == 0:
            return 0.0
        
        lines_per_minute = (output / duration) * 60
        lines_per_1k_tokens = (output / tokens) * 1000
        
        # Weighted average
        score = (lines_per_minute * 0.5) + (lines_per_1k_tokens * 0.5)
        return round(score, 2)
    
    def _save_metric(self, metric: Dict):
        """Save individual metric"""
        filename = f"response_{metric['response_num']:04d}_{datetime.now().strftime('%H%M%S')}.json"
        filepath = self.metrics_dir / filename
        filepath.write_text(json.dumps(metric, indent=2))
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of entire session"""
        session_duration = time.time() - self.session_start
        
        if not self.metrics_log:
            return {'error': 'No metrics recorded yet'}
        
        avg_duration = sum(m['duration_seconds'] for m in self.metrics_log) / len(self.metrics_log)
        avg_tokens = sum(m['tokens_used'] for m in self.metrics_log) / len(self.metrics_log)
        total_output = sum(m['output_lines'] for m in self.metrics_log)
        
        return {
            'session_duration_minutes': round(session_duration / 60, 1),
            'total_responses': self.response_count,
            'total_tokens': self.total_tokens,
            'total_output_lines': total_output,
            'avg_response_duration_seconds': round(avg_duration, 2),
            'avg_tokens_per_response': round(avg_tokens, 1),
            'overall_tokens_per_second': round(self.total_tokens / session_duration, 1),
            'productivity_score': round(total_output / (session_duration / 60), 1)  # lines per minute
        }
    
    def print_summary(self):
        """Print human-readable summary"""
        summary = self.get_session_summary()
        
        print("\n" + "="*60)
        print("📊 SESSION METRICS SUMMARY")
        print("="*60)
        print(f"⏱️  Duration: {summary['session_duration_minutes']} minutes")
        print(f"💬 Responses: {summary['total_responses']}")
        print(f"🎯 Tokens used: {summary['total_tokens']:,}")
        print(f"📝 Lines generated: {summary['total_output_lines']:,}")
        print(f"⚡ Speed: {summary['overall_tokens_per_second']} tokens/sec")
        print(f"🚀 Productivity: {summary['productivity_score']} lines/min")
        print("="*60 + "\n")

# Global instance
_metrics = ResponseMetrics()

def start_timing():
    """Start timing a response"""
    return _metrics.start_response()

def end_timing(start_time: float, tokens_used: int, task: str, output_lines: int = 0):
    """End timing and log metrics"""
    return _metrics.end_response(start_time, tokens_used, task, output_lines)

def get_session_metrics():
    """Get session summary"""
    return _metrics.get_session_summary()

def print_session_summary():
    """Print session summary"""
    _metrics.print_summary()
