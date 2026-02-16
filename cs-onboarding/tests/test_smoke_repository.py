from pathlib import Path
import re


def test_blueprints_directory_exists():
    blueprints_dir = Path("backend/project/blueprints")
    assert blueprints_dir.exists()
    assert blueprints_dir.is_dir()


def test_route_decorators_are_present():
    blueprints_dir = Path("backend/project/blueprints")
    route_pattern = re.compile(r"@\w+\.route\(")

    route_count = 0
    for py_file in blueprints_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        route_count += len(route_pattern.findall(text))

    # Smoke threshold to detect accidental mass-removal of routes.
    assert route_count >= 50
