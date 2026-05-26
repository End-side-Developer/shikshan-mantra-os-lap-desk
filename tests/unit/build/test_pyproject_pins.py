import tomllib
from pathlib import Path


def test_pyproject_pins():
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    expected_pins = {
        "yamllint": ">=1.35,<2.0",
        "jsonschema": ">=4.21,<5.0",
        "pyyaml": ">=6.0.1,<7.0",
        "polib": ">=1.2,<2.0",
        "pytest": ">=8.0,<9.0",
        "ruff": ">=0.4,<1.0",
    }

    # Parse actual deps into a dict
    actual_pins = {}
    for dep in dev_deps:
        # Simple parsing for the required format (e.g. yamllint>=1.35,<2.0)
        # We find the first character that is not a letter/number/-/_ to split package name
        name = ""
        for i, char in enumerate(dep):
            if char in ">=<~=!":
                name = dep[:i]
                actual_pins[name] = dep[i:]
                break
        if not name:
            actual_pins[dep] = ""

    for req_pkg, req_version in expected_pins.items():
        assert (
            req_pkg in actual_pins
        ), f"Package {req_pkg} not found in dev dependencies array: {dev_deps}"
        assert (
            actual_pins[req_pkg] == req_version
        ), f"Package {req_pkg} version mismatch: expected {req_version}, got {actual_pins[req_pkg]}"


def test_pytest_config():
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    pytest_opts = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
    assert "tests" in pytest_opts.get(
        "testpaths", []
    ), "pytest ini should have 'tests' in testpaths"
    assert "." in pytest_opts.get("pythonpath", []), "pytest ini should have '.' in pythonpath"
    assert "scripts" in pytest_opts.get(
        "pythonpath", []
    ), "pytest ini should have 'scripts' in pythonpath"


def test_ruff_config():
    pyproject_path = Path("pyproject.toml")
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    ruff_opts = data.get("tool", {}).get("ruff", {})
    assert ruff_opts.get("line-length") == 100, "ruff should have line-length 100"
    assert ruff_opts.get("target-version") == "py311", "ruff should have py311 as target-version"
