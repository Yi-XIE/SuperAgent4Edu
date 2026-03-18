"""File-level contracts for run result and blueprint/package object APIs."""

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_schema_contains_blueprint_package_and_result_contracts():
    content = _read(_repo_root() / "backend" / "src" / "education" / "schemas.py")
    assert "class CreateCourseBlueprintRequest" in content
    assert "class CreateCoursePackageRequest" in content
    assert "class EducationRunResult" in content
    assert "artifact_paths" in content
    assert "extraction_candidates" in content
    assert "extracted_assets" in content


def test_router_has_blueprint_package_endpoints():
    blueprints = _read(_repo_root() / "backend" / "src" / "gateway" / "routers" / "education_blueprints.py")
    packages = _read(_repo_root() / "backend" / "src" / "gateway" / "routers" / "education_packages.py")
    assert 'prefix="/api/education/blueprints"' in blueprints
    assert "@router.get" in blueprints
    assert "@router.post" in blueprints
    assert 'prefix="/api/education/packages"' in packages
    assert "@router.get" in packages
    assert "@router.post" in packages


def test_runs_router_has_result_aggregation_endpoint():
    runs = _read(_repo_root() / "backend" / "src" / "gateway" / "routers" / "education_runs.py")
    assert '@router.get("/{run_id}/result"' in runs
    assert "response_model=EducationRunResult" in runs
    assert "blueprint_not_found" in runs
    assert "package_not_found" in runs
    assert "artifact_missing:" in runs
    assert "parse_errors" in runs
