__all__ = [
    "agents",
    "artifacts",
    "channels",
    "education_assets",
    "education_audit",
    "education_blueprints",
    "education_checkpoints",
    "education_extractions",
    "education_feedback",
    "education_packages",
    "education_projects",
    "education_runs",
    "memory",
    "mcp",
    "models",
    "orgs",
    "resources",
    "skills",
    "student",
    "suggestions",
    "templates",
    "uploads",
]

from importlib import import_module
from typing import Any


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    module = import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module
