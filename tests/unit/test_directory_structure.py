"""S00 Bootstrap — Schema directory smoke test.

Verifies that the contracts directory structure exists and is ready for S01.
"""
from pathlib import Path


def test_contracts_directory_exists():
    """packages/contracts/ must exist with __init__.py."""
    contracts_dir = Path(__file__).resolve().parents[2] / "packages" / "contracts"
    assert contracts_dir.exists(), "packages/contracts/ directory missing"
    assert (contracts_dir / "__init__.py").exists(), "packages/contracts/__init__.py missing"


def test_config_directories_exist():
    """configs/{profiles,scenarios,policies} must exist."""
    configs_dir = Path(__file__).resolve().parents[2] / "configs"
    assert (configs_dir / "profiles").exists(), "configs/profiles/ missing"
    assert (configs_dir / "scenarios").exists(), "configs/scenarios/ missing"
    assert (configs_dir / "policies").exists(), "configs/policies/ missing"


def test_validation_directories_exist():
    """validation/{invariants,golden,calibration,reports} must exist."""
    validation_dir = Path(__file__).resolve().parents[2] / "validation"
    assert (validation_dir / "invariants").exists(), "validation/invariants/ missing"
    assert (validation_dir / "golden").exists(), "validation/golden/ missing"
    assert (validation_dir / "calibration").exists(), "validation/calibration/ missing"
    assert (validation_dir / "reports").exists(), "validation/reports/ missing"


def test_docs_architecture_exists():
    """docs/architecture/guardrails.md must exist."""
    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    assert (docs_dir / "architecture" / "guardrails.md").exists()
    assert (docs_dir / "adr" / "0001-single-source-of-truth.md").exists()
    assert (docs_dir / "decisions" / "LOG.md").exists()
