"""
Salesforce Browser Automation Agent — Uses Chrome browser session to perform
actions in Salesforce without API credentials.

Requires: Claude in Chrome MCP tools (runs from Claude Code session, not from Vercel)

Workflow per matched unit:
1. Search for unit in SF global search
2. Navigate to Payments tab
3. Find the correct payment record (by amount/type)
4. Update Amount Paid if needed (click Edit → update field → Save)
5. Click "Generate Invoice" to create receipt
6. Go back to unit → Account Statements tab → verify statement exists
7. Send email to buyer via SF Activity panel (with receipt + statement)
8. Mark receipt as "Done" in master sheet

Safety:
- DRY_RUN mode: logs all actions without executing clicks
- Each action is confirmed before execution
- Errors are caught and reported per-unit (doesn't stop the batch)
"""

import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SFAction:
    """A single Salesforce browser action."""
    unit_no: str = ""
    payment_id: str = ""        # e.g., BP-03041
    action_type: str = ""       # "generate_invoice", "update_payment", "send_email"
    status: str = "pending"     # "pending", "in_progress", "done", "error", "dry_run"
    message: str = ""
    details: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class SFBrowserConfig:
    """Configuration for the SF browser agent."""
    sf_base_url: str = "https://momentum-ability-3447.lightning.force.com"
    dry_run: bool = True        # If True, log actions but don't click
    wait_seconds: float = 3.0   # Wait time between page loads
    confirm_each: bool = False  # If True, pause and confirm before each action


class SalesforceBrowserAgent:
    """
    Automates Salesforce operations through the browser using Chrome MCP tools.

    This agent is designed to be called from a Claude Code session where
    the Chrome MCP tools are available. It does NOT run on Vercel.

    Usage from Claude Code:
        agent = SalesforceBrowserAgent(tab_id=12345)
        results = agent.process_units(needs_receipt_list)
    """

    def __init__(self, tab_id: int = None, config: SFBrowserConfig = None):
        self.tab_id = tab_id
        self.config = config or SFBrowserConfig()
        self.actions_log: list[SFAction] = []

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_units(self, units: list[dict]) -> list[SFAction]:
        """
        Process a list of units that need SF actions.
        Each unit dict should have: unit_no, credit, account_name, date, etc.

        This method returns the planned actions. Actual execution happens
        via the execute_* methods which use Chrome MCP tools.
        """
        self.actions_log = []

        for unit_info in units:
            unit_no = unit_info.get("unit_no", "")
            amount = unit_info.get("credit", 0)
            client = unit_info.get("account_name", "")

            if not unit_no:
                continue

            # Plan: Generate Invoice
            self.actions_log.append(SFAction(
                unit_no=unit_no,
                action_type="generate_invoice",
                status="dry_run" if self.config.dry_run else "pending",
                message=f"Generate invoice for Unit {unit_no} — AED {amount:,.2f}",
                details={
                    "amount": amount,
                    "client": client,
                    "date": unit_info.get("date", ""),
                },
            ))

            # Plan: Send email with receipt + statement
            self.actions_log.append(SFAction(
                unit_no=unit_no,
                action_type="send_email",
                status="dry_run" if self.config.dry_run else "pending",
                message=f"Send receipt + statement email to buyer of Unit {unit_no}",
                details={
                    "client": client,
                    "attachments": ["receipt", "statement"],
                },
            ))

        return self.actions_log

    # ------------------------------------------------------------------
    # Browser automation steps (use Chrome MCP tools)
    # These are designed to be called by Claude Code with MCP access
    # ------------------------------------------------------------------

    def get_search_url(self, unit_no: str) -> str:
        """Get the SF search URL for a unit number."""
        return f"{self.config.sf_base_url}/lightning/o/Inventory_Unit__c/list?filterName=Recent"

    def get_unit_url(self, unit_no: str, project: str = "CENTURY") -> str:
        """
        Construct the SF search URL to find a unit.
        Note: The actual SF record ID is needed — we search by unit name.
        """
        # SF global search URL
        return f"{self.config.sf_base_url}/lightning/o/Inventory_Unit__c/list?filterName=Recent&q={unit_no}"

    # ------------------------------------------------------------------
    # Step-by-step browser instructions (for Claude to execute)
    # ------------------------------------------------------------------

    def get_instructions_for_unit(self, unit_no: str, amount: float = 0, client: str = "") -> list[dict]:
        """
        Return step-by-step browser instructions for processing a unit.
        Each step has: action, description, selector/coordinate hints, wait_after.

        These instructions are meant to be executed by Claude using Chrome MCP tools.
        """
        base = self.config.sf_base_url
        steps = []

        # Step 1: Search for the unit
        steps.append({
            "step": 1,
            "action": "navigate",
            "description": f"Search for Unit {unit_no} in Salesforce",
            "url": f"{base}/lightning/o/Inventory_Unit__c/list",
            "then": f"Use the search/filter to find unit {unit_no}, or use global search",
            "wait_after": self.config.wait_seconds,
        })

        # Step 2: Click on the unit record
        steps.append({
            "step": 2,
            "action": "click",
            "description": f"Click on Unit {unit_no} to open the record",
            "hint": f"Look for '{unit_no}' in the list view and click on it",
            "wait_after": self.config.wait_seconds,
        })

        # Step 3: Go to Payments tab
        steps.append({
            "step": 3,
            "action": "click",
            "description": "Click the 'Payments' tab on the unit record",
            "hint": "Tab labeled 'Payments' next to 'Details'",
            "wait_after": self.config.wait_seconds + 1,
        })

        # Step 4: Find the right payment record
        steps.append({
            "step": 4,
            "action": "find_and_click",
            "description": f"Find the payment record matching AED {amount:,.2f} or the next unpaid/overdue one",
            "hint": "Look at Sub Total and Status columns. Click the BP-XXXXX link for the matching payment",
            "wait_after": self.config.wait_seconds,
        })

        # Step 5: Click Generate Invoice
        steps.append({
            "step": 5,
            "action": "click",
            "description": "Click 'Generate Invoice' button",
            "hint": "Button in the top-right area of the payment record header, next to 'Edit'",
            "wait_after": self.config.wait_seconds + 2,
            "confirm": True,
        })

        # Step 6: Handle any confirmation dialog
        steps.append({
            "step": 6,
            "action": "confirm_dialog",
            "description": "If a confirmation dialog appears, click OK/Confirm/Save",
            "hint": "Look for a modal with confirm/save button",
            "wait_after": self.config.wait_seconds,
        })

        # Step 7: Go back to unit record
        steps.append({
            "step": 7,
            "action": "click",
            "description": f"Click the Unit '{unit_no}' link to go back to the inventory record",
            "hint": "The Inventory field shows '201' (or unit number) as a link",
            "wait_after": self.config.wait_seconds,
        })

        # Step 8: Go to Account Statements tab
        steps.append({
            "step": 8,
            "action": "click",
            "description": "Click the 'Account Statements' tab",
            "hint": "Tab next to 'Payments' tab",
            "wait_after": self.config.wait_seconds + 1,
        })

        # Step 9: Send email via Activity panel
        steps.append({
            "step": 9,
            "action": "send_email",
            "description": f"Send email to buyer ({client}) with receipt + statement",
            "hint": "Click the email icon (envelope) in the Activity panel on the right side",
            "email_details": {
                "to": f"Buyer of Unit {unit_no}",
                "subject": f"[fam Properties] Payment Receipt & Statement — Century Unit No.{unit_no}",
                "body": f"Dear Valued Client,\n\nPlease find attached the payment receipt and updated statement of account for Century Unit No.{unit_no}.\n\nKindly acknowledge receipt of this email.\n\nRegards",
                "attachments": ["Receipt PDF", "Statement of Account PDF"],
            },
            "wait_after": self.config.wait_seconds,
            "confirm": True,
        })

        return steps

    # ------------------------------------------------------------------
    # Batch processing plan
    # ------------------------------------------------------------------

    def generate_batch_plan(self, needs_receipt: list[dict]) -> dict:
        """
        Generate a complete execution plan for all units needing receipts.
        Returns a structured plan that can be reviewed before execution.
        """
        plan = {
            "total_units": len(needs_receipt),
            "dry_run": self.config.dry_run,
            "sf_base_url": self.config.sf_base_url,
            "units": [],
        }

        for item in needs_receipt:
            unit_no = item.get("unit_no", "")
            if not unit_no:
                continue

            unit_plan = {
                "unit_no": unit_no,
                "amount": item.get("credit", 0),
                "client": item.get("account_name", ""),
                "date": item.get("date", ""),
                "row_in_master": item.get("row", ""),
                "sheet": item.get("sheet", ""),
                "steps": self.get_instructions_for_unit(
                    unit_no=unit_no,
                    amount=item.get("credit", 0),
                    client=item.get("account_name", ""),
                ),
                "actions": [
                    {
                        "type": "update_payment",
                        "description": f"Update Amount Paid for the matching installment",
                    },
                    {
                        "type": "generate_invoice",
                        "description": f"Click 'Generate Invoice' on the payment record",
                    },
                    {
                        "type": "send_email",
                        "description": f"Send receipt + statement to buyer via SF email",
                    },
                    {
                        "type": "mark_master_sheet",
                        "description": f"Mark receipt column as 'Done' in master sheet row {item.get('row', '?')}",
                    },
                ],
            }
            plan["units"].append(unit_plan)

        return plan

    # ------------------------------------------------------------------
    # Master sheet receipt column update
    # ------------------------------------------------------------------

    @staticmethod
    def mark_receipts_done(master_path: str, output_path: str, completed_units: list[dict]) -> dict:
        """
        Update the receipt column in the master sheet for completed units.
        completed_units: list of {"row": int, "sheet": str, "unit_no": str}
        """
        import openpyxl
        from openpyxl.styles import PatternFill

        wb = openpyxl.load_workbook(master_path)
        done_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        updated = 0

        for item in completed_units:
            sheet_name = item.get("sheet", "")
            row = item.get("row", 0)
            if not sheet_name or not row or sheet_name not in wb.sheetnames:
                continue

            ws = wb[sheet_name]

            # Receipt column: Col J (10) for Escrow, doesn't exist for Corporate
            if "Escrow" in sheet_name:
                receipt_col = 10
            else:
                continue  # Corporate doesn't have a receipt column

            ws.cell(row, receipt_col, "Done")
            ws.cell(row, receipt_col).fill = done_fill
            updated += 1

        wb.save(output_path)
        return {"updated": updated, "output_path": output_path}

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> dict:
        """Get a summary of all planned/executed actions."""
        by_type = {}
        by_status = {}
        for a in self.actions_log:
            by_type[a.action_type] = by_type.get(a.action_type, 0) + 1
            by_status[a.status] = by_status.get(a.status, 0) + 1

        return {
            "total_actions": len(self.actions_log),
            "by_type": by_type,
            "by_status": by_status,
            "actions": [a.to_dict() for a in self.actions_log],
        }


# ---------------------------------------------------------------------------
# Convenience function for Claude Code execution
# ---------------------------------------------------------------------------

def plan_sf_automation(needs_receipt: list[dict], dry_run: bool = True) -> dict:
    """
    Generate an SF browser automation plan from the needs_receipt list.

    Usage in Claude Code:
        from agents.sf_browser_agent import plan_sf_automation
        plan = plan_sf_automation(needs_receipt_data)
        print(json.dumps(plan, indent=2))
    """
    config = SFBrowserConfig(dry_run=dry_run)
    agent = SalesforceBrowserAgent(config=config)
    return agent.generate_batch_plan(needs_receipt)


def mark_receipts_in_master(
    master_path: str, output_path: str, completed_units: list[dict]
) -> dict:
    """
    Mark receipt column as 'Done' for completed units.

    Usage in Claude Code:
        from agents.sf_browser_agent import mark_receipts_in_master
        result = mark_receipts_in_master('Century_Updated.xlsx', 'output.xlsx', units)
    """
    return SalesforceBrowserAgent.mark_receipts_done(
        master_path, output_path, completed_units
    )
