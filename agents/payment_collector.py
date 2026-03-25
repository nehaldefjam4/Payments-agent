"""
Payment Collector Agent -- Automates Amit's payment reconciliation workflow
for the Century project (Business Bay).

Core workflow:
1. Parse bank statement PDF from Geo (Emirates NBD escrow)
2. Identify credit transactions
3. Match each credit to a unit/client (multi-phase matching)
4. For matched payments: generate receipt data + SOA for client
5. For unmatched: flag for human review
6. Produce reconciled statement for Century team

Uses Claude for intelligent analysis when ambiguous matches arise.
"""

import os
import json
from datetime import datetime
from pathlib import Path

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS
from config.payment_settings import (
    CENTURY_PROJECT, STAKEHOLDERS, EMAIL_TEMPLATES,
    MATCHING_RULES, CALENDLY_PAYMENT, DECISION_RULES,
    SPA_PENALTY,
)
from processors.bank_statement_parser import BankStatementParser, Transaction
from processors.payment_matcher import PaymentMatcher, ExpectedPayment, MatchResult
from utils.email_service import EmailService

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


PAYMENT_SYSTEM_PROMPT = """You are the Payment Collector Agent for fam Properties Master Agency, managing payment reconciliation for the Century project in Business Bay, Dubai.

Your role is to:
1. Analyze bank statement transactions from the Century escrow account (Emirates NBD)
2. Match incoming payments (credits) to specific unit buyers
3. Identify which installment each payment corresponds to
4. Flag unmatched or ambiguous transactions for human review
5. Generate payment receipts and SOA updates for clients
6. Prepare reconciled statements for the Century developer team

You have deep knowledge of:
- Century payment plan structure (pre-handover Q1-Q8, on-handover, post-handover Q1-Q8)
- SPA penalty clause: 2% per month compounded quarterly for late payments
- Emirates NBD escrow account conventions
- Common transaction description formats

When matching payments, use this priority:
1. Unit number explicitly mentioned in description (highest confidence)
2. Payer name matching against known client database
3. Amount matching against expected installments (use with caution if multiple units expect the same amount)

Always err on the side of flagging for review rather than making incorrect matches. A wrong match causes receipt/SOA errors that are hard to correct."""

PAYMENT_TOOLS = [
    {
        "name": "parse_bank_statement",
        "description": "Parse the uploaded bank statement PDF and extract all transactions. Returns credits and debits with dates, amounts, descriptions.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "match_payments",
        "description": "Run the multi-phase matching engine on credit transactions against expected payments. Returns matched, review-needed, and unmatched transactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "credits": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Credit transactions to match"
                }
            },
            "required": ["credits"]
        }
    },
    {
        "name": "get_expected_payments",
        "description": "Retrieve the list of expected (pending) installment payments for Century units. Used for amount-based matching.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "update_match",
        "description": "Manually update or confirm a match for a specific transaction. Use when Claude identifies a better match than the automated engine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_index": {"type": "integer", "description": "Index of the transaction in the credits list"},
                "unit_no": {"type": "string"},
                "client_name": {"type": "string"},
                "installment": {"type": "string"},
                "confidence": {"type": "number"},
                "method": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["transaction_index", "unit_no"]
        }
    },
    {
        "name": "generate_reconciliation",
        "description": "Generate the reconciled bank statement summary to send to the Century team. Lists each credit with matched unit details.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "draft_client_email",
        "description": "Draft an email to a client (payment acknowledgment, receipt delivery, SOA, or bounced cheque notification).",
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "enum": ["payment_proof_ack", "payment_receipt_delivery", "soa_delivery", "bounced_cheque"],
                    "description": "Which email template to use"
                },
                "client_email": {"type": "string"},
                "client_name": {"type": "string"},
                "unit_no": {"type": "string"},
                "variables": {"type": "object", "description": "Template variables to fill in"},
            },
            "required": ["template", "unit_no"]
        }
    },
    {
        "name": "draft_developer_email",
        "description": "Draft an email to the Century developer team (bank statement request, cash collection list, reconciliation).",
        "input_schema": {
            "type": "object",
            "properties": {
                "template": {
                    "type": "string",
                    "enum": ["bank_statement_request", "cash_collection", "reconciliation_summary"],
                    "description": "Which email template to use"
                },
                "variables": {"type": "object", "description": "Template variables"},
            },
            "required": ["template"]
        }
    },
]


class PaymentCollectorAgent:
    """The Payment Collector Agent -- orchestrates payment reconciliation."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
        self.use_claude = bool(self.api_key) and HAS_ANTHROPIC
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.use_claude else None

        self.parser = BankStatementParser()
        self.matcher = PaymentMatcher()
        self.email_service = EmailService(live_mode=False)

        # State
        self.parsed_statement = None
        self.match_results: list[MatchResult] = []
        self.expected_payments: list[ExpectedPayment] = []
        self.drafted_emails: list[dict] = []
        self.reconciliation: dict = {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_bank_statement(
        self,
        pdf_path: str,
        expected_payments: list[dict] = None,
        step_callback=None,
    ) -> dict:
        """
        Full pipeline: parse statement -> match payments -> generate outputs.
        """
        print(f"\n{'='*60}")
        print(f"  PAYMENT COLLECTOR AGENT -- Processing Bank Statement")
        print(f"{'='*60}")
        print(f"  File:  {pdf_path}")
        print(f"  Mode:  {'Agentic (Claude)' if self.use_claude else 'Rule-based'}")
        print(f"{'='*60}\n")

        # Load expected payments if provided
        if expected_payments:
            self.expected_payments = [
                ExpectedPayment(**ep) if isinstance(ep, dict) else ep
                for ep in expected_payments
            ]
            self.matcher = PaymentMatcher(self.expected_payments)
            print(f"  Loaded {len(self.expected_payments)} expected payment(s)\n")

        # Step 1: Parse the bank statement
        print("[1/4] Parsing bank statement PDF...")
        self.parsed_statement = self.parser.parse(pdf_path)

        if self.parsed_statement.get("error"):
            print(f"  ERROR: {self.parsed_statement['error']}")
            return self.parsed_statement

        print(f"  Period: {self.parsed_statement.get('statement_period', 'N/A')}")
        print(f"  Total transactions: {self.parsed_statement['total_transactions']}")
        print(f"  Credits: {self.parsed_statement['total_credits']} (AED {self.parsed_statement['total_credit_amount']:,.2f})")
        print(f"  Debits: {self.parsed_statement['total_debits']}")

        if step_callback:
            step_callback(1, "parse", "parse_bank_statement", "Parsed bank statement",
                         {"credits": self.parsed_statement["total_credits"],
                          "total_amount": self.parsed_statement["total_credit_amount"]})

        # Step 1.5: Run multi-pass intelligent matching
        print(f"\n[1.5/4] Running multi-pass matching (unit, IBAN, name, fuzzy)...")
        self.parser.run_multi_pass_matching()
        credits_after = self.parser.get_credits_only()
        matched_count = sum(1 for c in credits_after if c.matched_unit)
        print(f"  Matched after multi-pass: {matched_count} out of {len(credits_after)}")

        # Step 2: Match credit transactions
        print(f"\n[2/4] Matching {self.parsed_statement['total_credits']} credit transaction(s)...")
        credits = self.parser.get_credits_only()

        if self.use_claude:
            print("  Running Claude agentic analysis...")
            result = self._run_agentic_loop(pdf_path, credits, step_callback)
        else:
            print("  Running rule-based matching...")
            self.match_results = self.matcher.match_transactions(credits)
            result = None

        summary = self.matcher.get_summary() if self.match_results else {}
        print(f"  Matched: {summary.get('matched', 0)}")
        print(f"  Needs review: {summary.get('needs_review', 0)}")
        print(f"  Unmatched: {summary.get('unmatched', 0)}")

        if step_callback:
            step_callback(2, "match", "match_payments", "Payment matching complete", summary)

        # Step 3: Generate reconciliation
        print(f"\n[3/4] Generating reconciliation...")
        self.reconciliation = self._build_reconciliation()

        if step_callback:
            step_callback(3, "reconcile", "generate_reconciliation",
                         "Reconciliation generated", self.reconciliation)

        # Step 4: Draft emails
        print(f"\n[4/4] Drafting notification emails...")
        self._draft_all_emails()
        print(f"  Drafted {len(self.drafted_emails)} email(s)")

        if step_callback:
            step_callback(4, "emails", "draft_emails",
                         f"Drafted {len(self.drafted_emails)} emails", {})

        # Build final result
        final = {
            "statement": {
                "file": self.parsed_statement.get("file"),
                "period": self.parsed_statement.get("statement_period"),
                "total_credits": self.parsed_statement["total_credits"],
                "total_credit_amount": self.parsed_statement["total_credit_amount"],
                "total_debits": self.parsed_statement["total_debits"],
                "total_debit_amount": self.parsed_statement["total_debit_amount"],
            },
            "matching": {
                "summary": summary,
                "results": [r.to_dict() for r in self.match_results],
            },
            "reconciliation": self.reconciliation,
            "drafted_emails": self.drafted_emails,
            "processed_at": datetime.now().isoformat(),
        }

        print(f"\n{'='*60}")
        print(f"  PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"  Credits processed: {self.parsed_statement['total_credits']}")
        print(f"  Matched: {summary.get('matched', 0)} | Review: {summary.get('needs_review', 0)} | Unmatched: {summary.get('unmatched', 0)}")
        print(f"  Emails drafted: {len(self.drafted_emails)}")
        print(f"{'='*60}\n")

        return final

    # ------------------------------------------------------------------
    # Agentic loop (Claude-powered)
    # ------------------------------------------------------------------

    def _run_agentic_loop(self, pdf_path: str, credits: list[Transaction], step_callback=None) -> dict:
        """Let Claude drive the matching process with tool calls."""
        if not self.client:
            return None

        # First do rule-based matching to give Claude a starting point
        self.match_results = self.matcher.match_transactions(credits)

        user_message = self._build_initial_prompt(credits)
        messages = [{"role": "user", "content": user_message}]

        turn_count = 0
        max_turns = 10

        while turn_count < max_turns:
            turn_count += 1
            print(f"    [Agentic] Turn {turn_count}/{max_turns}")

            try:
                response = self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=CLAUDE_MAX_TOKENS,
                    system=PAYMENT_SYSTEM_PROMPT,
                    tools=PAYMENT_TOOLS,
                    messages=messages,
                )
            except Exception as e:
                print(f"    [Agentic] API error: {e}")
                return {"error": str(e)}

            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason == "end_turn":
                print(f"    [Agentic] Finished after {turn_count} turns")
                return {"turns": turn_count}

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        print(f"    [Tool] {tool_name}")

                        result = self._handle_tool_call(tool_name, tool_input, credits)

                        if step_callback:
                            step_callback(
                                turn_count, "tool_call", tool_name,
                                f"Called {tool_name}", {"result_keys": list(result.keys()) if isinstance(result, dict) else []}
                            )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, default=str),
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                return {"turns": turn_count, "stop_reason": response.stop_reason}

        return {"error": "max_turns_exceeded", "turns": turn_count}

    def _handle_tool_call(self, tool_name: str, tool_input: dict, credits: list[Transaction]) -> dict:
        """Execute a tool call."""
        try:
            if tool_name == "parse_bank_statement":
                return {
                    "total_credits": self.parsed_statement["total_credits"],
                    "total_credit_amount": self.parsed_statement["total_credit_amount"],
                    "credits": [
                        {
                            "index": i,
                            "date": c.date,
                            "amount": c.credit,
                            "description": c.description[:200],
                            "reference": c.reference,
                        }
                        for i, c in enumerate(credits)
                    ],
                }

            elif tool_name == "get_expected_payments":
                return {
                    "count": len(self.expected_payments),
                    "payments": [ep.to_dict() for ep in self.expected_payments[:50]],
                }

            elif tool_name == "match_payments":
                return {
                    "summary": self.matcher.get_summary(),
                    "results": [
                        {
                            "index": i,
                            "date": r.transaction_date,
                            "amount": r.transaction_amount,
                            "unit": r.matched_unit,
                            "client": r.matched_client,
                            "installment": r.matched_installment,
                            "confidence": r.confidence,
                            "method": r.match_method,
                            "status": r.status,
                            "notes": r.notes,
                        }
                        for i, r in enumerate(self.match_results)
                    ],
                }

            elif tool_name == "update_match":
                idx = tool_input["transaction_index"]
                if 0 <= idx < len(self.match_results):
                    r = self.match_results[idx]
                    r.matched_unit = tool_input.get("unit_no", r.matched_unit)
                    r.matched_client = tool_input.get("client_name", r.matched_client)
                    r.matched_installment = tool_input.get("installment", r.matched_installment)
                    r.confidence = tool_input.get("confidence", r.confidence)
                    r.match_method = tool_input.get("method", "claude_override")
                    r.status = "matched" if r.confidence >= MATCHING_RULES["auto_match_confidence"] else "review"
                    r.notes = tool_input.get("notes", r.notes)
                    return {"status": "updated", "index": idx, "new_status": r.status}
                return {"error": f"Invalid index: {idx}"}

            elif tool_name == "generate_reconciliation":
                self.reconciliation = self._build_reconciliation()
                return self.reconciliation

            elif tool_name == "draft_client_email":
                template_id = tool_input["template"]
                unit_no = tool_input["unit_no"]
                variables = tool_input.get("variables", {})
                variables["unit_no"] = unit_no

                template = EMAIL_TEMPLATES.get(template_id)
                if not template:
                    return {"error": f"Unknown template: {template_id}"}

                subject = template["subject"].format(**variables)
                body = template["body"].format(**{k: variables.get(k, f"[{k}]") for k in
                    set(sum([list(re.findall(r'\{(\w+)\}', s)) for s in [template["subject"], template["body"]]], []))
                })

                email = {
                    "to": tool_input.get("client_email", f"client_{unit_no}@email.com"),
                    "subject": subject,
                    "body": body,
                    "template": template_id,
                    "unit_no": unit_no,
                }
                self.drafted_emails.append(email)
                return {"status": "drafted", "email_index": len(self.drafted_emails) - 1, "subject": subject}

            elif tool_name == "draft_developer_email":
                template_id = tool_input["template"]
                variables = tool_input.get("variables", {})

                template = EMAIL_TEMPLATES.get(template_id)
                if not template:
                    return {"error": f"Unknown template: {template_id}"}

                import re as _re
                keys = set(sum([list(_re.findall(r'\{(\w+)\}', s)) for s in [template["subject"], template["body"]]], []))
                safe_vars = {k: variables.get(k, f"[{k}]") for k in keys}

                email = {
                    "to": ", ".join([s["email"] for s in STAKEHOLDERS["developer"]]),
                    "subject": template["subject"].format(**safe_vars),
                    "body": template["body"].format(**safe_vars),
                    "template": template_id,
                }
                self.drafted_emails.append(email)
                return {"status": "drafted", "email_index": len(self.drafted_emails) - 1}

            return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}

    def _build_initial_prompt(self, credits: list[Transaction]) -> str:
        """Build the prompt that kicks off Claude's analysis."""
        credits_summary = []
        for i, c in enumerate(credits):
            credits_summary.append(f"  [{i}] {c.date} | AED {c.credit:,.2f} | {c.description[:100]}")

        match_summary = []
        for i, r in enumerate(self.match_results):
            match_summary.append(
                f"  [{i}] AED {r.transaction_amount:,.2f} -> "
                f"Unit: {r.matched_unit or '?'} | "
                f"Client: {r.matched_client or '?'} | "
                f"Confidence: {r.confidence:.0%} | "
                f"Status: {r.status}"
            )

        return f"""I've parsed a bank statement and run initial matching. Please review and improve the results.

BANK STATEMENT SUMMARY:
- Period: {self.parsed_statement.get('statement_period', 'N/A')}
- Total credits: {self.parsed_statement['total_credits']}
- Total credit amount: AED {self.parsed_statement['total_credit_amount']:,.2f}

CREDIT TRANSACTIONS:
{chr(10).join(credits_summary)}

INITIAL MATCHING RESULTS:
{chr(10).join(match_summary)}

EXPECTED PAYMENTS LOADED: {len(self.expected_payments)}

Please:
1. Call `match_payments` to see the detailed matching results
2. Review any "review" or "unmatched" transactions
3. Use `update_match` to correct or improve matches where you can identify the unit/client
4. Call `generate_reconciliation` to produce the final reconciled statement
5. Draft any necessary client notification emails using `draft_client_email`

After completing all steps, provide your final analysis summary."""

    # ------------------------------------------------------------------
    # Reconciliation builder
    # ------------------------------------------------------------------

    def _build_reconciliation(self) -> dict:
        """Build the reconciled statement for the Century team."""
        rows = []
        for r in self.match_results:
            rows.append({
                "date": r.transaction_date,
                "amount": r.transaction_amount,
                "description": r.transaction_description[:80],
                "unit_no": r.matched_unit or "UNMATCHED",
                "client": r.matched_client or "Unknown",
                "installment": r.matched_installment or "",
                "status": r.status,
                "confidence": r.confidence,
            })

        matched = [r for r in rows if r["status"] == "matched"]
        review = [r for r in rows if r["status"] == "review"]
        unmatched = [r for r in rows if r["status"] == "unmatched"]

        return {
            "period": self.parsed_statement.get("statement_period", ""),
            "generated_at": datetime.now().isoformat(),
            "rows": rows,
            "matched_count": len(matched),
            "review_count": len(review),
            "unmatched_count": len(unmatched),
            "total_matched_amount": round(sum(r["amount"] for r in matched), 2),
            "total_review_amount": round(sum(r["amount"] for r in review), 2),
            "total_unmatched_amount": round(sum(r["amount"] for r in unmatched), 2),
        }

    # ------------------------------------------------------------------
    # Email drafting
    # ------------------------------------------------------------------

    def _draft_all_emails(self):
        """Draft notification emails for all matched payments."""
        for r in self.match_results:
            if r.status == "matched" and r.matched_unit:
                # Draft payment receipt email for matched transactions
                client = self.matcher._find_client_for_unit(r.matched_unit)
                self.drafted_emails.append({
                    "to": client.client_email if client else f"unit_{r.matched_unit}@pending.com",
                    "subject": f"[fam Properties] Payment Receipt -- Century Unit No.{r.matched_unit}",
                    "body": EMAIL_TEMPLATES["payment_receipt_delivery"]["body"].format(
                        unit_no=r.matched_unit,
                        installment_type=r.matched_installment or "N/A",
                    ),
                    "template": "payment_receipt_delivery",
                    "unit_no": r.matched_unit,
                    "amount": r.transaction_amount,
                })
