"""
fam Properties -- Payment Collector Agent Configuration
Multi-project payment structure, stakeholder contacts, email templates,
and matching rules for bank statement reconciliation.

Supports multiple projects (Century, etc.) via PROJECT_REGISTRY.
"""

# =============================================================================
# PROJECT: CENTURY (Business Bay)
# =============================================================================
CENTURY_PROJECT = {
    "name": "Century",
    "location": "Business Bay, Dubai",
    "developer": "Al Shafar National Contracting (ASNC)",
    "total_units": 180,
    "floors": "2-18",
    "escrow_account": {
        "name": "CENTURY - ESCROW ACCOUNT",
        "bank": "Emirates NBD Bank (PJSC)",
        "branch": "ENBD Group HO Branch, Baniyas Road, Deira, Dubai",
    },
}

# =============================================================================
# STAKEHOLDERS
# =============================================================================
STAKEHOLDERS = {
    "developer": [
        {"name": "Geo John", "email": "Geo@asnc.ae", "role": "Main developer contact"},
        {"name": "Jamaluddeen", "email": "Accounts1@binshafar.ae", "role": "Accountant (cash/cheques)"},
        {"name": "Ananthukrishna", "email": "accounts3@binshafar.ae", "role": "Cheque tracking, bounce alerts"},
        {"name": "", "email": "accounts2@binshafar.ae", "role": "Secondary accounts"},
        {"name": "Bharat", "email": "bharat@dore.ae", "role": "Cash collection representative"},
        {"name": "Wilson", "email": "manager@dore.ae", "role": "Dore Manager"},
    ],
    "internal": [
        {"name": "Alora Tupas Rias", "email": "alora.r@famproperties.com", "role": "Senior Operations Executive"},
        {"name": "Nancy H.", "email": "nancy.h@famproperties.com", "role": "Daily Cash Report, client comms"},
        {"name": "Mohamed Elshiekh", "email": "mohamed.lshiekh@famproperties.com", "role": "Operations Executive"},
        {"name": "Raed Hechmi", "email": "raed.h@famproperties.com", "role": "Operations lead"},
        {"name": "Francesco Ferretti", "email": "francesco@famproperties.com", "role": "Managing Director"},
    ],
    "group_inboxes": {
        "crm": "ma.crm@famproperties.com",
        "accounting": "ma.accounting@famproperties.com",
    },
}

# Cash collection email recipients
CASH_COLLECTION_TO = [
    "Geo@asnc.ae",
    "Accounts1@binshafar.ae",
    "bharat@dore.ae",
    "accounts2@binshafar.ae",
    "accounts3@binshafar.ae",
    "manager@dore.ae",
]
CASH_COLLECTION_CC = [
    "ma.crm@famproperties.com",
    "mohamed.lshiekh@famproperties.com",
    "nancy.h@famproperties.com",
    "ma.accounting@famproperties.com",
]

# =============================================================================
# CALENDLY LINKS
# =============================================================================
CALENDLY_PAYMENT = "https://calendly.com/d/ct95-qvj-jss/schedule-your-payment-appointment-century"
CALENDLY_HOME_ORIENTATION = "https://calendly.com/d/ctqm-p3k-m9d/schedule-your-home-orientation-appointment-century"

# =============================================================================
# DAILY CASH REPORT (Google Sheet)
# =============================================================================
DAILY_CASH_REPORT_SHEET_ID = "1iJ4kdXIpo1CsqzBTv1EZarn6CkSYhiefnMd-6Z9BQoM"
DAILY_CASH_REPORT_GID = "1463283676"

# =============================================================================
# INSTALLMENT STRUCTURE
# =============================================================================
# Century payment plan: pre-handover milestones + on-handover + post-handover quarterly
INSTALLMENT_TYPES = [
    # Pre-handover (construction milestones)
    {"id": "pre_q1", "label": "Q1 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q2", "label": "Q2 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q3", "label": "Q3 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q4", "label": "Q4 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q5", "label": "Q5 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q6", "label": "Q6 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q7", "label": "Q7 - Pre-Handover", "phase": "pre_handover"},
    {"id": "pre_q8", "label": "Q8 - Pre-Handover", "phase": "pre_handover"},
    # On Handover
    {"id": "on_handover", "label": "On Handover", "phase": "handover"},
    # Post-handover (quarterly, ~2 years)
    {"id": "post_q1", "label": "Q1 - 3 months from Handover", "phase": "post_handover", "months_after": 3},
    {"id": "post_q2", "label": "Q2 - 6 months from Handover", "phase": "post_handover", "months_after": 6},
    {"id": "post_q3", "label": "Q3 - 9 months from Handover", "phase": "post_handover", "months_after": 9},
    {"id": "post_q4", "label": "Q4 - 12 months from Handover", "phase": "post_handover", "months_after": 12},
    {"id": "post_q5", "label": "Q5 - 15 months from Handover", "phase": "post_handover", "months_after": 15},
    {"id": "post_q6", "label": "Q6 - 18 months from Handover", "phase": "post_handover", "months_after": 18},
    {"id": "post_q7", "label": "Q7 - 21 months from Handover", "phase": "post_handover", "months_after": 21},
    {"id": "post_q8", "label": "Q8 - 24 months from Handover", "phase": "post_handover", "months_after": 24},
]

# SPA penalty clause
SPA_PENALTY = {
    "rate_pct_monthly": 2,
    "compounding": "quarterly",
    "clause_ref": "Clause 5.2 of SPA",
}

# =============================================================================
# PAYMENT MATCHING RULES
# =============================================================================
MATCHING_RULES = {
    # Phase 1: Direct match -- unit number found in transaction description
    "unit_pattern": r"(?:unit|apt|apartment|flat)?\s*#?\s*(\d{3,4}[A-Za-z]?)",
    # Phase 2: Amount tolerance for fuzzy matching (AED)
    "amount_tolerance_aed": 100,
    # Phase 3: Confidence thresholds
    "auto_match_confidence": 0.90,    # Above this -> auto-match
    "review_confidence": 0.60,        # Between review and auto -> flag for review
    "reject_confidence": 0.60,        # Below this -> unmatched
}

# =============================================================================
# EMAIL TEMPLATES
# =============================================================================
EMAIL_TEMPLATES = {
    "payment_proof_ack": {
        "subject": "[fam Properties] Payment Proof Received",
        "body": """Dear Valued Client,

Good day!

Thank you for sharing the proof of transfer. Please be informed that we will notify you once we receive confirmation from the developer's relationship assistant that the payment has been credited to the escrow account.

Regards""",
    },

    "payment_receipt_delivery": {
        "subject": "[fam Properties] Payment Receipt -- Century Unit No.{unit_no}",
        "body": """Dear Valued Client,

Good day!

Please find attached the payment receipt for the amount paid towards {installment_type} Installment for Century Unit No.{unit_no}. Also attached is the updated SOA for your reference.

Kindly acknowledge receipt of this email.

Regards""",
    },

    "bounced_cheque": {
        "subject": "[fam Properties] Cheque Return Notification -- Century Unit No.{unit_no}",
        "body": """Dear Valued Client,

Good day!

We would like to inform you that Cheque No.{cheque_no}, issued under the payer name {payer_name}, amounting to AED {amount}, has been returned by the bank due to the following reason: "{bounce_reason}".

{cheque_table}

According to the signed Sales and Purchase Agreement (SPA), failure to settle this amount will incur a developer compensation charge of two percent (2%) per month compounded quarterly.

To avoid accruing additional charges, we kindly urge you to make the payment at your earliest convenience.

Should you have any questions or require further clarification, please do not hesitate to contact us or reply to this email directly.

Thank you""",
    },

    "soa_delivery": {
        "subject": "[fam Properties] Statement of Account -- Century Unit No.{unit_no}",
        "body": """Dear Valued Client,

Good day.

As requested please see below the details of the payments due and attached is the SOA for your reference.

Unit: {unit_no}

{payment_schedule_table}

If you need further clarification or assistance, please do not hesitate to reach out.

Regards""",
    },

    "bank_statement_request": {
        "subject": "Request for Updated Bank Statement",
        "body": """Dear Geo,

Good Day.

Kindly share the updated bank statement as of today.

Thanks & Regards""",
    },

    "cash_collection": {
        "subject": "Century -- Cash Collection List & PDC Requirements",
        "body": """Dear Century Team,

Good day!

Sharing with you the list of the units for cash collection along with the customer details and breakdown for your reference.

Kindly use the link below to book an appointment for the cash collection:
{calendly_link}

{collection_table}

{cheques_to_replace}

{cheques_to_collect}

Regards""",
    },

    "weekly_handover_status": {
        "subject": "[fam Properties] Handover Update -- Century Unit No.{unit_no}",
        "body": """Dear Valued Client,

Good Day.

As part of the handover update, please find below the current status of your unit {unit_no} and the next steps required to proceed toward key handover.

1. Current Handover Status

Utility Activation Status:
1) DEWA # {dewa_number}: {dewa_status}
2) Empower # {empower_number}: {empower_status}

Home Orientation: {orientation_status}

Next Step:
Once both utilities are activated, you may proceed to book your home orientation appointment through the link below:
{calendly_link}

2. Outstanding Payment Details

As per our records, the following amount remains outstanding:
Outstanding Amount: AED {outstanding_amount}
Installment Type: {installment_type}
Due Date: {due_date}

We request you to clear the outstanding balance at the earliest to ensure there are no delays in proceeding with the handover.

3. Post-Dated Cheques (PDCs) Requirement

Kindly arrange the required PDCs as per your payment schedule:

{pdc_table}

Please ensure cheques are submitted at the earliest to avoid any delay in the handover process.
PDCs Submission Link: {calendly_payment_link}

Our objective is to support you in completing the remaining formalities smoothly and progressing toward key collection at the earliest.

Should you require any clarification or assistance, please feel free to reach out.

Warm regards,""",
    },

    "reconciliation_summary": {
        "subject": "Century -- Reconciled Bank Statement ({date_range})",
        "body": """Dear Century Team,

Good day!

Please find below the reconciled bank statement for the period {date_range}. Unit details have been matched next to each respective transaction.

{reconciliation_table}

Summary:
- Total credits processed: {total_credits}
- Matched to units: {matched_count}
- Unmatched (pending identification): {unmatched_count}
- Total amount reconciled: AED {total_amount}

Regards""",
    },
}

# =============================================================================
# DECISION RULES
# =============================================================================
DECISION_RULES = {
    "payment_not_confirmed": "Respond with acknowledgment template. Do NOT issue receipt.",
    "cheque_bounced": "Immediately notify client with SPA penalty warning + notify developer.",
    "payment_extension": "Escalate to developer. Developer may approve or deny.",
    "no_reference": "Ask developer to check. Follow up with client for details.",
    "escrow_details": "Share ENBD escrow details (Century Escrow Account).",
    "cheque_replacement": "Add to 'cheques to be replaced' list for next collection run.",
    "poa_handover": "Must be NOTARIZED Power of Attorney. Simple written authorization not accepted.",
    "spa_dispute": "Reference specific SPA clauses. Escalate to Alora/Francesco if client is aggressive.",
}

# =============================================================================
# MULTI-PROJECT REGISTRY
# =============================================================================
# Each project can have its own stakeholders, installments, and templates.
# The agent auto-detects the project from the master sheet or SF lookup.
PROJECT_REGISTRY = {
    "CENTURY": {
        "project": CENTURY_PROJECT,
        "stakeholders": STAKEHOLDERS,
        "installment_types": INSTALLMENT_TYPES,
        "matching_rules": MATCHING_RULES,
        "spa_penalty": SPA_PENALTY,
        "email_templates": EMAIL_TEMPLATES,
        "decision_rules": DECISION_RULES,
        "cash_collection_to": CASH_COLLECTION_TO,
        "cash_collection_cc": CASH_COLLECTION_CC,
        "calendly_payment": CALENDLY_PAYMENT,
        "calendly_home_orientation": CALENDLY_HOME_ORIENTATION,
    },
    # Add more projects here as needed:
    # "PROJECT_X": { ... }
}

def get_project_config(project_name: str) -> dict:
    """Get configuration for a specific project. Falls back to CENTURY defaults."""
    return PROJECT_REGISTRY.get(project_name.upper(), PROJECT_REGISTRY.get("CENTURY", {}))

# =============================================================================
# COMMON ARABIC NAME VARIANTS (for fuzzy matching)
# =============================================================================
NAME_VARIANTS = {
    "MOHAMMED": ["MOHAMMAD", "MOHAMED", "MUHAMMAD", "MUHAMMED", "MOHAMAD"],
    "AHMED": ["AHMAD", "AHAMED"],
    "ALI": ["ALY"],
    "ABDEL": ["ABDAL", "ABDUL", "ABD"],
    "HASSAN": ["HASAN"],
    "HUSSEIN": ["HUSAIN", "HUSSAIN", "HUSEIN"],
    "KHALID": ["KHALED"],
    "SAEED": ["SAID", "SAEID"],
    "NASSER": ["NASIR", "NASR"],
    "OMAR": ["UMAR"],
    "IBRAHIM": ["EBRAHIM"],
    "YOUSEF": ["YUSUF", "YOUSSEF", "YOUSUF"],
    "FATIMA": ["FATMA"],
    "AISHA": ["AYSHA", "AESHA"],
    "HAIDAR": ["HAIDER", "HAYDAR"],
    "SALEH": ["SALIH", "SALAH"],
    "JAMAL": ["GAMAL", "GAMMAL"],
    "KARIM": ["KAREEM"],
    "RASHID": ["RASHED", "RASHEED"],
    "WALID": ["WALEED"],
    "TARIQ": ["TAREK", "TAREQ"],
    "MAJID": ["MAJED", "MAGED"],
    "HAMAD": ["HAMMAD", "HAMID"],
    "FAISAL": ["FAIZEL", "FAYSAL"],
    # Russian name variants (patronymic endings)
    "PETROVA": ["PETROVNA", "PETROV"],
    "IVANOVA": ["IVANOVNA", "IVANOV"],
    "SMIRNOVA": ["SMIRNOVNA", "SMIRNOV"],
    "KUZNETSOVA": ["KUZNETSOVNA", "KUZNETSOV"],
    # Common international variants
    "JOHNSON": ["JONSON", "JOHNSEN"],
    "WILSON": ["WILLSON"],
    "THOMAS": ["TOMAS"],
}
