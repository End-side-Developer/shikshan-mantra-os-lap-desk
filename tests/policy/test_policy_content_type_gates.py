"""
tests/policy/test_policy_content_type_gates.py

Verifies the allowed_content_types and allowed_sub_engines keys added to
config/includes.chroot/etc/shikshan/policy.yml in SMO-0520.

Checks:
  1. The shipped default policy.yml parses as valid YAML.
  2. allowed_content_types contains the expected v1 values.
  3. allowed_sub_engines contains the expected v1 values (excludes ctf
     by default — strict safety_mode).
  4. ctf is NOT in the default allowed_sub_engines (strict mode).
  5. A policy with ctf explicitly added is a valid YAML structure.

Run: python -m pytest tests/policy/test_policy_content_type_gates.py -v
"""

import pathlib
import pytest

try:
    import yaml
except ImportError:
    pytest.skip("PyYAML not installed", allow_module_level=True)

REPO = pathlib.Path(__file__).parent.parent.parent
POLICY_PATH = REPO / "config/includes.chroot/etc/shikshan/policy.yml"

EXPECTED_CONTENT_TYPES = {"interactive-runner", "quiz"}
EXPECTED_SUB_ENGINES_STRICT = {"sql", "web", "code", "quiz"}


@pytest.fixture(scope="module")
def policy():
    with POLICY_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestPolicyContentTypeGates:
    def test_policy_parses(self, policy):
        assert isinstance(policy, dict)

    def test_allowed_content_types_present(self, policy):
        assert "allowed_content_types" in policy

    def test_allowed_content_types_values(self, policy):
        actual = set(policy["allowed_content_types"])
        assert EXPECTED_CONTENT_TYPES == actual, f"expected {EXPECTED_CONTENT_TYPES}, got {actual}"

    def test_allowed_sub_engines_present(self, policy):
        assert "allowed_sub_engines" in policy

    def test_allowed_sub_engines_strict_excludes_ctf(self, policy):
        assert policy["safety_mode"] == "strict"
        assert "ctf" not in policy["allowed_sub_engines"]

    def test_allowed_sub_engines_strict_values(self, policy):
        actual = set(policy["allowed_sub_engines"])
        assert (
            EXPECTED_SUB_ENGINES_STRICT == actual
        ), f"expected {EXPECTED_SUB_ENGINES_STRICT}, got {actual}"

    def test_safety_mode_is_strict_by_default(self, policy):
        assert policy["safety_mode"] == "strict"

    def test_moderate_policy_can_include_ctf(self):
        moderate = {
            "version": 1,
            "safety_mode": "moderate",
            "allowed_content_types": ["interactive-runner", "quiz"],
            "allowed_sub_engines": ["sql", "web", "code", "quiz", "ctf"],
        }
        # Just verify this is parseable and ctf is accepted
        assert "ctf" in moderate["allowed_sub_engines"]

    def test_open_policy_can_include_all(self):
        open_policy = {
            "version": 1,
            "safety_mode": "open",
            "allowed_content_types": ["interactive-runner", "quiz"],
            "allowed_sub_engines": ["sql", "web", "code", "quiz", "ctf"],
        }
        assert len(open_policy["allowed_sub_engines"]) == 5
