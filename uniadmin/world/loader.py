import copy
import json
import os
from typing import Any, Dict

_WORLD_DIR = os.path.dirname(__file__)
_WORLD_SEED_PATH = os.path.join(_WORLD_DIR, "world_seed.json")
_POLICIES_PATH = os.path.join(_WORLD_DIR, "policies.json")

# Cache the loaded JSON so we only read from disk once
_world_cache: Dict[str, Any] = {}
_policies_cache: Dict[str, Any] = {}


def _ensure_loaded() -> None:
    """Load world_seed.json and policies.json into cache if not already loaded."""
    global _world_cache, _policies_cache

    if not _world_cache:
        if not os.path.exists(_WORLD_SEED_PATH):
            raise FileNotFoundError(
                f"World seed not found at {_WORLD_SEED_PATH}. "
                "Run: python uniadmin/world/generator.py"
            )
        with open(_WORLD_SEED_PATH, "r", encoding="utf-8") as f:
            _world_cache = json.load(f)

    if not _policies_cache:
        if not os.path.exists(_POLICIES_PATH):
            raise FileNotFoundError(
                f"Policies not found at {_POLICIES_PATH}. "
                "Run: python uniadmin/world/generator.py"
            )
        with open(_POLICIES_PATH, "r", encoding="utf-8") as f:
            _policies_cache = json.load(f)


def load_world_copy() -> Dict[str, Any]:
    """Return a deep copy of the world entity graph.

    Each call returns an independent copy so mutations during an episode
    do not affect subsequent episodes.
    """
    _ensure_loaded()
    return copy.deepcopy(_world_cache)


def load_policies() -> Dict[str, Any]:
    """Return the policies dict (not deep-copied — policies are read-only)."""
    _ensure_loaded()
    return _policies_cache


def get_task_entity_refs() -> Dict[str, Any]:
    """Return the task-specific entity reference map."""
    _ensure_loaded()
    return copy.deepcopy(_world_cache.get("_task_entity_refs", {}))
