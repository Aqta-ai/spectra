"""Plugin system with performance optimizations."""

import os
from typing import Callable, Optional

# Plugin registry
_registry = {
    "extra_routers": [],
    "validate_api_key": None,
    "on_session_start": None,
}


def load_plugins():
    """Load plugins from environment."""
    plugin_paths = os.getenv("PLUGIN_PATHS", "").split(",")
    
    for path in plugin_paths:
        path = path.strip()
        if path:
            _load_plugin(path)


def _load_plugin(path: str):
    """Load a single plugin."""
    try:
        # In production, would import actual plugin modules
        print(f"Loading plugin from {path}")
    except Exception as e:
        print(f"Failed to load plugin {path}: {e}")


def register_router(router):
    """Register extra router."""
    _registry["extra_routers"].append(router)


def register_api_validator(func: Callable[[str], Optional[tuple[dict, str]]]):
    """Register API key validator."""
    _registry["validate_api_key"] = func


def register_session_handler(func: Callable[[str, str, str], None]):
    """Register session start handler."""
    _registry["on_session_start"] = func


def get_registry():
    """Get plugin registry."""
    return _registry


# Export registry as a module-level variable for backward compatibility
class Registry:
    """Registry wrapper for easy access."""
    @property
    def extra_routers(self):
        return _registry["extra_routers"]
    
    @property
    def validate_api_key(self):
        return _registry["validate_api_key"]
    
    @property
    def on_session_start(self):
        return _registry["on_session_start"]


registry = Registry()
