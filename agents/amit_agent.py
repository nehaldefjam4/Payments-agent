"""
Amit Agent -- Unified AI agent that replaces Amit Patel's role as
Operations Executive for Century project (Business Bay).

Handles all 8 core workflows:
1. Payment proof acknowledgment
2. Cash & cheque collection coordination
3. Bounced cheque notification
4. SOA sharing & payment schedule
5. Cheque due date management
6. Bank statement reconciliation (delegates to PaymentCollectorAgent)
7. Weekly handover status emails
8. Commission follow-up

The agent classifies incoming emails, determines the appropriate workflow,
and either auto-responds or drafts a response for review.
"""

import os
import re
import json
import sys
import logging
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional

logger = logging.getLogger("amit_agent")
logging.basicConfig(level=logging.INFO, stream=sys.stderr)

from config.payment_settings import (
    EMAIL_TEMPLATES, STAKEHOLDERS, CENTURY_PROJECT,
    CALENDLY_PAYMENT, CALENDLY_HOME_ORIENTATION,
    SPA_PENALTY, INSTALLMENT_TYPES,
)


# =========================================================================
# EMAIL CLASSIFICATION
# =========================================================================

WORKFLOW_LABELS = {
    "1_payment_proof": "Payment Proof Acknowledgment",
    "1b_receipt_request": "Payment Receipt Request",
    "2_cash_collection": "Cash & Cheque Collection",
    "3_bounced_cheque": "Bounced Cheque Alert",
    "4_soa_request": "SOA / Payment Schedule",
    "4b_escrow_details": "Escrow Account Details",
    "5_cheque_due_date": "Cheque Due Date",
    "5b_cheque_replacement": "Cheque Replacement",
    "6_bank_reconciliation": "Bank Statement Reconciliation",
    "7_handover": "Handover / Key Collection",
    "8_commission": "Commission Follow-Up",
    "unknown": "Unclassified",
}


@dataclass
class ClassifiedEmail:
    """An incoming email classified into a workflow."""
    message_id: str = ""
    thread_id: str = ""
    from_addr: str = ""
    from_name: str = ""
    to_addr: str = ""
    subject: str = ""
    body_preview: str = ""
    date: str = ""
    workflow: str = ""
    workflow_label: str = ""
    confidence: float = 0.0
    extracted_data: dict = field(default_factory=dict)
    suggested_action: str = ""
    draft_response: str = ""
    draft_subject: str = ""
    classification_method: str = ""  # "regex" or "claude"

    def to_dict(self):
        return asdict(self)


# Workflow classification patterns
WORKFLOW_PATTERNS = {
    "payment_proof": {
        "workflow": "1_payment_proof",
        "label": "Payment Proof Acknowledgment",
        "action": "auto_reply",
        "patterns": [
            r"proof\s+of\s+(?:transfer|payment|deposit)",
            r"(?:attached|sharing|find)\s+(?:the\s+)?(?:proof|transfer|receipt|screenshot)",
            r"bank\s+transfer\s+(?:confirmation|receipt|proof)",
            r"(?:payment|transfer)\s+(?:has been|was)\s+(?:made|done|completed|sent)",
            r"kindly\s+find\s+(?:attached|the)\s+(?:proof|transfer)",
            r"transferred\s+(?:the\s+)?(?:amount|payment|AED)",
        ],
    },
    "soa_request": {
        "workflow": "4_soa_request",
        "label": "SOA / Payment Schedule Request",
        "action": "draft_reply",
        "patterns": [
            r"(?:share|send|provide)\s+(?:the\s+)?(?:SOA|statement\s+of\s+account)",
            r"(?:how\s+much|what)\s+(?:do\s+I|is)\s+(?:owe|due|outstanding|remaining)",
            r"(?:payment|installment)\s+(?:schedule|plan|breakdown|details)",
            r"(?:next|upcoming)\s+(?:payment|installment|due\s+date)",
            r"(?:balance|amount)\s+(?:due|outstanding|remaining|pending)",
        ],
    },
    "bounced_cheque": {
        "workflow": "3_bounced_cheque",
        "label": "Bounced Cheque Alert",
        "action": "auto_reply",
        "patterns": [
            r"(?:cheque|check)\s+(?:return|bounce|reject|dishon)",
            r"(?:returned|bounced)\s+(?:cheque|check)",
            r"(?:insufficient\s+funds|signature\s+irregular|refer\s+to\s+drawer)",
            r"CHQ\.?\s*NO",
        ],
    },
    "receipt_request": {
        "workflow": "1b_receipt_request",
        "label": "Payment Receipt Request",
        "action": "draft_reply",
        "patterns": [
            r"(?:where|when)\s+(?:is|will)\s+(?:my|the)\s+receipt",
            r"(?:send|share|provide)\s+(?:the\s+)?(?:payment\s+)?receipt",
            r"(?:haven.t|not)\s+(?:received|got)\s+(?:the\s+)?receipt",
            r"receipt\s+(?:for|of)\s+(?:the\s+)?(?:payment|transfer)",
        ],
    },
    "escrow_details": {
        "workflow": "4b_escrow_details",
        "label": "Escrow Account Details Request",
        "action": "auto_reply",
        "patterns": [
            r"(?:escrow|bank)\s+(?:account|details|information)",
            r"(?:where|how)\s+(?:to|should\s+I)\s+(?:transfer|pay|send|deposit)",
            r"(?:IBAN|account\s+number|bank\s+details)",
            r"(?:payment|transfer)\s+(?:method|instructions|details)",
        ],
    },
    "cheque_replacement": {
        "workflow": "5b_cheque_replacement",
        "label": "Cheque Replacement Request",
        "action": "draft_reply",
        "patterns": [
            r"(?:replace|swap|change)\s+(?:the\s+)?(?:cheque|check)",
            r"(?:bank\s+transfer)\s+(?:instead\s+of|rather\s+than)\s+(?:cheque|check)",
            r"(?:cancel|stop)\s+(?:the\s+)?(?:cheque|check)",
        ],
    },
    "cash_collection": {
        "workflow": "2_cash_collection",
        "label": "Cash & Cheque Collection",
        "action": "draft_reply",
        "patterns": [
            r"cash\s+collection",
            r"(?:PDC|post[- ]?dated\s+cheque)",
            r"collection\s+(?:schedule|appointment|list)",
        ],
    },
    "cheque_due_date": {
        "workflow": "5_cheque_due_date",
        "label": "Cheque Due Date",
        "action": "draft_reply",
        "patterns": [
            r"(?:cheque|check)\s+(?:due\s+date|deposit\s+date)",
            r"(?:cheques|checks)\s+on\s+hand",
            r"(?:put\s+on\s+hold|hold\s+(?:the\s+)?cheque)",
        ],
    },
    "bank_reconciliation": {
        "workflow": "6_bank_reconciliation",
        "label": "Bank Statement Reconciliation",
        "action": "draft_reply",
        "patterns": [
            r"bank\s+statement",
            r"reconcil(?:e|iation)",
            r"escrow\s+(?:statement|balance)",
        ],
    },
    "handover_query": {
        "workflow": "7_handover",
        "label": "Handover / Key Collection Query",
        "action": "draft_reply",
        "patterns": [
            r"(?:handover|hand\s+over|key\s+(?:collection|handover))",
            r"(?:DEWA|Empower)\s+(?:activation|status|registration)",
            r"(?:home\s+orientation|snagging|inspection)",
            r"(?:when|how)\s+(?:can\s+I|to)\s+(?:collect|get)\s+(?:the\s+)?(?:key|keys)",
            r"(?:POA|power\s+of\s+attorney)",
        ],
    },
    "commission_query": {
        "workflow": "8_commission",
        "label": "Commission Follow-Up",
        "action": "escalate",
        "patterns": [
            r"commission\s+(?:payment|status|update|invoice)",
            r"(?:when|where)\s+(?:is|will)\s+(?:the\s+)?commission",
            r"(?:invoice|payment)\s+(?:for|of)\s+(?:commission|brokerage)",
        ],
    },
}


# =========================================================================
# CLAUDE AI CLASSIFICATION
# =========================================================================

CLASSIFICATION_SYSTEM_PROMPT = """You are an email classifier for fam Master Agency's Century project operations.

Classify incoming emails into exactly ONE of these workflows:
- 1_payment_proof: Client sends proof of bank transfer/payment
- 1b_receipt_request: Client asks where their payment receipt is
- 2_cash_collection: Related to cash/cheque collection scheduling
- 3_bounced_cheque: Cheque returned/bounced notification from developer
- 4_soa_request: Client requests Statement of Account or payment schedule
- 4b_escrow_details: Client asks for escrow/bank account details to make payment
- 5_cheque_due_date: Cheque deposit date management
- 5b_cheque_replacement: Client wants to replace cheque with bank transfer
- 6_bank_reconciliation: Bank statement sharing/reconciliation
- 7_handover: Handover status, DEWA/Empower, home orientation, key collection
- 8_commission: Commission payment follow-up from sub-agents
- unknown: Cannot classify

Also extract any structured data: unit_no, amount (AED), cheque_no, installment_type, bounce_reason, payer_name.

Respond in JSON format:
{
  "workflow": "1_payment_proof",
  "confidence": 0.95,
  "suggested_action": "auto_reply|draft_reply|escalate",
  "extracted_data": {"unit_no": "1205", "amount": "125000"},
  "reasoning": "Brief explanation"
}"""


def classify_with_claude(subject: str, body: str, from_addr: str) -> Optional[dict]:
    """Use Claude to classify an email when regex is uncertain."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=CLASSIFICATION_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"From: {from_addr}\nSubject: {subject}\n\nBody:\n{body[:1500]}"
            }],
        )

        text = message.content[0].text
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"[AmitAgent] Claude classification error: {e}")

    return None


# =========================================================================
# AGENT
# =========================================================================

class AmitAgent:
    """
    The unified AI agent that handles all of Amit's workflows.
    Classifies emails, generates responses, and manages the payment lifecycle.
    """

    def __init__(self, supabase_client=None):
        self.classified_emails: list[ClassifiedEmail] = []
        self.actions_taken: list[dict] = []
        self._sb = supabase_client

    @property
    def sb(self):
        if self._sb is None:
            try:
                from supabase import create_client
                from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY
                url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
                key = os.environ.get("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)
                if url and key:
                    self._sb = create_client(url, key)
            except Exception as e:
                logger.error(f"Supabase init error: {e}")
        return self._sb

    # =================================================================
    # EMAIL CLASSIFICATION
    # =================================================================

    def classify_email(self, message_id: str, thread_id: str,
                       from_addr: str, from_name: str, to_addr: str,
                       subject: str, body: str, date: str = "",
                       use_claude: bool = True) -> ClassifiedEmail:
        """Classify an incoming email into one of the workflows.

        Uses regex first-pass. If confidence < 0.6, falls back to Claude AI.
        """
        classified = ClassifiedEmail(
            message_id=message_id,
            thread_id=thread_id,
            from_addr=from_addr,
            from_name=from_name,
            to_addr=to_addr,
            subject=subject,
            body_preview=body[:500],
            date=date,
        )

        combined_text = f"{subject} {body}".lower()

        # --- Phase 1: Regex classification ---
        best_workflow = None
        best_score = 0

        for wf_key, wf_config in WORKFLOW_PATTERNS.items():
            score = 0
            for pattern in wf_config["patterns"]:
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                score += len(matches) * 2

            if score > best_score:
                best_score = score
                best_workflow = wf_config

        regex_confidence = min(1.0, best_score / 10) if best_workflow else 0.0

        if best_workflow and regex_confidence >= 0.6:
            classified.workflow = best_workflow["workflow"]
            classified.workflow_label = best_workflow["label"]
            classified.confidence = regex_confidence
            classified.suggested_action = best_workflow["action"]
            classified.extracted_data = self._extract_data(combined_text)
            classified.classification_method = "regex"
        elif use_claude:
            # --- Phase 2: Claude AI classification ---
            claude_result = classify_with_claude(subject, body, from_addr)
            if claude_result:
                wf = claude_result.get("workflow", "unknown")
                classified.workflow = wf
                classified.workflow_label = WORKFLOW_LABELS.get(wf, wf)
                classified.confidence = claude_result.get("confidence", 0.5)
                classified.suggested_action = claude_result.get("suggested_action", "draft_reply")
                classified.extracted_data = claude_result.get("extracted_data", {})
                classified.classification_method = "claude"
            else:
                # Fallback: use regex result even if low confidence
                if best_workflow and best_score >= 2:
                    classified.workflow = best_workflow["workflow"]
                    classified.workflow_label = best_workflow["label"]
                    classified.confidence = regex_confidence
                    classified.suggested_action = best_workflow["action"]
                    classified.extracted_data = self._extract_data(combined_text)
                    classified.classification_method = "regex"
                else:
                    classified.workflow = "unknown"
                    classified.workflow_label = "Unclassified"
                    classified.confidence = 0.0
                    classified.suggested_action = "escalate"
                    classified.classification_method = "regex"
        else:
            if best_workflow and best_score >= 2:
                classified.workflow = best_workflow["workflow"]
                classified.workflow_label = best_workflow["label"]
                classified.confidence = regex_confidence
                classified.suggested_action = best_workflow["action"]
                classified.extracted_data = self._extract_data(combined_text)
                classified.classification_method = "regex"
            else:
                classified.workflow = "unknown"
                classified.workflow_label = "Unclassified"
                classified.confidence = 0.0
                classified.suggested_action = "escalate"
                classified.classification_method = "regex"

        # Generate draft response
        classified.draft_subject, classified.draft_response = self._generate_response(
            classified.workflow, classified.from_name, classified.extracted_data
        )

        self.classified_emails.append(classified)
        return classified

    def _extract_data(self, text: str) -> dict:
        """Extract structured data from email text."""
        data = {}

        # Unit number
        unit_match = re.search(r'(?:unit|apt|apartment)\s*(?:no\.?\s*)?(\d{3,4})', text, re.IGNORECASE)
        if unit_match:
            data["unit_no"] = unit_match.group(1)

        # Amount
        amount_match = re.search(r'AED\s*([\d,]+(?:\.\d{2})?)', text, re.IGNORECASE)
        if amount_match:
            data["amount"] = amount_match.group(1).replace(",", "")

        # Cheque number
        chq_match = re.search(r'(?:cheque|check|chq)\.?\s*(?:no\.?\s*)?:?\s*(\d+)', text, re.IGNORECASE)
        if chq_match:
            data["cheque_no"] = chq_match.group(1)

        # Bounce reason
        bounce_reasons = ["insufficient funds", "signature irregular", "refer to drawer",
                         "payment stopped", "account closed", "stale cheque"]
        for reason in bounce_reasons:
            if reason in text.lower():
                data["bounce_reason"] = reason.title()
                break

        # Installment type
        installment_patterns = [
            (r'(?:on[- ]?handover|handover\s+payment)', "On Handover"),
            (r'(?:Q[1-8]|quarter\s*[1-8])', None),
            (r'(?:booking|down\s*payment|reservation)', "Booking / Down Payment"),
        ]
        for pattern, label in installment_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                if label:
                    data["installment_type"] = label
                else:
                    data["installment_type"] = m.group(0).upper()
                break

        # Payer name (from cheque context)
        payer_match = re.search(r'payer\s+name\s*:?\s*([A-Za-z\s]+?)(?:\n|,|$)', text, re.IGNORECASE)
        if payer_match:
            data["payer_name"] = payer_match.group(1).strip()

        return data

    # =================================================================
    # RESPONSE GENERATION
    # =================================================================

    def _generate_response(self, workflow: str, client_name: str, data: dict) -> tuple:
        """Generate a draft email response based on the workflow."""
        name = client_name or "Valued Client"
        unit = data.get("unit_no", "[UNIT_NO]")

        if workflow == "1_payment_proof":
            return (
                "Re: Payment Proof Received",
                f"Dear {name},\n\nGood day!\n\nThank you for sharing the proof of transfer. Please be informed that we will notify you once we receive confirmation from the developer's relationship assistant that the payment has been credited to the escrow account.\n\nRegards"
            )

        elif workflow == "4_soa_request":
            return (
                f"Re: Statement of Account - Century Unit No.{unit}",
                f"Dear {name},\n\nGood day.\n\nAs requested please see below the details of the payments due and attached is the SOA for your reference.\n\nUnit: {unit}\n\nINSTALLMENTS | INSTALLMENT AMOUNT | DUE DATE\nOn Handover | AED [AMOUNT] | [DATE]\nQ1 - 3 months from Handover | AED [AMOUNT] | [DATE]\nQ2 - 6 months from Handover | AED [AMOUNT] | [DATE]\nQ3 - 9 months from Handover | AED [AMOUNT] | [DATE]\nQ4 - 12 months from Handover | AED [AMOUNT] | [DATE]\n\nIf you need further clarification or assistance, please do not hesitate to reach out.\n\nRegards"
            )

        elif workflow == "3_bounced_cheque":
            cheque_no = data.get("cheque_no", "[CHQ_NO]")
            amount = data.get("amount", "[AMOUNT]")
            reason = data.get("bounce_reason", "[BOUNCE_REASON]")
            payer = data.get("payer_name", "[PAYER_NAME]")

            return (
                f"Cheque Return Notification - Century Unit No.{unit}",
                f'Dear {name},\n\nGood day!\n\nWe would like to inform you that Cheque No.{cheque_no}, issued under the payer name {payer}, amounting to AED {amount}, has been returned by the bank due to the following reason: "{reason}".\n\nAccording to the signed Sales and Purchase Agreement (SPA), failure to settle this amount will incur a developer compensation charge of two percent (2%) per month compounded quarterly.\n\nTo avoid accruing additional charges, we kindly urge you to make the payment at your earliest convenience.\n\nShould you have any questions or require further clarification, please do not hesitate to contact us or reply to this email directly.\n\nThank you'
            )

        elif workflow == "1b_receipt_request":
            return (
                f"Re: Payment Receipt - Century Unit No.{unit}",
                f"Dear {name},\n\nGood day!\n\nWe are following up with the developer's relationship assistant to confirm the payment has been credited to the escrow account. Once confirmed, we will share the payment receipt along with the updated Statement of Account (SOA).\n\nWe appreciate your patience and will get back to you shortly.\n\nRegards"
            )

        elif workflow == "4b_escrow_details":
            escrow = CENTURY_PROJECT["escrow_account"]
            return (
                "Re: Escrow Account Details - Century",
                f"Dear {name},\n\nGood day!\n\nPlease find below the escrow account details for making the payment:\n\nAccount Name: {escrow['name']}\nBank: {escrow['bank']}\nBranch: {escrow['branch']}\nIBAN: AE650260000205879166402\n\nPlease ensure to mention your unit number ({unit}) in the transfer reference/description for easy identification.\n\nOnce the transfer is made, kindly share the proof of payment so we can track it.\n\nRegards"
            )

        elif workflow == "5b_cheque_replacement":
            return (
                f"Re: Cheque Replacement - Century Unit No.{unit}",
                f"Dear {name},\n\nGood day!\n\nThank you for informing us. We have noted the cheque replacement request for Unit No.{unit}. The old cheque will be added to our replacement list for the next collection run with the developer team.\n\nPlease ensure the bank transfer is made to the escrow account and share the proof of payment once completed.\n\nRegards"
            )

        elif workflow == "7_handover":
            return (
                f"Re: Handover Update - Century Unit No.{unit}",
                f"Dear {name},\n\nGood Day.\n\nAs part of the handover update, please find below the current status of your unit {unit} and the next steps required to proceed toward key handover.\n\n1. Current Handover Status\n\nUtility Activation Status:\n1) DEWA #: [Pending/Activated]\n2) Empower #: [Pending/Activated]\n\nHome Orientation: [Pending/Completed]\n\nNext Step:\nOnce both utilities are activated, you may proceed to book your home orientation appointment through the link below:\n{CALENDLY_HOME_ORIENTATION}\n\n2. Outstanding Payment Details\n\nAs per our records, the following amount remains outstanding:\nOutstanding Amount: AED [AMOUNT]\nInstallment Type: [INSTALLMENT_TYPE]\nDue Date: [DATE]\n\nShould you require any clarification or assistance, please feel free to reach out.\n\nWarm regards,"
            )

        elif workflow == "8_commission":
            return (
                "Re: Commission Follow-Up",
                f"Dear {name},\n\nGood day!\n\nThank you for your follow-up. We have forwarded your inquiry to our accounting team and will provide an update on the commission payment status shortly.\n\nRegards"
            )

        elif workflow == "6_bank_reconciliation":
            return (
                "Request for Updated Bank Statement",
                "Dear Geo,\n\nGood Day.\n\nKindly share the updated bank statement as of today.\n\nThanks & Regards"
            )

        elif workflow == "2_cash_collection":
            return (
                "Century -- Cash Collection List & PDC Requirements",
                f"Dear Century Team,\n\nGood day!\n\nSharing with you the list of the units for cash collection along with the customer details and breakdown for your reference.\n\nKindly use the link below to book an appointment for the cash collection:\n{CALENDLY_PAYMENT}\n\n[Collection details to be populated]\n\nRegards"
            )

        elif workflow == "5_cheque_due_date":
            return (
                "Re: Cheque Due Dates",
                f"Dear Team,\n\nGood day.\n\nPlease find below the cheque due dates for the current month:\n\n[Due date details to be populated]\n\nRegards"
            )

        return ("", "")

    # =================================================================
    # SUPABASE PERSISTENCE
    # =================================================================

    def save_classified_email(self, classified: ClassifiedEmail) -> Optional[dict]:
        """Save a classified email and its draft to Supabase."""
        if not self.sb:
            return None

        try:
            # Save email
            email_record = {
                "message_id": classified.message_id,
                "thread_id": classified.thread_id,
                "from_addr": classified.from_addr,
                "from_name": classified.from_name,
                "to_addr": classified.to_addr,
                "subject": classified.subject,
                "body_preview": classified.body_preview[:2000],
                "date": classified.date or None,
                "workflow": classified.workflow,
                "workflow_label": classified.workflow_label or WORKFLOW_LABELS.get(classified.workflow, ""),
                "confidence": classified.confidence,
                "suggested_action": classified.suggested_action,
                "extracted_data": classified.extracted_data,
                "status": "new",
            }

            resp = self.sb.table("amit_emails").upsert(
                email_record, on_conflict="message_id"
            ).execute()

            email_row = resp.data[0] if resp.data else None
            if not email_row:
                return None

            email_id = email_row["id"]

            # Save draft if we have one
            if classified.draft_response:
                draft_record = {
                    "email_id": email_id,
                    "draft_subject": classified.draft_subject,
                    "draft_body": classified.draft_response,
                    "to_addr": classified.from_addr,
                    "reply_to_thread_id": classified.thread_id,
                    "status": "pending",
                }
                self.sb.table("amit_drafts").insert(draft_record).execute()

            # Log action
            self.sb.table("amit_actions").insert({
                "email_id": email_id,
                "action_type": "classify",
                "details": {
                    "workflow": classified.workflow,
                    "confidence": classified.confidence,
                    "method": classified.classification_method,
                },
                "performed_by": "agent",
            }).execute()

            return email_row

        except Exception as e:
            import traceback
            logger.error(f"Supabase save error: {e}")
            traceback.print_exc()
            return None

    # =================================================================
    # GMAIL MESSAGE PROCESSING
    # =================================================================

    def process_gmail_message(self, gmail_data: dict,
                              use_claude: bool = True) -> ClassifiedEmail:
        """Process a raw Gmail message (from MCP or API).

        gmail_data should contain:
        - messageId, threadId
        - from (email), fromName
        - to, subject, body/snippet
        - date
        """
        classified = self.classify_email(
            message_id=gmail_data.get("messageId", gmail_data.get("message_id", "")),
            thread_id=gmail_data.get("threadId", gmail_data.get("thread_id", "")),
            from_addr=gmail_data.get("from", gmail_data.get("from_addr", "")),
            from_name=gmail_data.get("fromName", gmail_data.get("from_name", "")),
            to_addr=gmail_data.get("to", gmail_data.get("to_addr", "")),
            subject=gmail_data.get("subject", ""),
            body=gmail_data.get("body", gmail_data.get("snippet", "")),
            date=gmail_data.get("date", ""),
            use_claude=use_claude,
        )

        # Save to Supabase
        self.save_classified_email(classified)

        return classified

    # =================================================================
    # BATCH OPERATIONS
    # =================================================================

    def scan_inbox(self, emails: list[dict],
                   use_claude: bool = True) -> list[ClassifiedEmail]:
        """Classify a batch of emails from the inbox."""
        results = []
        for email in emails:
            classified = self.process_gmail_message(email, use_claude=use_claude)
            results.append(classified)
        return results

    def get_dashboard(self) -> dict:
        """Get a summary of all classified emails and suggested actions."""
        by_workflow = {}
        by_action = {"auto_reply": [], "draft_reply": [], "escalate": [], "info_only": []}

        for ce in self.classified_emails:
            wf = ce.workflow
            if wf not in by_workflow:
                by_workflow[wf] = []
            by_workflow[wf].append(ce.to_dict())

            action = ce.suggested_action
            if action in by_action:
                by_action[action].append(ce.to_dict())

        return {
            "total_emails": len(self.classified_emails),
            "by_workflow": {k: len(v) for k, v in by_workflow.items()},
            "by_action": {k: len(v) for k, v in by_action.items()},
            "auto_replies_ready": len(by_action["auto_reply"]),
            "drafts_for_review": len(by_action["draft_reply"]),
            "escalations": len(by_action["escalate"]),
            "details": {
                "auto_reply": by_action["auto_reply"][:20],
                "draft_reply": by_action["draft_reply"][:20],
                "escalate": by_action["escalate"][:20],
            },
        }
