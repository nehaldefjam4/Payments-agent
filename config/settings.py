"""
fam Properties — Document Checker Agent Configuration
All Dubai real estate document requirements, validation rules, and approval thresholds.
"""

# =============================================================================
# ANTHROPIC API
# =============================================================================
ANTHROPIC_API_KEY = "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"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_MAX_TOKENS = 4096          # Max tokens per Claude response in the agentic loop
AGENT_MAX_TURNS = 15              # Safety limit: max tool-use round-trips

# =============================================================================
# SUPABASE
# =============================================================================
SUPABASE_URL = "https://uqcteifgiyoibduveqdk.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVxY3RlaWZnaXlvaWJkdXZlcWRrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MjA2NDYsImV4cCI6MjA4OTM5NjY0Nn0.Z4snE56jxbACi_gihyCr7np0ZEnWsjckKPA7ykT2deY"

# =============================================================================
# DOCUMENT REQUIREMENTS BY TRANSACTION TYPE
# =============================================================================
DOCUMENT_REQUIREMENTS = {
    "residential_sale": {
        "label": "Residential Sale",
        "required": [
            {"id": "emirates_id", "name": "Emirates ID", "description": "Valid Emirates ID (front and back)", "expiry_check": True},
            {"id": "passport", "name": "Passport Copy", "description": "Valid passport with minimum 6 months validity", "expiry_check": True},
            {"id": "title_deed", "name": "Title Deed", "description": "Original title deed or certified copy from DLD"},
            {"id": "noc_developer", "name": "NOC from Developer", "description": "No Objection Certificate from the developer"},
            {"id": "spa", "name": "Sale & Purchase Agreement (SPA)", "description": "Signed SPA between buyer and seller"},
            {"id": "form_f", "name": "Form F (Listing Agreement)", "description": "RERA Form F signed by seller and agent"},
            {"id": "form_a", "name": "Form A (Buyer Agreement)", "description": "RERA Form A signed by buyer and agent"},
            {"id": "valuation_report", "name": "Property Valuation Report", "description": "Bank-approved valuation report"},
            {"id": "mortgage_clearance", "name": "Mortgage Clearance Letter", "description": "If property has existing mortgage — clearance or liability letter"},
            {"id": "agency_agreement", "name": "Agency Agreement", "description": "Signed agreement between agency and client"},
        ],
        "optional": [
            {"id": "power_of_attorney", "name": "Power of Attorney", "description": "If representative is acting on behalf of owner", "expiry_check": True},
            {"id": "company_trade_license", "name": "Company Trade License", "description": "If buyer/seller is a company", "expiry_check": True},
            {"id": "board_resolution", "name": "Board Resolution", "description": "If buyer/seller is a company"},
            {"id": "visa_copy", "name": "Visa Copy", "description": "UAE residence visa copy"},
        ],
    },
    "residential_rent": {
        "label": "Residential Rent",
        "required": [
            {"id": "emirates_id", "name": "Emirates ID", "description": "Valid Emirates ID (front and back)", "expiry_check": True},
            {"id": "passport", "name": "Passport Copy", "description": "Valid passport copy", "expiry_check": True},
            {"id": "visa_copy", "name": "Visa Copy", "description": "Valid UAE residence visa", "expiry_check": True},
            {"id": "tenancy_contract", "name": "Tenancy Contract (Ejari)", "description": "Standard Ejari tenancy contract"},
            {"id": "form_a", "name": "Form A (Tenant Agreement)", "description": "RERA Form A signed by tenant and agent"},
            {"id": "security_deposit_receipt", "name": "Security Deposit Receipt", "description": "Proof of security deposit payment"},
            {"id": "title_deed", "name": "Title Deed", "description": "Copy of property title deed"},
        ],
        "optional": [
            {"id": "salary_certificate", "name": "Salary Certificate", "description": "Employment/salary verification"},
            {"id": "bank_statement", "name": "Bank Statement", "description": "Last 3 months bank statement"},
            {"id": "company_trade_license", "name": "Company Trade License", "description": "If tenant is a company", "expiry_check": True},
        ],
    },
    "commercial_sale": {
        "label": "Commercial Sale",
        "required": [
            {"id": "emirates_id", "name": "Emirates ID", "description": "Valid Emirates ID (front and back)", "expiry_check": True},
            {"id": "passport", "name": "Passport Copy", "description": "Valid passport with minimum 6 months validity", "expiry_check": True},
            {"id": "company_trade_license", "name": "Company Trade License", "description": "Valid trade license of the company", "expiry_check": True},
            {"id": "board_resolution", "name": "Board Resolution", "description": "Board resolution authorizing the transaction"},
            {"id": "title_deed", "name": "Title Deed", "description": "Original title deed or certified copy"},
            {"id": "noc_developer", "name": "NOC from Developer", "description": "No Objection Certificate from the developer"},
            {"id": "spa", "name": "Sale & Purchase Agreement (SPA)", "description": "Signed SPA"},
            {"id": "form_f", "name": "Form F (Listing Agreement)", "description": "RERA Form F"},
            {"id": "form_a", "name": "Form A (Buyer Agreement)", "description": "RERA Form A"},
            {"id": "agency_agreement", "name": "Agency Agreement", "description": "Signed agreement between agency and client"},
            {"id": "moa_aoa", "name": "MOA / AOA", "description": "Memorandum and Articles of Association"},
        ],
        "optional": [
            {"id": "power_of_attorney", "name": "Power of Attorney", "description": "If representative is acting on behalf", "expiry_check": True},
            {"id": "valuation_report", "name": "Property Valuation Report", "description": "Bank-approved valuation"},
        ],
    },
    "off_plan_sale": {
        "label": "Off-Plan Sale",
        "required": [
            {"id": "emirates_id", "name": "Emirates ID", "description": "Valid Emirates ID (front and back)", "expiry_check": True},
            {"id": "passport", "name": "Passport Copy", "description": "Valid passport copy", "expiry_check": True},
            {"id": "reservation_form", "name": "Reservation Form", "description": "Developer's reservation/booking form"},
            {"id": "spa", "name": "Sale & Purchase Agreement (SPA)", "description": "SPA from developer"},
            {"id": "oqood_registration", "name": "Oqood Registration", "description": "DLD off-plan registration certificate"},
            {"id": "payment_plan", "name": "Payment Plan", "description": "Developer's payment schedule"},
            {"id": "form_a", "name": "Form A (Buyer Agreement)", "description": "RERA Form A"},
            {"id": "agency_agreement", "name": "Agency Agreement", "description": "Signed agency agreement"},
        ],
        "optional": [
            {"id": "noc_resale", "name": "NOC for Resale", "description": "If reselling off-plan unit before completion"},
            {"id": "payment_receipts", "name": "Payment Receipts", "description": "All payment receipts to developer"},
        ],
    },
}

# =============================================================================
# VALIDATION RULES
# =============================================================================
VALIDATION_RULES = {
    "expiry_buffer_days": 30,          # Documents must be valid for at least 30 more days
    "passport_validity_months": 6,      # Passport must have 6+ months validity
    "max_document_age_days": 90,        # Some docs must be issued within 90 days
    "allowed_file_types": [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc", ".tiff"],
    "max_file_size_mb": 25,
    "min_resolution_dpi": 150,          # Minimum scan quality
}

# =============================================================================
# APPROVAL LEVELS
# =============================================================================
APPROVAL_LEVELS = {
    "auto": {
        "level": 0,
        "label": "Auto-Approved",
        "description": "100% complete, all validations pass",
        "sla_minutes": 0,
    },
    "agent": {
        "level": 1,
        "label": "Agent Review",
        "description": "Minor issues — missing optional docs or near-expiry",
        "sla_minutes": 60,
        "approver_email": "agent.review@famproperties.com",
    },
    "manager": {
        "level": 2,
        "label": "Manager Review",
        "description": "Missing required docs or expired documents",
        "sla_minutes": 240,
        "approver_email": "manager.review@famproperties.com",
    },
    "director": {
        "level": 3,
        "label": "Director Review",
        "description": "Multiple critical issues or override requests",
        "sla_minutes": 480,
        "approver_email": "director.review@famproperties.com",
    },
}

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================
EMAIL_CONFIG = {
    "doc_checker_inbox": "doc.checker@famproperties.com",
    "ops_manager_inbox": "ops.manager@famproperties.com",
    "notifications_from": "doc.checker.agent@famproperties.com",
    "smtp_host": "",   # Set via environment
    "smtp_port": 587,
    "smtp_user": "",   # Set via environment
    "smtp_pass": "",   # Set via environment
}

# =============================================================================
# AGENT IDENTITY
# =============================================================================
AGENT_IDENTITY = {
    "name": "Payment Collector Agent",
    "role": "Autonomous payment reconciliation and client operations",
    "organization": "fam Master Agency",
    "version": "3.0.0",
}

# =============================================================================
# SALESFORCE CONFIGURATION
# =============================================================================
import os
SF_CONFIG = {
    "instance_url": "momentum-ability-3447.my.salesforce.com",
    "client_id": os.environ.get("SF_CLIENT_ID", ""),
    "client_secret": os.environ.get("SF_CLIENT_SECRET", ""),
    "username": os.environ.get("SF_USERNAME", ""),
    "password": os.environ.get("SF_PASSWORD", ""),
    "security_token": os.environ.get("SF_SECURITY_TOKEN", ""),
}

# Production mode — writes and emails enabled
SF_WRITE_MODE = os.environ.get("SF_WRITE_MODE", "true").lower() == "true"
EMAIL_LIVE_MODE = os.environ.get("EMAIL_LIVE_MODE", "true").lower() == "true"

# =============================================================================
# AI MATCHING CONFIGURATION
# =============================================================================
AI_MATCHING_PROMPT = """You are an AI payment matching agent for fam Master Agency.

Given a list of unmatched bank transactions and a knowledge base of unit→client mappings + expected payments, your job is to identify which unit each transaction belongs to.

Analysis approach:
1. Parse the transaction narration for any name fragments, unit references, or identifiers
2. Cross-reference names against the known client database (consider name variations, transliterations)
3. Check if the amount matches any pending installment for a unit
4. Consider that one transaction may cover multiple installments (split payment)
5. Common Arabic name variants: Mohammed/Mohamed/Muhammad, Ahmed/Ahmad, Ali/Aly, etc.

For each transaction, return:
- unit_no: the matched unit number (or "" if no match)
- confidence: 0.0 to 1.0
- reasoning: brief explanation of why this match was made
- installments_covered: list of installment types if identifiable

Return your analysis as a JSON array."""

# =============================================================================
# FILE WATCHING
# =============================================================================
INBOX_DIR = "inbox"          # Drop documents here
PROCESSED_DIR = "processed"  # Completed submissions moved here
WATCH_INTERVAL_SECONDS = 5
