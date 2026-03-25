"""
Salesforce Service Layer — API integration for Inventory Units, Payments, Receipts.

Supports:
- Reading unit details and payment schedules
- Updating payment status (Amount_Paid__c)
- Creating receipts and invoices
- Sending emails with attachments via SF SingleEmailMessage
- Activity logging on unit records

Safety:
- SF_WRITE_MODE must be True for any write operations (default: False)
- EMAIL_LIVE_MODE must be True for actual email sending (default: False)
- All write operations return simulated results when in dry-run mode
"""

import os
import json
import base64
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
    HAS_SIMPLE_SF = True
except ImportError:
    HAS_SIMPLE_SF = False


# ---------------------------------------------------------------------------
# Configuration (from env vars)
# ---------------------------------------------------------------------------
SF_INSTANCE_URL = "momentum-ability-3447.my.salesforce.com"
SF_CLIENT_ID = os.environ.get("SF_CLIENT_ID", "")
SF_CLIENT_SECRET = os.environ.get("SF_CLIENT_SECRET", "")
SF_USERNAME = os.environ.get("SF_USERNAME", "")
SF_PASSWORD = os.environ.get("SF_PASSWORD", "")
SF_SECURITY_TOKEN = os.environ.get("SF_SECURITY_TOKEN", "")

# Safety flags
SF_WRITE_MODE = os.environ.get("SF_WRITE_MODE", "false").lower() == "true"
EMAIL_LIVE_MODE = os.environ.get("EMAIL_LIVE_MODE", "false").lower() == "true"


@dataclass
class SFUnit:
    """A Salesforce Inventory Unit record."""
    sf_id: str = ""
    unit_name: str = ""          # e.g., "201"
    project_name: str = ""       # e.g., "CENTURY"
    building_name: str = ""
    price: float = 0.0
    status: str = ""             # Handover, Pre-Sold, etc.
    purchaser_name: str = ""
    purchaser_email: str = ""
    booking_id: str = ""
    fam_deal_id: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class SFPayment:
    """A Salesforce Booking Payment record."""
    sf_id: str = ""
    name: str = ""               # BP-03037
    unit_name: str = ""
    project_name: str = ""
    payment_type: str = ""       # Down Payment, Q1, Q2, etc.
    amount_due: float = 0.0      # Amount_New__c or Sub_Total__c
    amount_paid: float = 0.0     # Amount_Paid__c
    remaining: float = 0.0       # Remaining_Amount__c (formula)
    sub_total: float = 0.0       # Sub_Total__c (formula)
    status: str = ""             # Paid, Partially Paid, Overdue, Unpaid
    payment_status: str = ""     # Payment_Status__c picklist
    due_date: str = ""
    sequence: int = 0
    invoice_id: str = ""
    booking_id: str = ""
    inventory_id: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class SFActionResult:
    """Result of a Salesforce action (real or simulated)."""
    action: str = ""             # "update_payment", "create_receipt", "send_email"
    target: str = ""             # e.g., "BP-03037" or "Unit 201"
    success: bool = False
    dry_run: bool = True         # True = simulated, False = actually executed
    message: str = ""
    data: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class SalesforceService:
    """
    Salesforce API service for payment operations.
    All write operations respect SF_WRITE_MODE and EMAIL_LIVE_MODE flags.
    """

    def __init__(self):
        self._sf: Optional[Salesforce] = None
        self._connected = False
        self._error = ""

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Establish connection to Salesforce."""
        if not HAS_SIMPLE_SF:
            self._error = "simple-salesforce not installed"
            return False

        if not all([SF_CLIENT_ID, SF_USERNAME, SF_PASSWORD]):
            self._error = "Missing SF credentials (SF_CLIENT_ID, SF_USERNAME, SF_PASSWORD)"
            return False

        try:
            self._sf = Salesforce(
                username=SF_USERNAME,
                password=SF_PASSWORD,
                security_token=SF_SECURITY_TOKEN,
                consumer_key=SF_CLIENT_ID,
                consumer_secret=SF_CLIENT_SECRET,
                domain="login",  # use "test" for sandbox
            )
            self._connected = True
            return True
        except SalesforceAuthenticationFailed as e:
            self._error = f"SF auth failed: {e}"
            return False
        except Exception as e:
            self._error = f"SF connection error: {e}"
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._sf is not None

    @property
    def connection_error(self) -> str:
        return self._error

    def _ensure_connected(self):
        if not self.is_connected:
            self.connect()
        if not self.is_connected:
            raise ConnectionError(f"Cannot connect to Salesforce: {self._error}")

    # ------------------------------------------------------------------
    # READ: Unit Details
    # ------------------------------------------------------------------

    def get_unit_details(self, unit_name: str, project_name: str = None) -> Optional[SFUnit]:
        """Get inventory unit details including purchaser info."""
        self._ensure_connected()

        query = f"""
            SELECT Id, Name, Project__r.Name, Building_Name_Formula__c,
                   Price__c, Status__c, Account_name__c, Account_1_email__c,
                   Booking__c, Fam_Deal_ID__c
            FROM Inventory_Unit__c
            WHERE Name = '{unit_name}'
        """
        if project_name:
            query += f" AND Project__r.Name = '{project_name}'"
        query += " LIMIT 1"

        result = self._sf.query(query)
        if not result["records"]:
            return None

        r = result["records"][0]
        return SFUnit(
            sf_id=r["Id"],
            unit_name=r["Name"],
            project_name=r.get("Project__r", {}).get("Name", "") if r.get("Project__r") else "",
            building_name=r.get("Building_Name_Formula__c", ""),
            price=float(r.get("Price__c", 0) or 0),
            status=r.get("Status__c", ""),
            purchaser_name=r.get("Account_name__c", ""),
            purchaser_email=r.get("Account_1_email__c", ""),
            booking_id=r.get("Booking__c", ""),
            fam_deal_id=str(r.get("Fam_Deal_ID__c", "")),
        )

    def get_all_project_units(self, project_name: str) -> list[SFUnit]:
        """Get all inventory units for a project with purchaser info."""
        self._ensure_connected()

        query = f"""
            SELECT Id, Name, Project__r.Name, Building_Name_Formula__c,
                   Price__c, Status__c, Account_name__c, Account_1_email__c,
                   Booking__c, Fam_Deal_ID__c
            FROM Inventory_Unit__c
            WHERE Project__r.Name = '{project_name}'
            ORDER BY Name
        """
        result = self._sf.query_all(query)
        units = []
        for r in result["records"]:
            units.append(SFUnit(
                sf_id=r["Id"],
                unit_name=r["Name"],
                project_name=r.get("Project__r", {}).get("Name", "") if r.get("Project__r") else "",
                building_name=r.get("Building_Name_Formula__c", ""),
                price=float(r.get("Price__c", 0) or 0),
                status=r.get("Status__c", ""),
                purchaser_name=r.get("Account_name__c", ""),
                purchaser_email=r.get("Account_1_email__c", ""),
                booking_id=r.get("Booking__c", ""),
                fam_deal_id=str(r.get("Fam_Deal_ID__c", "")),
            ))
        return units

    # ------------------------------------------------------------------
    # READ: Payment Schedule
    # ------------------------------------------------------------------

    def get_unit_payments(self, unit_name: str, project_name: str = None) -> list[SFPayment]:
        """Get all booking payments for a unit, ordered by sequence."""
        self._ensure_connected()

        query = f"""
            SELECT Id, Name, Inventory__r.Name, Project__r.Name,
                   Payment_Type__c, Amount_New__c, Amount_Paid__c,
                   Remaining_Amount__c, Sub_Total__c, Status__c,
                   Payment_Status__c, Due_Date__c, Sequence__c,
                   Invoice__c, Booking__c, Inventory__c
            FROM Booking_Payment__c
            WHERE Inventory__r.Name = '{unit_name}'
        """
        if project_name:
            query += f" AND Project__r.Name = '{project_name}'"
        query += " ORDER BY Sequence__c ASC"

        result = self._sf.query_all(query)
        payments = []
        for r in result["records"]:
            payments.append(SFPayment(
                sf_id=r["Id"],
                name=r["Name"],
                unit_name=r.get("Inventory__r", {}).get("Name", "") if r.get("Inventory__r") else "",
                project_name=r.get("Project__r", {}).get("Name", "") if r.get("Project__r") else "",
                payment_type=r.get("Payment_Type__c", ""),
                amount_due=float(r.get("Amount_New__c", 0) or 0),
                amount_paid=float(r.get("Amount_Paid__c", 0) or 0),
                remaining=float(r.get("Remaining_Amount__c", 0) or 0),
                sub_total=float(r.get("Sub_Total__c", 0) or 0),
                status=r.get("Status__c", ""),
                payment_status=r.get("Payment_Status__c", ""),
                due_date=r.get("Due_Date__c", ""),
                sequence=int(r.get("Sequence__c", 0) or 0),
                invoice_id=r.get("Invoice__c", "") or "",
                booking_id=r.get("Booking__c", "") or "",
                inventory_id=r.get("Inventory__c", "") or "",
            ))
        return payments

    def get_unpaid_payments(self, unit_name: str, project_name: str = None) -> list[SFPayment]:
        """Get only unpaid/partially paid/overdue payments for a unit."""
        all_payments = self.get_unit_payments(unit_name, project_name)
        return [p for p in all_payments if p.status not in ("Paid",) and p.remaining > 0]

    def get_project_payment_summary(self, project_name: str) -> dict:
        """Get summary of all payments for a project (for KB building)."""
        self._ensure_connected()

        query = f"""
            SELECT Inventory__r.Name, Payment_Type__c, Amount_New__c,
                   Amount_Paid__c, Remaining_Amount__c, Sub_Total__c,
                   Status__c, Due_Date__c, Sequence__c, Id, Name
            FROM Booking_Payment__c
            WHERE Project__r.Name = '{project_name}'
              AND Status__c != 'Paid'
              AND Payment_Cancelled__c = false
            ORDER BY Inventory__r.Name, Sequence__c
        """
        result = self._sf.query_all(query)

        by_unit = {}
        for r in result["records"]:
            unit = r.get("Inventory__r", {}).get("Name", "") if r.get("Inventory__r") else ""
            if not unit:
                continue
            if unit not in by_unit:
                by_unit[unit] = []
            by_unit[unit].append({
                "sf_id": r["Id"],
                "name": r["Name"],
                "type": r.get("Payment_Type__c", ""),
                "amount_due": float(r.get("Amount_New__c", 0) or 0),
                "sub_total": float(r.get("Sub_Total__c", 0) or 0),
                "remaining": float(r.get("Remaining_Amount__c", 0) or 0),
                "status": r.get("Status__c", ""),
                "due_date": r.get("Due_Date__c", ""),
            })

        return {
            "project": project_name,
            "units_with_outstanding": len(by_unit),
            "total_records": result["totalSize"],
            "by_unit": by_unit,
        }

    # ------------------------------------------------------------------
    # READ: Available Projects
    # ------------------------------------------------------------------

    def get_available_projects(self) -> list[str]:
        """Get list of project names that have inventory units."""
        self._ensure_connected()
        query = """
            SELECT Project__r.Name, COUNT(Id) cnt
            FROM Inventory_Unit__c
            WHERE Project__r.Name != null
            GROUP BY Project__r.Name
            ORDER BY Project__r.Name
        """
        result = self._sf.query(query)
        return [r["Project__r"]["Name"] for r in result["records"] if r.get("Project__r")]

    # ------------------------------------------------------------------
    # WRITE: Update Payment Status
    # ------------------------------------------------------------------

    def update_payment_amount_paid(
        self, booking_payment_id: str, new_amount_paid: float, notes: str = ""
    ) -> SFActionResult:
        """
        Update Amount_Paid__c on a Booking_Payment__c record.
        Status__c and Remaining_Amount__c are formula fields — they auto-recalculate.
        """
        action = SFActionResult(
            action="update_payment",
            target=booking_payment_id,
        )

        if not SF_WRITE_MODE:
            action.dry_run = True
            action.success = True
            action.message = f"DRY RUN: Would update Amount_Paid__c to {new_amount_paid:.2f}"
            action.data = {"amount_paid": new_amount_paid, "notes": notes}
            return action

        try:
            self._ensure_connected()
            update_data = {"Amount_Paid__c": new_amount_paid}
            if notes:
                update_data["Payment_Detail__c"] = notes

            self._sf.Booking_Payment__c.update(booking_payment_id, update_data)
            action.dry_run = False
            action.success = True
            action.message = f"Updated Amount_Paid__c to {new_amount_paid:.2f}"
            action.data = update_data
        except Exception as e:
            action.success = False
            action.message = f"Error: {e}"

        return action

    # ------------------------------------------------------------------
    # WRITE: Create Receipt
    # ------------------------------------------------------------------

    def create_receipt_record(
        self,
        inventory_id: str,
        amount: float,
        payment_type: str,
        payment_date: str,
        reference: str,
        receipt_number: str = "",
    ) -> SFActionResult:
        """Create a Receipt record linked to an Inventory Unit."""
        action = SFActionResult(
            action="create_receipt",
            target=f"Receipt for {inventory_id}",
        )

        if not SF_WRITE_MODE:
            action.dry_run = True
            action.success = True
            action.message = f"DRY RUN: Would create receipt — AED {amount:,.2f} ({payment_type})"
            action.data = {
                "inventory_id": inventory_id,
                "amount": amount,
                "payment_type": payment_type,
                "date": payment_date,
                "reference": reference,
            }
            return action

        try:
            self._ensure_connected()
            # Note: The exact Receipt object API name needs to be confirmed
            # It may be Receipt__c or similar based on the org setup
            receipt_data = {
                "Inventory__c": inventory_id,
                "Amount__c": amount,
                "Payment_Type__c": payment_type,
                "Date__c": payment_date,
                "Reference__c": reference,
            }
            if receipt_number:
                receipt_data["Name"] = receipt_number

            result = self._sf.Receipt__c.create(receipt_data)
            action.dry_run = False
            action.success = True
            action.message = f"Created receipt: {result.get('id', 'unknown')}"
            action.data = {"receipt_id": result.get("id", "")}
        except Exception as e:
            action.success = False
            action.message = f"Error creating receipt: {e}"

        return action

    # ------------------------------------------------------------------
    # WRITE: Send Email via Salesforce
    # ------------------------------------------------------------------

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        pdf_attachments: list[dict] = None,
        related_to_id: str = None,
    ) -> SFActionResult:
        """
        Send email via Salesforce SingleEmailMessage API.
        pdf_attachments: list of {"filename": "receipt.pdf", "body_bytes": b"..."}
        """
        action = SFActionResult(
            action="send_email",
            target=to_email,
        )

        if not EMAIL_LIVE_MODE:
            action.dry_run = True
            action.success = True
            attachment_names = [a["filename"] for a in (pdf_attachments or [])]
            action.message = (
                f"DRY RUN: Would send email to {to_email} — "
                f"Subject: {subject} — Attachments: {attachment_names}"
            )
            action.data = {
                "to": to_email,
                "subject": subject,
                "body_preview": body[:200],
                "attachments": attachment_names,
            }
            return action

        try:
            self._ensure_connected()

            email_data = {
                "toAddresses": [to_email],
                "subject": subject,
                "plainTextBody": body,
                "saveAsActivity": True,
            }

            if related_to_id:
                email_data["whatId"] = related_to_id

            # Handle PDF attachments
            if pdf_attachments:
                file_attachments = []
                for att in pdf_attachments:
                    file_attachments.append({
                        "fileName": att["filename"],
                        "body": base64.b64encode(att["body_bytes"]).decode("utf-8"),
                        "contentType": "application/pdf",
                    })
                email_data["fileAttachments"] = file_attachments

            # Use Salesforce REST API to send email
            url = f"{self._sf.base_url}actions/standard/emailSimple"
            payload = {
                "inputs": [{
                    "emailAddresses": to_email,
                    "emailSubject": subject,
                    "emailBody": body,
                    "senderType": "CurrentUser",
                }]
            }
            resp = self._sf._call_salesforce("POST", url, data=json.dumps(payload))

            action.dry_run = False
            action.success = True
            action.message = f"Email sent to {to_email}"
        except Exception as e:
            action.success = False
            action.message = f"Error sending email: {e}"

        return action

    # ------------------------------------------------------------------
    # WRITE: Log Activity on Unit
    # ------------------------------------------------------------------

    def log_activity(
        self, unit_sf_id: str, subject: str, description: str
    ) -> SFActionResult:
        """Create a Task (activity) on an Inventory Unit record."""
        action = SFActionResult(
            action="log_activity",
            target=unit_sf_id,
        )

        if not SF_WRITE_MODE:
            action.dry_run = True
            action.success = True
            action.message = f"DRY RUN: Would log activity — {subject}"
            action.data = {"subject": subject, "description": description[:200]}
            return action

        try:
            self._ensure_connected()
            task_data = {
                "WhatId": unit_sf_id,
                "Subject": subject,
                "Description": description,
                "Status": "Completed",
                "ActivityDate": datetime.now().strftime("%Y-%m-%d"),
            }
            result = self._sf.Task.create(task_data)
            action.dry_run = False
            action.success = True
            action.message = f"Activity logged: {result.get('id', '')}"
        except Exception as e:
            action.success = False
            action.message = f"Error logging activity: {e}"

        return action

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def identify_installments_for_amount(
        self, unit_name: str, bank_amount: float, project_name: str = None, tolerance: float = 100
    ) -> list[dict]:
        """
        Given a bank transaction amount, identify which installment(s) it covers.
        Handles: exact match, split payments (2-3 installments), partial payments.
        Returns list of {"payment": SFPayment, "allocated_amount": float, "match_type": str}
        """
        unpaid = self.get_unpaid_payments(unit_name, project_name)
        if not unpaid:
            return []

        results = []

        # 1. Exact match — bank amount matches one installment's remaining
        for p in unpaid:
            if abs(bank_amount - p.remaining) <= tolerance:
                return [{"payment": p, "allocated_amount": p.remaining, "match_type": "exact"}]
            if abs(bank_amount - p.sub_total) <= tolerance:
                return [{"payment": p, "allocated_amount": p.sub_total, "match_type": "exact_subtotal"}]

        # 2. Split payment — bank amount = sum of 2-3 consecutive unpaid installments
        for i in range(len(unpaid)):
            cumulative = 0.0
            batch = []
            for j in range(i, min(i + 4, len(unpaid))):  # Check up to 4 consecutive
                cumulative += unpaid[j].remaining
                batch.append(unpaid[j])
                if abs(cumulative - bank_amount) <= tolerance:
                    return [
                        {"payment": p, "allocated_amount": p.remaining, "match_type": "split"}
                        for p in batch
                    ]

        # 3. Partial payment — bank amount < smallest remaining
        for p in unpaid:
            if bank_amount < p.remaining and bank_amount > 0:
                return [{"payment": p, "allocated_amount": bank_amount, "match_type": "partial"}]

        return []

    def get_status(self) -> dict:
        """Return current service status."""
        return {
            "connected": self.is_connected,
            "error": self._error,
            "write_mode": SF_WRITE_MODE,
            "email_live_mode": EMAIL_LIVE_MODE,
            "has_credentials": bool(SF_CLIENT_ID and SF_USERNAME),
            "instance": SF_INSTANCE_URL,
        }
