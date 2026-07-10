#!/usr/bin/env python3
"""Audit generated inventory files for upstream fidelity and Ansible conventions.

Run from repo root or `installer/`:
    python3 scripts/audit_inventories.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AAP_REPO_ROOT = REPO_ROOT.parent

BOOL_CAP = re.compile(r"(?<![a-zA-Z])(True|False)(?![a-zA-Z])")
PYTHON_NONE = re.compile(r"=\s*None\b")
CONFIG_SECTION = re.compile(r"# .+ Configuration\s*$")

RPM_CASES = [
    ("2.4", "AAP24/rpm/inventory-example", ".installer-dumps/2.4/ansible-automation-platform-setup-2.4-16/inventory"),
    ("2.5", "AAP25/rpm/inventory-example", ".installer-dumps/2.5/ansible-automation-platform-setup-2.5-23/inventory"),
    ("2.6", "AAP26/rpm/inventory-example", ".installer-dumps/2.6/ansible-automation-platform-setup-2.6-7/inventory"),
]

CONTAINERIZED_CASES = [
    ("2.5 enterprise", "AAP25/containerized/inventory-example", ".installer-dumps/2.5/ansible-automation-platform-containerized-setup-2.5-25/inventory"),
    ("2.5 growth", "AAP25/containerized/inventory-growth-example", ".installer-dumps/2.5/ansible-automation-platform-containerized-setup-2.5-25/inventory-growth"),
    ("2.6 enterprise", "AAP26/containerized/inventory-example", ".installer-dumps/2.6/ansible-automation-platform-containerized-setup-2.6-10/inventory"),
    ("2.6 growth", "AAP26/containerized/inventory-growth-example", ".installer-dumps/2.6/ansible-automation-platform-containerized-setup-2.6-10/inventory-growth"),
    ("2.7 enterprise", "AAP27/containerized/inventory-example", ".installer-dumps/2.7/ansible-automation-platform-containerized-setup-2.7-2/inventory"),
    ("2.7 growth", "AAP27/containerized/inventory-growth-example", ".installer-dumps/2.7/ansible-automation-platform-containerized-setup-2.7-2/inventory-growth"),
]

CATALOG_MARKERS = ("# Additional optional", "# Optional variables")


def extract_enabled_lines(text: str) -> list[str]:
    in_all = False
    lines: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s == "[all:vars]":
            in_all = True
            continue
        if in_all and (s.startswith("[") or s.startswith(CATALOG_MARKERS)):
            break
        if in_all and s and not s.startswith("#"):
            lines.append(s)
    return lines


def enabled_var_names(text: str) -> set[str]:
    return {line.split("=")[0].strip() for line in extract_enabled_lines(text) if "=" in line}


def catalog_duplicates(text: str, enabled: set[str]) -> list[str]:
    dups: list[str] = []
    in_catalog = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(CATALOG_MARKERS):
            in_catalog = True
            continue
        if not in_catalog:
            continue
        m = re.match(r"#\s*([a-zA-Z_][\w]*)=", s)
        if m and m.group(1) in enabled:
            dups.append(m.group(1))
    return dups


def empty_configuration_sections(text: str) -> list[tuple[int, str]]:
    issues: list[tuple[int, str]] = []
    lines = text.splitlines()
    in_all = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s == "[all:vars]":
            in_all = True
            continue
        if not in_all or s.startswith(CATALOG_MARKERS):
            if in_all and s.startswith(CATALOG_MARKERS):
                break
            continue
        if not CONFIG_SECTION.match(s):
            continue
        j = i + 1
        has_enabled = False
        while j < len(lines):
            ns = lines[j].strip()
            if ns.startswith(CATALOG_MARKERS):
                break
            if ns and not ns.startswith("#"):
                has_enabled = True
                break
            if CONFIG_SECTION.match(ns):
                break
            j += 1
        if not has_enabled:
            issues.append((i + 1, s))
    return issues


def audit_file(label: str, gen_path: Path, up_path: Path | None) -> list[str]:
    issues: list[str] = []
    text = gen_path.read_text(encoding="utf-8")
    enabled = enabled_var_names(text)

    for i, line in enumerate(text.splitlines(), 1):
        if BOOL_CAP.search(line):
            issues.append(f"{label}:{i}: capitalized bool")
        if PYTHON_NONE.search(line):
            issues.append(f"{label}:{i}: Python None")

    for dup in catalog_duplicates(text, enabled):
        issues.append(f"{label}: enabled var duplicated in optional catalog: {dup}")

    for lineno, title in empty_configuration_sections(text):
        issues.append(f"{label}:{lineno}: empty configuration section: {title}")

    if up_path and up_path.exists():
        up_enabled = extract_enabled_lines(up_path.read_text(encoding="utf-8"))
        gen_enabled = extract_enabled_lines(text)
        if up_enabled != gen_enabled:
            issues.append(f"{label}: enabled [all:vars] lines differ from upstream")

    return issues


def main() -> int:
    issues: list[str] = []
    for ver, gen_rel, up_rel in RPM_CASES + CONTAINERIZED_CASES:
        gen = REPO_ROOT / gen_rel
        up = AAP_REPO_ROOT / up_rel
        if not gen.exists():
            issues.append(f"{ver}: missing {gen_rel}")
            continue
        issues.extend(audit_file(ver, gen, up if up.exists() else None))

    total = len(RPM_CASES) + len(CONTAINERIZED_CASES)
    print(f"Audited {total} inventory files\n")
    if issues:
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("All checks passed:")
    print("  - enabled [all:vars] lines match upstream installer dumps")
    print("  - no True/False/None Ansible convention violations")
    print("  - no enabled vars duplicated in optional catalog")
    print("  - no empty *Configuration section headers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
