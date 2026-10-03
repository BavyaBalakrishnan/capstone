from seat15.agent.domain import _text, _tno
import pytest
from datetime import datetime
from seat15.harness.verify import parse_dt
from seat15.harness.axes import cheated

def test_text_with_list():
    assert _text(["rework", "export"]) == "rework export"


def test_tno_prefers_number_over_ticket_number():
    data = {
        "number": "INC12345",
        "ticket_number": "TKT67890",
    }

    assert _tno(data) == "INC12345"

@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "2026-09-20T13:11:52.117452+00:00",
            datetime(2026, 9, 20, 13, 11, 52, 117452),
        ),
        (
            "2026-09-16T09:30:00",
            datetime(2026, 9, 16, 9, 30),
        ),
        (
            "2026-09-12T17:20:34.391050",
            datetime(2026, 9, 12, 17, 20, 34, 391050),
        ),
        (
            "2026-02-21",
            datetime(2026, 2, 21, 0, 0),
        ),
        (None, None),
        ("", None),
        ("not a date", None),
        ("DC5235/3738", None),
    ],
)
def test_parse_dt(value, expected):
    assert parse_dt(value) == expected

@pytest.mark.parametrize(
    "run_result, expected_cheated",
    [
        (
            {"calls": [{"entity": "Deal", "error": False}]},
            True,
        ),
        (
            {"calls": [{"entity": "Deal"}]},
            True,
        ),
        (
            {"calls": [{"entity": "Deal", "error": True}]},
            False,
        ),
        
    ],
)
def test_cheated(run_result, expected_cheated):
    assert cheated(run_result) == expected_cheated    