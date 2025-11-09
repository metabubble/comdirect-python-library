"""Data models for the Comdirect API client."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


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
    def from_dict(cls, data: dict) -> "Account":
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
    def from_dict(cls, data: dict) -> "AccountBalance":
        """Create AccountBalance from API response dict."""
        return cls(
            accountId=data["accountId"],
            account=Account.from_dict(data["account"]),
            balance=AmountValue.from_dict(data["balance"]),
            balanceEUR=AmountValue.from_dict(data["balanceEUR"]),
            availableCashAmount=AmountValue.from_dict(data["availableCashAmount"]),
            availableCashAmountEUR=AmountValue.from_dict(data["availableCashAmountEUR"]),
        )


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
    remittanceInfo: Optional[str] = None
    bookingDate: Optional[date] = None
    remitter: Optional[AccountInformation] = None
    debtor: Optional[AccountInformation] = None
    creditor: Optional[AccountInformation] = None
    endToEndReference: Optional[str] = None
    directDebitCreditorId: Optional[str] = None
    directDebitMandateId: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
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

        return cls(
            bookingStatus=data["bookingStatus"],
            amount=amount,
            reference=data["reference"],
            valutaDate=data["valutaDate"],
            transactionType=transaction_type,
            remittanceInfo=data.get("remittanceInfo"),
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
