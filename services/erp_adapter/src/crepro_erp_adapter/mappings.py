"""Entity field mappings from domain models to ERP doctypes.

This module provides converters for mapping domain entity fields to external ERP
field formats. Each mapping class handles conversion for a specific entity type
(Customer, Invoice, Payment, etc.).
"""

from uuid import UUID


class CustomerMapping:
    """Map domain Customer to ERP Customer doctype."""

    @staticmethod
    def to_erp(payload: dict) -> dict:
        """
        Convert domain customer fields to ERP format.

        Domain fields:
            - name: Customer name
            - email: Email address
            - phone: Phone number
            - type: "person" or "company"
            - tier: Customer tier (Gold, Silver, etc.)
            - region: Geographic region/territory
            - platform_id: UUID for idempotency

        ERP fields (ERPNext-compatible):
            - name: Customer name (auto-numbered by ERP)
            - email_id: Primary email
            - phone: Phone number
            - customer_type: "Individual" or "Company"
            - customer_group: Tier/classification
            - territory: Sales region
            - custom_platform_id: Platform UUID for idempotency
        """
        platform_id = payload.get("platform_id")
        if isinstance(platform_id, UUID):
            platform_id = str(platform_id)

        return {
            "customer_name": payload.get("name"),
            "email_id": payload.get("email"),
            "phone": payload.get("phone"),
            "customer_type": "Individual" if payload.get("type") == "person" else "Company",
            "customer_group": payload.get("tier", "Gold"),
            "territory": payload.get("region"),
            "custom_platform_id": platform_id,
        }


class SupplierMapping:
    """Map domain Vendor to ERP Supplier doctype."""

    @staticmethod
    def to_erp(payload: dict) -> dict:
        """
        Convert domain vendor fields to ERP format.

        Domain fields:
            - name: Vendor name
            - email: Email address
            - phone: Phone number
            - tier: Vendor tier
            - region: Geographic region
            - platform_id: UUID for idempotency

        ERP fields (ERPNext-compatible):
            - supplier_name: Vendor name
            - email_id: Primary email
            - phone: Phone number
            - supplier_type: "Individual" or "Organization"
            - supplier_group: Tier/classification
            - territory: Region
            - custom_platform_id: Platform UUID for idempotency
        """
        platform_id = payload.get("platform_id")
        if isinstance(platform_id, UUID):
            platform_id = str(platform_id)

        return {
            "supplier_name": payload.get("name"),
            "email_id": payload.get("email"),
            "phone": payload.get("phone"),
            "supplier_type": "Individual" if payload.get("type") == "person" else "Organization",
            "supplier_group": payload.get("tier", "Gold"),
            "territory": payload.get("region"),
            "custom_platform_id": platform_id,
        }


class InvoiceMapping:
    """Map domain Invoice/Lease Payment to ERP Sales Invoice doctype."""

    @staticmethod
    def to_erp(payload: dict) -> dict:
        """
        Convert domain invoice fields to ERP format.

        Domain fields:
            - customer_id: Reference to customer (external name/ID)
            - issued_at: Invoice issue date
            - due_date: Payment due date
            - total_amount: Total invoice amount
            - items: List of {product_id, quantity, unit_price, line_amount}
            - invoice_number: Domain invoice identifier
            - platform_id: UUID for idempotency

        ERP fields (ERPNext-compatible):
            - customer: Link to Customer doctype (by external name)
            - posting_date: Invoice date
            - due_date: Due date
            - grand_total: Total amount
            - items: List of {item_code, qty, rate, amount}
            - custom_platform_invoice_id: Domain invoice number
            - custom_platform_id: Platform UUID for idempotency
        """
        platform_id = payload.get("platform_id")
        if isinstance(platform_id, UUID):
            platform_id = str(platform_id)

        items = []
        for item in payload.get("items", []):
            items.append({
                "item_code": item.get("product_id"),
                "qty": item.get("quantity", 1),
                "rate": item.get("unit_price", 0),
                "amount": item.get("line_amount", 0),
            })

        return {
            "customer": payload.get("customer_id"),
            "posting_date": payload.get("issued_at"),
            "due_date": payload.get("due_date"),
            "grand_total": payload.get("total_amount", 0),
            "items": items,
            "custom_platform_invoice_id": payload.get("invoice_number"),
            "custom_platform_id": platform_id,
        }


class PaymentMapping:
    """Map domain Payment to ERP Payment Entry doctype."""

    @staticmethod
    def to_erp(payload: dict) -> dict:
        """
        Convert domain payment fields to ERP format.

        Domain fields:
            - customer_id: Reference to customer
            - amount: Payment amount
            - date: Payment date
            - method: Payment method (Cash, Check, Bank Transfer, etc.)
            - reference_id: External reference (check #, transaction ID, etc.)
            - invoice_id: Link to invoice (optional)
            - platform_id: UUID for idempotency

        ERP fields (ERPNext-compatible):
            - party_type: Always "Customer" for payments received
            - party: Customer link
            - posting_date: Payment date
            - received_amount: Amount received
            - mode_of_payment: Payment method
            - reference_no: External reference
            - custom_platform_id: Platform UUID for idempotency

        Note: Invoice linking is done via journal entry matching in ERP,
        not directly in Payment Entry, so invoice_id is stored as a reference.
        """
        platform_id = payload.get("platform_id")
        if isinstance(platform_id, UUID):
            platform_id = str(platform_id)

        return {
            "party_type": "Customer",
            "party": payload.get("customer_id"),
            "posting_date": payload.get("date"),
            "received_amount": payload.get("amount", 0),
            "mode_of_payment": payload.get("method", "Bank Transfer"),
            "reference_no": payload.get("reference_id"),
            "custom_platform_id": platform_id,
            # Store invoice_id as a custom field for reconciliation
            "custom_invoice_reference": payload.get("invoice_id"),
        }


class DepositMapping:
    """Map domain Deposit to ERP Payment Entry (received) doctype."""

    @staticmethod
    def to_erp(payload: dict) -> dict:
        """
        Convert domain deposit fields to ERP format.

        Deposits are similar to payments but may include additional metadata
        for bank account reconciliation.

        Domain fields:
            - customer_id: Reference to customer
            - amount: Deposit amount
            - date: Deposit date
            - account: Bank account info
            - reference_id: Bank reference/transaction ID
            - platform_id: UUID for idempotency

        ERP fields:
            - party_type: "Customer"
            - party: Customer link
            - posting_date: Deposit date
            - received_amount: Deposit amount
            - mode_of_payment: "Bank Transfer"
            - reference_no: Bank transaction reference
            - custom_platform_id: Platform UUID for idempotency
        """
        platform_id = payload.get("platform_id")
        if isinstance(platform_id, UUID):
            platform_id = str(platform_id)

        return {
            "party_type": "Customer",
            "party": payload.get("customer_id"),
            "posting_date": payload.get("date"),
            "received_amount": payload.get("amount", 0),
            "mode_of_payment": "Bank Transfer",
            "reference_no": payload.get("reference_id"),
            "custom_platform_id": platform_id,
            "custom_deposit_account": payload.get("account"),
        }


class AdjustmentMapping:
    """Map domain Adjustment to ERP Journal Entry doctype."""

    @staticmethod
    def to_erp(payload: dict) -> dict:
        """
        Convert domain adjustment fields to ERP format.

        Adjustments are recorded as journal entries with two legs:
        one to the customer account and one to an expense/income account.

        Domain fields:
            - customer_id: Customer account
            - amount: Adjustment amount (can be negative for reversal)
            - date: Adjustment date
            - description: Reason for adjustment
            - type: "credit" or "debit"
            - account: Expense/income account code
            - platform_id: UUID for idempotency

        ERP fields:
            - posting_date: JE date
            - due_date: Same as posting_date (JE has no due date)
            - remarks: Description
            - accounts: List of two {account, debit_in_account_currency, credit_in_account_currency}
            - custom_platform_id: Platform UUID for idempotency
        """
        platform_id = payload.get("platform_id")
        if isinstance(platform_id, UUID):
            platform_id = str(platform_id)

        amount = payload.get("amount", 0)
        adjustment_type = payload.get("type", "debit")

        # Create two journal entry lines: customer line and account line
        accounts = [
            {
                "account": payload.get("customer_id"),  # Customer account
                "debit_in_account_currency": amount if adjustment_type == "debit" else 0,
                "credit_in_account_currency": amount if adjustment_type == "credit" else 0,
            },
            {
                "account": payload.get("account"),  # Expense/income account
                "debit_in_account_currency": amount if adjustment_type == "credit" else 0,
                "credit_in_account_currency": amount if adjustment_type == "debit" else 0,
            }
        ]

        return {
            "posting_date": payload.get("date"),
            "due_date": payload.get("date"),
            "remarks": payload.get("description"),
            "accounts": accounts,
            "custom_platform_id": platform_id,
        }


# Mapping table: external_doctype -> mapping class
ENTITY_MAPPINGS = {
    "Customer": CustomerMapping,
    "Supplier": SupplierMapping,
    "Sales Invoice": InvoiceMapping,
    "Payment Entry": PaymentMapping,
    "Journal Entry": AdjustmentMapping,
}


def apply_entity_mapping(external_doctype: str, payload: dict) -> dict:
    """
    Apply entity-specific field mapping based on doctype.

    Args:
        external_doctype: ERP doctype name (e.g., "Customer", "Sales Invoice")
        payload: Domain entity payload

    Returns:
        Payload formatted for ERP with all fields mapped and cleaned.
        Returns original payload if doctype not found (fallback).
    """
    mapper_class = ENTITY_MAPPINGS.get(external_doctype)
    if mapper_class:
        try:
            return mapper_class.to_erp(payload)
        except Exception as exc:
            logger.error(f"Error mapping {external_doctype}: {exc}")
            return payload
    return payload


import logging
logger = logging.getLogger(__name__)
