"""
Common utilities for frontend Engine initialization and management.

This module provides helpers for creating and managing Engine instances
across different frontends (CLI, Chainlit, Slack, etc.).
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv

from backend.engine.config import Config
from backend.engine.engine import Engine


def create_from_config(
    config_path: str, 
    session_id: Optional[str] = None,
    env_file_path: Optional[str] = None
) -> Tuple[Engine, Config]:
    """Create an Engine instance from a configuration file.
    
    Args:
        config_path: Path to the configuration file (JSON, YAML, or TOML)
        session_id: Optional session ID to load after initialization
        env_file_path: Optional path to a .env file to load environment variables from
        
    Returns:
        A tuple containing (engine, config) where engine is the initialized
        Engine instance and config is the loaded Config object.
    """
    # Load environment variables from .env file if provided
    if env_file_path and os.path.exists(env_file_path):
        load_dotenv(env_file_path)
    else:
        load_dotenv()

    # Pre-create the memory directory so Config.invariant() doesn't fail on a
    # first run before the directory has been created yet.
    import json as _json
    try:
        with open(config_path) as _f:
            _raw = _json.load(_f)
        _mem = _raw.get("memory_dir", "")
        import re as _re
        _mem = _re.sub(r'\$\{([^}]+)\}', lambda m: os.environ.get(m.group(1), ''), _mem)
        if _mem:
            Path(_mem).mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Load the configuration
    config = Config.from_file(config_path)

    # Ensure memory directory exists (catches any paths resolved inside Config)
    memory_dir = Path(config.memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    # Create the engine from the configuration
    engine = Engine.from_config_file(config_path)
    
    # Load session if provided
    if session_id:
        if not engine.load_session(session_id):
            raise ValueError(f"Session ID not found: {session_id}")
    
    return engine, config