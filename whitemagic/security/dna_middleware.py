"""DNA Middleware - Intercept and validate all operations"""

from typing import Callable, Any, Dict
from functools import wraps


class DNAMiddleware:
    """Middleware that validates operations against DNA principles
    
    Philosophy: Every operation flows through DNA validation.
    Like an immune system checkpoint.
    """
    
    def __init__(self):
        self.validator = None
        self.responder = None
        self._init_components()
    
    def _init_components(self):
        """Initialize validator and responder"""
        try:
            from whitemagic.security.principle_validator import PrincipleValidator
            from whitemagic.security.violation_responder import ViolationResponder
            self.validator = PrincipleValidator()
            self.responder = ViolationResponder()
        except Exception:
            pass
    
    def validate_operation(self, operation: str, context: Dict) -> bool:
        """Validate operation against DNA principles
        
        Args:
            operation: Operation description
            context: Operation context
            
        Returns:
            True if allowed, False if violates DNA
        """
        if not self.validator:
            return True  # Fail open if not available
        
        violations = self.validator.check_operation(operation, context)
        
        if violations:
            if self.responder:
                self.responder.handle_violations(operation, violations)
            return False
        
        return True
    
    def enforce(self, operation_type: str = "general"):
        """Decorator to enforce DNA principles on function
        
        Usage:
            @dna_middleware.enforce("file_operation")
            def create_file(path):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Build context
                context = {
                    'function': func.__name__,
                    'operation_type': operation_type,
                    'args': args,
                    'kwargs': kwargs
                }
                
                # Validate
                if not self.validate_operation(operation_type, context):
                    raise PermissionError(f"DNA principles violated: {operation_type}")
                
                # Execute if validated
                return func(*args, **kwargs)
            
            return wrapper
        return decorator


# Global instance
_middleware: DNAMiddleware = None


def get_dna_middleware() -> DNAMiddleware:
    """Get global DNA middleware instance"""
    global _middleware
    if _middleware is None:
        _middleware = DNAMiddleware()
    return _middleware
