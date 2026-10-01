from pathlib import Path

import pytest

from suites.runner import assert_mitigated, load_cases, run_case

CASES = load_cases(Path(__file__).parent / "cases.yaml")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case(case, client, audit_record):
    """Pass = Mitigated; fail = assertion_rule violated (Vulnerable)."""
    trace = run_case(client, case)
    audit_record(case, trace)
    assert_mitigated(case, trace)
