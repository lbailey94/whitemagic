#!/usr/bin/env python3
"""
Fix python-apt version parsing issue on Zorin OS / Ubuntu derivatives.

The issue: python-apt version "2.4.0-ubuntu4-zorin1" is not PEP 440 compliant.
Solution: Patch pkg_resources to ignore python-apt version parsing.
"""

import sys
import warnings

def fix_python_apt_version():
    """Suppress python-apt version parsing warnings."""
    try:
        # Ignore the specific warning
        warnings.filterwarnings(
            'ignore',
            message='.*Invalid version.*python-apt.*',
            category=UserWarning
        )
        
        # Also patch pkg_resources if available
        try:
            import pkg_resources
            
            # Monkey patch to skip python-apt
            original_get_distribution = pkg_resources.get_distribution
            
            def patched_get_distribution(dist):
                if 'python-apt' in str(dist):
                    # Return a dummy distribution
                    class DummyDist:
                        version = "2.4.0"
                        project_name = "python-apt"
                    return DummyDist()
                return original_get_distribution(dist)
            
            pkg_resources.get_distribution = patched_get_distribution
            
        except ImportError:
            pass
        
        print("✅ python-apt version issue patched")
        return True
        
    except Exception as e:
        print(f"⚠️  Could not patch python-apt: {e}")
        return False

if __name__ == "__main__":
    fix_python_apt_version()
