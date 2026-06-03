"""Domain pack loader — discovers and loads DomainSpec instances.

Discovery order:
  1. Python entry_points (group='pwps.domains') — for installed packages
  2. Directory scan of PWPS_DOMAIN_PATH — for development / local packs

A domain pack directory must contain at minimum:
  - domain.yaml   (name, version)
  - fields.yaml   (field definitions + groups)

Optional files:
  - prompts/*.md          (prompt templates keyed by filename)
  - default_prior.yaml    (soft fallback candidate values)
  - render_templates/*    (output render templates)
"""

from __future__ import annotations

import importlib.metadata
import logging
import os
from pathlib import Path
from typing import Any

import yaml

from pwps_agent_api.domain.spec import DomainSpec
from pwps_agent_api.fields.registry import FieldRegistry, _field, _group
from pwps_agent_api.schemas import (
    ConfirmationPolicy,
    FieldGroupSpec,
    FieldSpec,
    FieldType,
    InferencePolicy,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_domain(name: str | None = None) -> DomainSpec:
    """Load a domain pack by name.

    If *name* is None, loads the first discovered domain.
    Raises FileNotFoundError if the domain cannot be found.
    """
    # Try entry_points first
    for ep in _iter_entry_points():
        if name is None or ep.name == name:
            try:
                loader = ep.load()
                spec = loader()
                if isinstance(spec, DomainSpec):
                    log.info("Loaded domain '%s' from entry_point '%s'", spec.name, ep.name)
                    return spec
            except Exception:
                log.debug("entry_point '%s' failed to load", ep.name, exc_info=True)

    # Fallback: directory scan
    for pack_dir in _iter_domain_dirs():
        meta = _load_meta(pack_dir)
        if meta is None:
            continue
        if name is not None and meta["name"] != name:
            continue
        spec = _load_domain_from_dir(pack_dir, meta)
        log.info("Loaded domain '%s' from directory '%s'", spec.name, pack_dir)
        return spec

    raise FileNotFoundError(f"Domain pack '{name}' not found.")


def list_domains() -> list[str]:
    """Return names of all discoverable domain packs."""
    names: list[str] = []

    for ep in _iter_entry_points():
        names.append(ep.name)

    for pack_dir in _iter_domain_dirs():
        meta = _load_meta(pack_dir)
        if meta is not None and meta["name"] not in names:
            names.append(meta["name"])

    return names


# ---------------------------------------------------------------------------
# Entry-points discovery
# ---------------------------------------------------------------------------


def _iter_entry_points():
    """Yield entry points registered under 'pwps.domains'."""
    try:
        eps = importlib.metadata.entry_points()
        # Python 3.12+ returns a SelectableGroups; older returns dict
        if hasattr(eps, "select"):
            yield from eps.select(group="pwps.domains")
        else:
            yield from eps.get("pwps.domains", [])  # type: ignore[union-attr]
    except Exception:
        return


# ---------------------------------------------------------------------------
# Directory scanning
# ---------------------------------------------------------------------------


def _iter_domain_dirs():
    """Yield directories that look like domain packs."""
    search_paths: list[Path] = []

    env_path = os.environ.get("PWPS_DOMAIN_PATH")
    if env_path:
        for p in env_path.split(os.pathsep):
            search_paths.append(Path(p))

    # Also check a conventional location relative to the project root
    project_root = _find_project_root()
    if project_root:
        search_paths.append(project_root / "domains")

    for search_dir in search_paths:
        if not search_dir.is_dir():
            continue
        for child in sorted(search_dir.iterdir()):
            if child.is_dir() and (child / "domain.yaml").exists():
                yield child


def _find_project_root() -> Path | None:
    """Walk up from this file to find a directory containing 'domains/'."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "domains").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_meta(pack_dir: Path) -> dict[str, Any] | None:
    """Load and validate domain.yaml metadata."""
    meta_path = pack_dir / "domain.yaml"
    if not meta_path.exists():
        return None
    try:
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            return None
        if "name" not in meta or "version" not in meta:
            log.warning("domain.yaml missing 'name' or 'version': %s", meta_path)
            return None
        return meta
    except Exception:
        log.debug("Failed to parse %s", meta_path, exc_info=True)
        return None


def _load_domain_from_dir(pack_dir: Path, meta: dict[str, Any]) -> DomainSpec:
    """Build a DomainSpec from a pack directory and its parsed metadata."""
    field_registry = _load_field_registry(pack_dir)
    prompt_templates = _load_prompt_templates(pack_dir)
    audit_dimensions = _load_audit_dimensions(pack_dir, prompt_templates)
    default_prior = _load_yaml_dict(pack_dir / "default_prior.yaml")
    render_templates = _load_render_templates(pack_dir)
    seed_documents = _discover_seed_documents(pack_dir)

    return DomainSpec(
        name=meta["name"],
        version=meta["version"],
        field_registry=field_registry,
        prompt_templates=prompt_templates,
        audit_dimensions=audit_dimensions,
        default_prior=default_prior,
        render_templates=render_templates,
        seed_documents=seed_documents,
    )


def _load_field_registry(pack_dir: Path) -> FieldRegistry:
    """Load fields.yaml and build a FieldRegistry."""
    fields_path = pack_dir / "fields.yaml"
    if not fields_path.exists():
        raise FileNotFoundError(f"fields.yaml not found in {pack_dir}")

    raw = yaml.safe_load(fields_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"fields.yaml must be a mapping: {fields_path}")

    fields_raw: dict[str, Any] = raw.get("fields", {})
    groups_raw: dict[str, Any] = raw.get("groups", {})

    fields = {name: _parse_field_spec(name, spec) for name, spec in fields_raw.items()}
    groups = {name: _parse_group_spec(name, spec) for name, spec in groups_raw.items()}

    return FieldRegistry(fields=fields, groups=groups)


def _parse_field_spec(name: str, raw: dict[str, Any]) -> FieldSpec:
    """Parse a single field definition from YAML into a FieldSpec."""
    return FieldSpec(
        name=name,
        label=raw.get("label", name),
        group=raw.get("group", ""),
        field_type=FieldType(raw.get("field_type", "string")),
        description=raw.get("description", ""),
        unit=raw.get("unit"),
        enum_values=raw.get("enum_values", []),
        required_for_start=raw.get("required_for_start", False),
        required_for_draft=raw.get("required_for_draft", True),
        high_risk=raw.get("high_risk", False),
        inference_policy=InferencePolicy(raw.get("inference_policy", "model_allowed")),
        confirmation_policy=ConfirmationPolicy(raw.get("confirmation_policy", "confirm_if_low_evidence")),
        dependencies=raw.get("dependencies", []),
        affects=raw.get("affects", []),
        output_section=raw.get("output_section"),
        audit_rules=raw.get("audit_rules", []),
        candidate_strategy=raw.get("candidate_strategy"),
        examples=raw.get("examples", []),
    )


def _parse_group_spec(name: str, raw: dict[str, Any]) -> FieldGroupSpec:
    """Parse a single group definition from YAML into a FieldGroupSpec."""
    return FieldGroupSpec(
        name=name,
        label=raw.get("label", name),
        description=raw.get("description", ""),
        fields=raw.get("fields", []),
        required_fields=raw.get("required_fields", []),
        optional_fields=raw.get("optional_fields", []),
        depends_on_groups=raw.get("depends_on_groups", []),
        confirmation_order=raw.get("confirmation_order", 99),
    )


def _load_prompt_templates(pack_dir: Path) -> dict[str, str]:
    """Load all .md files from prompts/ directory."""
    prompts_dir = pack_dir / "prompts"
    if not prompts_dir.is_dir():
        return {}

    templates: dict[str, str] = {}
    for md_file in sorted(prompts_dir.glob("*.md")):
        key = md_file.stem  # e.g. "candidate_generation"
        templates[key] = md_file.read_text(encoding="utf-8")

    return templates


def _load_audit_dimensions(pack_dir: Path, prompt_templates: dict[str, str]) -> list[str]:
    """Extract audit dimensions from audit prompt template or config.

    Looks for a YAML front-matter block in the audit prompt template
    containing a 'dimensions' list.  Falls back to a default list.
    """
    audit_prompt = prompt_templates.get("audit", "")
    # Try to extract from YAML front-matter
    if audit_prompt.startswith("---"):
        try:
            _, front_matter, _ = audit_prompt.split("---", 2)
            meta = yaml.safe_load(front_matter)
            if isinstance(meta, dict) and "dimensions" in meta:
                return list(meta["dimensions"])
        except Exception:
            pass

    # Default dimensions
    return [
        "工艺兼容性",
        "参数完整性",
        "热过程合规性",
        "证据充分性",
        "字段约束",
    ]


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    """Load a YAML file as a dict, returning empty dict if missing."""
    if not path.exists():
        return {}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        log.debug("Failed to parse %s", path, exc_info=True)
        return {}


def _load_render_templates(pack_dir: Path) -> dict[str, str]:
    """Load all files from render_templates/ directory."""
    templates_dir = pack_dir / "render_templates"
    if not templates_dir.is_dir():
        return {}

    templates: dict[str, str] = {}
    for f in sorted(templates_dir.iterdir()):
        if f.is_file():
            templates[f.stem] = f.read_text(encoding="utf-8")

    return templates


def _discover_seed_documents(pack_dir: Path) -> list[Path]:
    """Discover seed documents in the pack's seed_documents/ directory."""
    seed_dir = pack_dir / "seed_documents"
    if not seed_dir.is_dir():
        return []

    return sorted(p for p in seed_dir.rglob("*") if p.is_file())
