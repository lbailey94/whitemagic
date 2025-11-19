"""Helper utilities"""
from datetime import datetime

def now_iso() -> str:
    """Get current time in ISO format"""
    return datetime.now().isoformat()

def format_date(dt: str) -> str:
    """Format date string"""
    return dt

def calculate_ttl_days(created: str, ttl_days: int) -> int:
    """Calculate TTL days"""
    return ttl_days
