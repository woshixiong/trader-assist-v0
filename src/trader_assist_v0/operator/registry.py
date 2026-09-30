"""Fixed project-owned dashboard module registration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    module_id: str
    title: str
    renderer: str
    builder: str


KNOWN_RENDERERS = frozenset({"three_setup_nautilus"})
KNOWN_BUILDERS = frozenset({"three_setup_current"})
MODULES = (
    ModuleSpec(
        "three_setup_nautilus", "Three Setup / Nautilus",
        "three_setup_nautilus", "three_setup_current",
    ),
)


def validate_registry(modules: tuple[ModuleSpec, ...] = MODULES) -> tuple[ModuleSpec, ...]:
    ids: set[str] = set()
    for module in modules:
        if not module.module_id or module.module_id in ids:
            raise ValueError("duplicate or empty dashboard module id")
        if module.renderer not in KNOWN_RENDERERS:
            raise ValueError("unknown dashboard renderer")
        if module.builder not in KNOWN_BUILDERS:
            raise ValueError("unknown dashboard builder")
        ids.add(module.module_id)
    return modules
