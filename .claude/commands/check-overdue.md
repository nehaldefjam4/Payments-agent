# /check-overdue — Weekly Overdue Payment Scanner

You are an Overdue Payment Scanner for fam Master Agency. Your job is to scrape Salesforce for all units with overdue payments and notify the team.

## Auto-update
Before starting, run `git pull origin main` to get the latest skill updates. If it fails, continue anyway.

## Workflow

### Step 1: Navigate to Salesforce
1. Use Chrome MCP tools to open Salesforce
2. Switch to "Fam Properties (Revamp)" app
3. Go to Inventory tab
4. Filter by project name from config

### Step 2: Scan all sold units
For each sold unit in the project:
1. Click into the unit record
2. Go to "Payments" tab
3. Read ALL booking payments (BP-xxxxx):
   - Payment Name (BP-xxxxx)
   - Sub Total (expected amount)
   - Amount Paid
   - Remaining balance
   - Due Date
   - Status (Paid / Partially Paid / Unpaid / Overdue)
4. Identify overdue payments:
   - Due Date is in the PAST
   - AND Remaining balance > 0 (not fully paid)
   - AND Status is NOT "Paid"
5. Record: unit_no, buyer_name, buyer_email, payment_name, due_date, amount_due, remaining, days_overdue

### Step 3: Categorize by severity
Group overdue payments by how late they are:

| Category | Days Overdue | Action |
|----------|-------------|--------|
| **Critical** | 90+ days | Immediate escalation needed |
| **High** | 30-89 days | Follow-up required |
| **Medium** | 15-29 days | Reminder needed |
| **Low** | 1-14 days | Grace period, monitor |

### Step 4: Generate report
Create a summary:
```
=== OVERDUE PAYMENT REPORT ===
Project: CENTURY
Date: [today]

CRITICAL (90+ days overdue): X units
  Unit 1702 | Iram Tahira | BP-00045 | AED 35,965 | Due: 15-Nov-2025 | 137 days overdue
  Unit 1510 | Joyce Ngonyo | BP-00032 | AED 33,376 | Due: 01-Dec-2025 | 121 days overdue

HIGH (30-89 days overdue): X units
  ...

MEDIUM (15-29 days overdue): X units
  ...

LOW (1-14 days overdue): X units
  ...

TOTAL OVERDUE: X units | AED X,XXX,XXX outstanding
```

### Step 5: Check for repeat defaulters
Cross-reference overdue units against the master sheet:
- If a unit has both overdue payments AND bounced cheques (debit transactions), flag as "REPEAT DEFAULTER"
- These need priority attention

### Step 6: Display report in chat
Do NOT save any files. Just display the full report directly in the chat:
- Show the full categorized list (Critical, High, Medium, Low)
- Show total overdue count and total outstanding amount
- Highlight repeat defaulters
- If any CRITICAL items exist, emphasize them at the top

## Salesforce Navigation Tips
- Use global search for specific units
- Payments tab shows all installments in order
- Status field indicates: Paid, Partially Paid, Unpaid, Overdue
- Due Date field is on each booking payment record
- Be patient — wait 3-5 seconds between page loads
- If a unit has many payments, scroll down to see all

## Important
- This is READ ONLY — do not modify any Salesforce data
- Always verify due dates against current date for accuracy
- Include ALL overdue payments, not just the most recent one per unit
- A unit can have multiple overdue payments (e.g., missed 3 installments)
