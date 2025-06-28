"""
Backend package for the Tailor Talk application.
"""

__version__ = "1.0.0"

# Use lazy imports to avoid circular imports
import importlib

def __getattr__(name):
    if name == 'app':
        from .main import app
        return app
    elif name == 'process_user_message':
        from .agent import process_user_message
        return process_user_message
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ["app", "process_user_message"]
