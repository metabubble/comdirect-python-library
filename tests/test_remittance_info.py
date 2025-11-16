"""Tests for remittanceInfo parsing and Transaction.remittance_lines."""

from typing import Optional

from comdirect_client.models import Transaction


def make_transaction(remittance: Optional[str]) -> Transaction:
    data = {
        "bookingStatus": "BOOKED",
        "reference": "ref",
        "valutaDate": "2020-01-01",
        "newTransaction": False,
        "remittanceInfo": remittance,
    }
    return Transaction.from_dict(data)


def test_remittance_lines_none() -> None:
    tx = make_transaction(None)
    assert tx.remittance_lines == []


def test_remittance_lines_empty_string() -> None:
    tx = make_transaction("")
    assert tx.remittance_lines == []


def test_remittance_lines_single_line_with_marker() -> None:
    tx = make_transaction("01Uebertrag auf Girokonto")
    assert tx.remittance_lines == ["Uebertrag auf Girokonto"]


def test_remittance_lines_multiple_lines_example_one() -> None:
    remittance = "01Uebertrag auf Girokonto 02End-to-End-Ref.: 03nicht angegeben"
    tx = make_transaction(remittance)
    assert tx.remittance_lines == [
        "Uebertrag auf Girokonto",
        "End-to-End-Ref.:",
        "nicht angegeben",
    ]


def test_remittance_lines_multiple_lines_example_two() -> None:
    remittance = "01Globus TS Forchheim//Forchheim/DE 022020-01-03T20:07:16 KFN 0 VJ 1234"
    tx = make_transaction(remittance)
    assert tx.remittance_lines == [
        "Globus TS Forchheim//Forchheim/DE",
        "2020-01-03T20:07:16 KFN 0 VJ 1234",
    ]


def test_remittance_lines_ignores_leading_whitespace_and_empty_parts() -> None:
    remittance = " 01First  02  Second   03   "
    tx = make_transaction(remittance)
    assert tx.remittance_lines == ["First", "Second"]
