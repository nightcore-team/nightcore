import pytest


def parse_clause(v: str) -> bool:
    """Check if the clause string is valid (non-empty and contains only positive integers separated by dots)."""  # noqa: E501
    return not (
        not v or any(not x.isdigit() or int(x) <= 0 for x in v.split("."))
    )


@pytest.mark.parametrize(
    "input_str, expected",
    [
        ("1.2.3", True),
        ("0.1", False),
        ("-1.2", False),
        ("1.a", False),
        ("", False),
        ("1", True),
        ("1.wefojewfew.2", False),
        ("1.", False),
        (".1", False),
        (".1.", False),
        ("1.2.3.", False),
        ("1..2", False),
        ("y.y.y", False),
        ("1..2", False),
    ],
)
def test_parse_clause(input_str: str, expected: bool):  # noqa: D103
    assert parse_clause(input_str) is expected
