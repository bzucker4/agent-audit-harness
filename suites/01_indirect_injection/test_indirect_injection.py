from pathlib import Path

import pytest

from suites.runner import assert_mitigated, load_cases, run_case

CASES = load_cases(Path(__file__).parent / "cases.yaml")


@pytest.mark.indirect_injection
@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_indirect_injection(case, client, audit_record):
    """Pass = mitigated; fail = vulnerable_if condition satisfied."""
    trace = run_case(client, case)
    audit_record(case, trace)

    assert_mitigated(case, trace)
