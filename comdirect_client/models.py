"""Data models for the Comdirect API client."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


@dataclass
class AmountValue:
    """Represents a monetary amount with currency unit."""

    value: Decimal
    unit: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "AmountValue":
        """Create AmountValue from API response dict."""
        return cls(value=Decimal(data["value"]), unit=data["unit"])


@dataclass
class EnumText:
    """Represents an enumerated value with key and text description."""

    key: str
    text: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EnumText":
        """Create EnumText from API response dict."""
        return cls(key=data["key"], text=data["text"])


@dataclass
class AccountInformation:
    """Account information for remitter/debtor/creditor."""

    holderName: str
    iban: Optional[str] = None
    bic: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "AccountInformation":
        """Create AccountInformation from API response dict."""
        return cls(holderName=data["holderName"], iban=data.get("iban"), bic=data.get("bic"))


@dataclass
class Account:
    """Account master data."""

    accountId: str
    accountDisplayId: str
    currency: str
    clientId: str
    accountType: EnumText
    iban: Optional[str] = None
    bic: Optional[str] = None
    creditLimit: Optional[AmountValue] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Account":
        """Create Account from API response dict."""
        return cls(
            accountId=data["accountId"],
            accountDisplayId=data["accountDisplayId"],
            currency=data["currency"],
            clientId=data["clientId"],
            accountType=EnumText.from_dict(data["accountType"]),
            iban=data.get("iban"),
            bic=data.get("bic"),
            creditLimit=(
                AmountValue.from_dict(data["creditLimit"]) if "creditLimit" in data else None
            ),
        )


@dataclass
class AccountBalance:
    """Account balance information."""

    accountId: str
    account: Account
    balance: AmountValue
    balanceEUR: AmountValue
    availableCashAmount: AmountValue
    availableCashAmountEUR: AmountValue

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccountBalance":
        """Create AccountBalance from API response dict."""
        return cls(
            accountId=data["accountId"],
            account=Account.from_dict(data["account"]),
            balance=AmountValue.from_dict(data["balance"]),
            balanceEUR=AmountValue.from_dict(data["balanceEUR"]),
            availableCashAmount=AmountValue.from_dict(data["availableCashAmount"]),
            availableCashAmountEUR=AmountValue.from_dict(data["availableCashAmountEUR"]),
        )


def _parse_remittance_info(remittance: Optional[str]) -> list[str]:
    """Parse Comdirect remittanceInfo string into logical lines.

    The Comdirect API encodes line breaks in remittanceInfo by prefixing each
    logical line with a two-digit sequence number ("01", "02", ...).

    Two formats are supported:
    1. Long format (real API data): Markers at ~37-char intervals
    2. Short format (test data): Markers with variable/close spacing

    This function adapts to detect which format is used and extracts lines accordingly.
    """

    if not remittance:
        return []

    text = remittance.strip()
    if not text:
        return []

    length = len(text)

    # Find the first marker (01)
    first_pos = -1
    if length >= 2 and text[0:2] == "01":
        first_pos = 0
    else:
        for i in range(length - 2):
            if text[i].isspace() and text[i + 1 : i + 3] == "01":
                first_pos = i + 1
                break

    if first_pos == -1:
        # No valid starting marker – treat entire string as single line
        return [text]

    # Detect format based on total length and marker spacing
    # Long format typically has 37-char intervals and total length > 100
    # Short format has variable/close spacing and total length < 100
    is_long_format = length > 100

    marker_positions: list[int] = [first_pos]
    expected_marker = 2

    if is_long_format:
        # Long format: use spacing heuristic with tolerance
        expected_pos = first_pos + 37
        tolerance = 15

        while expected_marker <= 99:
            found = False
            search_start = max(marker_positions[-1] + 20, expected_pos - tolerance)
            search_end = min(length - 1, expected_pos + tolerance)

            for pos in range(search_start, search_end):
                if pos + 1 < length and text[pos].isdigit() and text[pos + 1].isdigit():
                    marker_value = int(text[pos : pos + 2])
                    if marker_value == expected_marker:
                        marker_positions.append(pos)
                        expected_pos = pos + 37
                        expected_marker += 1
                        found = True
                        break

            if not found:
                break
    else:
        # Short format: scan for markers that appear after whitespace
        # This avoids false positives in timestamps like "2020-01-03T20:07:16"
        while expected_marker <= 99:
            found = False
            search_start = marker_positions[-1] + 2

            for pos in range(search_start, length - 1):
                # Marker must be after whitespace (not in middle of numbers/text)
                if (
                    text[pos].isdigit()
                    and text[pos + 1].isdigit()
                    and (pos == 0 or text[pos - 1].isspace())
                ):
                    marker_value = int(text[pos : pos + 2])
                    if marker_value == expected_marker:
                        marker_positions.append(pos)
                        expected_marker += 1
                        found = True
                        break

            if not found:
                break

    # Extract lines between markers
    lines: list[str] = []
    for idx, pos in enumerate(marker_positions):
        start = pos + 2  # skip the two-digit marker
        end = marker_positions[idx + 1] if idx + 1 < len(marker_positions) else length
        line = text[start:end].strip()
        if line:
            lines.append(line)

    return lines if lines else [text]


@dataclass
class Transaction:
    """Bank account transaction.

    Note: The Comdirect API Swagger spec contains a typo where the field "debtor"
    is documented as "deptor" (line 354 in API spec v20.04). This implementation
    uses the correct field name "debtor". If the live API returns "deptor",
    add fallback logic in from_dict() method.
    """

    bookingStatus: str
    reference: str
    valutaDate: str
    newTransaction: bool
    amount: Optional[AmountValue] = None
    transactionType: Optional[EnumText] = None
    remittanceLines: list[str] = field(default_factory=list)
    bookingDate: Optional[date] = None

    remitter: Optional[AccountInformation] = None
    debtor: Optional[AccountInformation] = None
    creditor: Optional[AccountInformation] = None
    endToEndReference: Optional[str] = None
    directDebitCreditorId: Optional[str] = None
    directDebitMandateId: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        """Create Transaction from API response dict."""
        booking_date = None
        if data.get("bookingDate"):
            booking_date = date.fromisoformat(data["bookingDate"])

        # Handle optional nested objects safely
        amount = None
        if data.get("amount"):
            amount = AmountValue.from_dict(data["amount"])

        transaction_type = None
        if data.get("transactionType"):
            transaction_type = EnumText.from_dict(data["transactionType"])

        remittance_lines = _parse_remittance_info(data.get("remittanceInfo"))

        return cls(
            bookingStatus=data["bookingStatus"],
            amount=amount,
            reference=data["reference"],
            valutaDate=data["valutaDate"],
            transactionType=transaction_type,
            remittanceLines=remittance_lines,
            newTransaction=data["newTransaction"],
            bookingDate=booking_date,
            remitter=(
                AccountInformation.from_dict(data["remitter"]) if data.get("remitter") else None
            ),
            debtor=(
                AccountInformation.from_dict(data.get("debtor") or data.get("deptor", {}))
                if data.get("debtor") or data.get("deptor")
                else None
            ),
            creditor=(
                AccountInformation.from_dict(data["creditor"]) if data.get("creditor") else None
            ),
            endToEndReference=data.get("endToEndReference"),
            directDebitCreditorId=data.get("directDebitCreditorId"),
            directDebitMandateId=data.get("directDebitMandateId"),
        )

    @property
    def remittance_lines(self) -> list[str]:
        """Return remittance lines for this transaction.

        The raw `remittanceInfo` string from the API is parsed once in
        `from_dict` into `remittanceLines`. This property simply returns
        that list.
        """

        return self.remittanceLines
