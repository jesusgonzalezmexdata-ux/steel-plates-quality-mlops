"""Packaging metadata stays consistent with the code and the public documentation."""
import importlib
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_cli_entry_point_resolves():
    module, function = PROJECT["scripts"]["steel-predict"].split(":")
    assert callable(getattr(importlib.import_module(module), function))


def test_version_matches_citation_and_changelog():
    version = PROJECT["version"]
    assert f'version: "{version}"' in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_license_metadata_and_files():
    assert PROJECT["license"] == "Apache-2.0"
    assert all((ROOT / name).is_file() for name in PROJECT["license-files"])


def test_runtime_dependencies_are_pinned():
    lines = [l.strip() for l in (ROOT / "requirements.txt").read_text().splitlines() if l.strip()]
    assert lines and all("==" in line for line in lines)
