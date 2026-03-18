#!/usr/bin/env python3
"""
fam Properties — Document Checker Agent
========================================
A fully functional, standalone AI agent for validating Dubai real estate
booking documents. Powered by Claude (Anthropic API).

Usage:
  python main.py                          # Interactive mode
  python main.py demo                     # Run full demo with sample documents
  python main.py check <folder> <type>    # Process a specific folder
  python main.py watch                    # Watch inbox folder for new submissions

Environment:
  ANTHROPIC_API_KEY=sk-ant-...            # Optional: enables Claude AI analysis

Transaction Types:
  residential_sale, residential_rent, commercial_sale, off_plan_sale
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.doc_checker import DocumentCheckerAgent
from config.settings import DOCUMENT_REQUIREMENTS, INBOX_DIR, PROCESSED_DIR


def create_sample_documents(base_dir: str, transaction_type: str = "residential_sale") -> str:
    """Create realistic sample document files for demo/testing."""
    submission_id = f"DEMO-{transaction_type}-{datetime.now().strftime('%H%M%S')}"
    folder = Path(base_dir) / submission_id
    folder.mkdir(parents=True, exist_ok=True)

    # Create sample PDFs/docs based on transaction type
    samples = {
        "residential_sale": [
            ("Emirates_ID_Front_Back.pdf", "emirates_id",
             "UNITED ARAB EMIRATES\nIDENTITY CARD\nName: Ahmed Al Maktoum\nID Number: 784-1985-1234567-1\nNationality: UAE\nDate of Birth: 15/03/1985\nExpiry Date: 20/06/2028"),
            ("Passport_Copy.pdf", "passport",
             "PASSPORT\nSurname: AL MAKTOUM\nGiven Names: AHMED\nNationality: UNITED ARAB EMIRATES\nDate of Birth: 15 MAR 1985\nPassport No: P1234567\nDate of Issue: 01 JAN 2023\nDate of Expiry: 01 JAN 2033"),
            ("Title_Deed_Unit_1204.pdf", "title_deed",
             "DUBAI LAND DEPARTMENT\nTITLE DEED\nDeed No: 2024/123456\nProperty: Unit 1204, Marina Heights Tower\nArea: Dubai Marina\nOwner: Ahmed Al Maktoum\nPlot No: 123\nRegistration Date: 15/01/2022"),
            ("SPA_Marina_Heights_1204.pdf", "spa",
             "SALE AND PURCHASE AGREEMENT\nSeller: Ahmed Al Maktoum\nBuyer: Sarah Williams\nProperty: Unit 1204, Marina Heights Tower\nPrice: AED 2,500,000\nDate: 01/03/2026"),
            ("Form_F_Listing.pdf", "form_f",
             "RERA FORM F\nLISTING AGREEMENT\nAgent: fam Properties\nBRN: 12345\nSeller: Ahmed Al Maktoum\nProperty: Unit 1204, Marina Heights\nList Price: AED 2,500,000"),
            ("Form_A_Buyer.pdf", "form_a",
             "RERA FORM A\nBUYER AGREEMENT\nAgent: fam Properties\nBuyer: Sarah Williams\nProperty: Unit 1204, Marina Heights\nDate: 01/03/2026"),
            ("Valuation_Report_1204.pdf", "valuation_report",
             "PROPERTY VALUATION REPORT\nProperty: Unit 1204, Marina Heights Tower\nValuation Date: 25/02/2026\nMarket Value: AED 2,450,000\nValued By: ABC Valuations LLC\nBank Reference: Mortgage Ref M-2026-789"),
            ("Agency_Agreement_fam.pdf", "agency_agreement",
             "AGENCY AGREEMENT\nBrokerage: fam Properties LLC\nBRN: 12345\nClient: Ahmed Al Maktoum\nService: Sale of Unit 1204\nCommission: 2%\nDate: 15/02/2026"),
            # Intentionally MISSING: noc_developer, mortgage_clearance
        ],
        "residential_rent": [
            ("Emirates_ID_Tenant.pdf", "emirates_id",
             "IDENTITY CARD\nName: John Smith\nID: 784-1990-9876543-1\nExpiry: 15/12/2027"),
            ("Passport_Tenant.pdf", "passport",
             "PASSPORT\nName: JOHN SMITH\nNationality: BRITISH\nPassport No: GB123456\nExpiry: 20/08/2030"),
            ("Visa_Copy_Tenant.pdf", "visa_copy",
             "UAE RESIDENCE VISA\nName: John Smith\nVisa No: 123/2024/456789\nExpiry: 01/06/2027"),
            ("Ejari_Tenancy_Contract.pdf", "tenancy_contract",
             "EJARI TENANCY CONTRACT\nTenant: John Smith\nLandlord: Ahmed Al Maktoum\nProperty: Apt 502, JBR Walk\nRent: AED 120,000/year\nDuration: 01/04/2026 - 31/03/2027"),
            ("Form_A_Tenant.pdf", "form_a",
             "RERA FORM A\nTENANT AGREEMENT\nAgent: fam Properties\nTenant: John Smith"),
            ("Security_Deposit_Receipt.pdf", "security_deposit_receipt",
             "SECURITY DEPOSIT RECEIPT\nTenant: John Smith\nAmount: AED 10,000\nDate: 15/03/2026"),
            ("Title_Deed_502.pdf", "title_deed",
             "TITLE DEED\nOwner: Ahmed Al Maktoum\nProperty: Apt 502, JBR Walk"),
        ],
        "off_plan_sale": [
            ("Emirates_ID.pdf", "emirates_id",
             "IDENTITY CARD\nName: Maria Garcia\nExpiry: 10/09/2028"),
            ("Passport.pdf", "passport",
             "PASSPORT\nName: MARIA GARCIA\nExpiry: 15/11/2031"),
            ("Reservation_Form_Creek_Views.pdf", "reservation_form",
             "RESERVATION FORM\nProject: Creek Views by Azizi\nUnit: 2BR-0815\nBuyer: Maria Garcia\nPrice: AED 1,800,000"),
            ("SPA_Creek_Views.pdf", "spa",
             "SALE AND PURCHASE AGREEMENT\nDeveloper: Azizi Developments\nBuyer: Maria Garcia\nUnit: 2BR-0815"),
            ("Oqood_Registration.pdf", "oqood_registration",
             "OQOOD CERTIFICATE\nDLD Registration No: OQ-2026-12345\nProject: Creek Views\nUnit: 2BR-0815"),
            ("Payment_Plan_Schedule.pdf", "payment_plan",
             "PAYMENT PLAN\n20% on booking\n30% during construction\n50% on handover"),
            ("Form_A_Buyer.pdf", "form_a",
             "RERA FORM A\nBuyer: Maria Garcia"),
            ("Agency_Agreement.pdf", "agency_agreement",
             "AGENCY AGREEMENT\nAgent: fam Properties\nClient: Maria Garcia"),
        ],
    }

    docs = samples.get(transaction_type, samples["residential_sale"])

    for filename, doc_type, content in docs:
        file_path = folder / filename
        file_path.write_text(content, encoding="utf-8")

    print(f"\n  Created {len(docs)} sample documents in: {folder}")
    return str(folder)


def run_demo():
    """Run a full demonstration of the Document Checker Agent."""
    print("\n" + "=" * 60)
    print("  fam Properties — Document Checker Agent DEMO")
    print("  " + "=" * 56)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        print("  Claude API:  ENABLED (intelligent analysis active)")
    else:
        print("  Claude API:  NOT SET (using rule-based analysis)")
        print("  Set ANTHROPIC_API_KEY environment variable for AI analysis")
    print("=" * 60)

    agent = DocumentCheckerAgent(api_key=api_key)

    # Demo 1: Residential Sale (missing some docs)
    print("\n" + "#" * 60)
    print("  DEMO 1: Residential Sale — Partial Submission")
    print("#" * 60)

    folder1 = create_sample_documents("demo_submissions", "residential_sale")
    result1 = agent.process_submission(
        folder_path=folder1,
        transaction_type="residential_sale",
        broker_name="Khalid Hassan",
        broker_email="khalid.h@broker-agency.ae",
        property_ref="Marina Heights — Unit 1204",
    )

    # Simulate approval
    if result1.get("approval_request"):
        req_id = result1["approval_request"]["id"]
        print(f"\n  Simulating manager approval for request {req_id}...")
        approval_result = agent.handle_approval_response(
            req_id, "approve",
            by="Sarah Manager",
            notes="NOC and mortgage clearance can follow — proceed with conditional approval",
        )
        print(f"  Approval result: {approval_result['status'].upper()}")

    # Demo 2: Residential Rent (complete)
    print("\n" + "#" * 60)
    print("  DEMO 2: Residential Rent — Complete Submission")
    print("#" * 60)

    folder2 = create_sample_documents("demo_submissions", "residential_rent")
    result2 = agent.process_submission(
        folder_path=folder2,
        transaction_type="residential_rent",
        broker_name="Lisa Chen",
        broker_email="lisa.c@broker-agency.ae",
        property_ref="JBR Walk — Apt 502",
    )

    # Demo 3: Off-Plan Sale
    print("\n" + "#" * 60)
    print("  DEMO 3: Off-Plan Sale — Full Submission")
    print("#" * 60)

    folder3 = create_sample_documents("demo_submissions", "off_plan_sale")
    result3 = agent.process_submission(
        folder_path=folder3,
        transaction_type="off_plan_sale",
        broker_name="Omar Farooq",
        broker_email="omar.f@partner-realty.ae",
        property_ref="Creek Views — Unit 2BR-0815",
    )

    # Dashboard
    print("\n" + "=" * 60)
    print("  AGENT DASHBOARD")
    print("=" * 60)
    dashboard = agent.get_dashboard()
    print(f"  Total Submissions:  {dashboard['total_submissions']}")
    print(f"  Approved:           {dashboard['by_status']['approved']}")
    print(f"  Pending:            {dashboard['by_status']['pending']}")
    print(f"  Emails Sent:        {dashboard['email_stats']['total_sent']}")
    print(f"  Approval Requests:  {dashboard['approval_stats']['total_requests']}")
    print(f"  SLA Violations:     {len(dashboard['sla_violations'])}")

    # Email log
    print(f"\n  --- ALL EMAILS SENT ---")
    for email in agent.email_service.get_all_emails():
        print(f"  [{email['id']}] To: {email['to']}")
        print(f"           Subject: {email['subject'][:60]}...")
        print()

    # Audit trail
    print(f"  --- AUDIT TRAIL ---")
    for event in agent.approval_engine.get_audit_log():
        print(f"  [{event['timestamp'][:19]}] {event['event']}")
        for k, v in event.items():
            if k not in ("timestamp", "event"):
                print(f"      {k}: {v}")
        print()

    # Save results
    results_path = Path("demo_results.json")
    all_results = {
        "demo_run_at": datetime.now().isoformat(),
        "submissions": {
            "residential_sale": result1,
            "residential_rent": result2,
            "off_plan_sale": result3,
        },
        "dashboard": dashboard,
        "emails": agent.email_service.get_all_emails(),
        "audit_trail": agent.approval_engine.get_audit_log(),
    }
    results_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n  Full results saved to: {results_path}")

    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)
    return all_results


def run_check(folder_path: str, transaction_type: str,
              broker_name: str = "Broker", broker_email: str = "broker@agency.ae"):
    """Process a specific folder of documents."""
    agent = DocumentCheckerAgent()
    result = agent.process_submission(
        folder_path=folder_path,
        transaction_type=transaction_type,
        broker_name=broker_name,
        broker_email=broker_email,
    )
    return result


def run_interactive():
    """Run the agent in interactive mode."""
    print("\n" + "=" * 60)
    print("  fam Properties — Document Checker Agent")
    print("  Interactive Mode")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if api_key:
        print("  Claude API: ENABLED")
    else:
        print("  Claude API: Not configured (set ANTHROPIC_API_KEY)")

    print("""
  Commands:
    demo                         Run full demo with sample documents
    check <folder> <type>        Check documents in a folder
    types                        List available transaction types
    requirements <type>          Show required documents for a type
    help                         Show this help
    quit                         Exit
    """)

    agent = DocumentCheckerAgent(api_key=api_key)

    while True:
        try:
            cmd = input("\n  agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not cmd:
            continue

        parts = cmd.split()
        command = parts[0].lower()

        if command in ("quit", "exit", "q"):
            print("  Goodbye!")
            break

        elif command == "demo":
            run_demo()

        elif command == "types":
            print("\n  Available transaction types:")
            for key, val in DOCUMENT_REQUIREMENTS.items():
                req_count = len(val["required"])
                opt_count = len(val.get("optional", []))
                print(f"    {key}: {val['label']} ({req_count} required, {opt_count} optional)")

        elif command == "requirements":
            if len(parts) < 2:
                print("  Usage: requirements <transaction_type>")
                continue
            tx_type = parts[1]
            reqs = DOCUMENT_REQUIREMENTS.get(tx_type)
            if not reqs:
                print(f"  Unknown type: {tx_type}")
                continue
            print(f"\n  {reqs['label']} — Required Documents:")
            for i, doc in enumerate(reqs["required"], 1):
                expiry = " [EXPIRY CHECK]" if doc.get("expiry_check") else ""
                print(f"    {i:2d}. {doc['name']}{expiry}")
                print(f"        {doc['description']}")
            if reqs.get("optional"):
                print(f"\n  Optional Documents:")
                for doc in reqs["optional"]:
                    print(f"    - {doc['name']}: {doc['description']}")

        elif command == "check":
            if len(parts) < 3:
                print("  Usage: check <folder_path> <transaction_type> [broker_name] [broker_email]")
                continue
            folder = parts[1]
            tx_type = parts[2]
            name = parts[3] if len(parts) > 3 else "Broker"
            email = parts[4] if len(parts) > 4 else "broker@agency.ae"

            if not Path(folder).is_dir():
                print(f"  Error: '{folder}' is not a directory")
                continue
            if tx_type not in DOCUMENT_REQUIREMENTS:
                print(f"  Error: Unknown type '{tx_type}'. Use 'types' to see available types.")
                continue

            run_check(folder, tx_type, name, email)

        elif command == "dashboard":
            dashboard = agent.get_dashboard()
            print(f"\n  Submissions: {dashboard['total_submissions']}")
            print(f"  Approved: {dashboard['by_status']['approved']}")
            print(f"  Pending:  {dashboard['by_status']['pending']}")
            print(f"  Emails:   {dashboard['email_stats']['total_sent']}")

        elif command == "help":
            print("""
  Commands:
    demo                         Run full demo with sample documents
    check <folder> <type>        Check documents in a folder
    types                        List available transaction types
    requirements <type>          Show required documents for a type
    dashboard                    Show agent dashboard
    help                         Show this help
    quit                         Exit
            """)

        else:
            print(f"  Unknown command: {command}. Type 'help' for available commands.")


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "demo":
            run_demo()
        elif command == "check":
            if len(sys.argv) < 4:
                print("Usage: python main.py check <folder_path> <transaction_type> [broker_name] [broker_email]")
                sys.exit(1)
            folder = sys.argv[2]
            tx_type = sys.argv[3]
            name = sys.argv[4] if len(sys.argv) > 4 else "Broker"
            email = sys.argv[5] if len(sys.argv) > 5 else "broker@agency.ae"
            run_check(folder, tx_type, name, email)
        elif command == "help":
            print(__doc__)
        else:
            print(f"Unknown command: {command}")
            print(__doc__)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
