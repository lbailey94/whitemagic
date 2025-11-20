"""Bottleneck Detector - Identify performance bottlenecks"""

from typing import Dict, List


class BottleneckDetector:
    """Detect performance bottlenecks"""
    
    def analyze_metrics(self, metrics: List) -> Dict:
        """Analyze metrics for bottlenecks
        
        Returns:
            Dict with bottleneck analysis
        """
        if not metrics:
            return {'bottlenecks': []}
        
        # Find operations taking > 100ms
        slow_ops = [m for m in metrics if m.duration_ms > 100]
        
        # Group by operation type
        by_operation = {}
        for metric in slow_ops:
            op = metric.operation
            if op not in by_operation:
                by_operation[op] = []
            by_operation[op].append(metric.duration_ms)
        
        # Calculate averages
        bottlenecks = []
        for op, durations in by_operation.items():
            avg = sum(durations) / len(durations)
            if avg > 100:
                bottlenecks.append({
                    'operation': op,
                    'average_ms': avg,
                    'occurrences': len(durations),
                    'severity': 'high' if avg > 500 else 'medium'
                })
        
        # Sort by severity
        bottlenecks = sorted(bottlenecks, key=lambda b: b['average_ms'], reverse=True)
        
        return {
            'bottlenecks': bottlenecks,
            'total_slow_operations': len(slow_ops),
            'recommendations': self._get_recommendations(bottlenecks)
        }
    
    def _get_recommendations(self, bottlenecks: List[Dict]) -> List[str]:
        """Get optimization recommendations"""
        recommendations = []
        
        for bottleneck in bottlenecks:
            op = bottleneck['operation']
            
            if 'file_read' in op.lower():
                recommendations.append(f"Consider Rust bridge for: {op}")
            elif 'pattern' in op.lower():
                recommendations.append(f"Consider Haskell type safety for: {op}")
            elif 'search' in op.lower():
                recommendations.append(f"Consider parallel processing for: {op}")
            else:
                recommendations.append(f"Profile and optimize: {op}")
        
        return recommendations
