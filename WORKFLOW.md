# Payments Agent — Full Workflow

## Overview

Automatically matches bank transactions to unit payments, updates the master escrow/corporate sheet with credits and debits, validates buyer names, and syncs payment status to Salesforce.

---

## 1. First-Time Setup (`/setup`)

```
User runs /setup
    |
    v
Asks: Master sheet path? --> C:\Users\...\Century-Escrow & Corporate Account.xlsx
    |
    v
Asks: Bank statement folder? --> C:\Users\...\Downloads\
    |
    v
Asks: Project name? --> CENTURY / CBC / THE 100 / MAG777
    |
    v
Asks: Salesforce access? --> yes/no
    |
    v
Saves payments-agent.config.json
    |
    v
DONE -- Ready to use /reconcile
```

---

## 2. Reconciliation (`/reconcile`)

```
/reconcile
    |
    v
[Step 0] Auto-update: git pull origin main
    |
    v
[Step 1] Find files
    |-- Reads payments-agent.config.json
    |-- Scans bank statement folder for new .xls/.xlsx files
    |-- Asks user to confirm escrow / corporate files
    |
    v
[Step 2] Credit Matching (API)
    |-- Sends master sheet + bank statement to API
    |-- API uses AI to match each credit to a unit/buyer:
    |     |-- Unit number in narration
    |     |-- Buyer name (fuzzy, substring, AI match)
    |     |-- Amount match against Salesforce KB
    |-- Returns: matched, unmatched, review items
    |
    v
[Step 3] Show Results to User
    |-- HIGH confidence (>65%): auto-accepted
    |-- LOW confidence (<65%): flagged for review with alternatives
    |-- UNMATCHED: asks user to identify unit
    |
    v
[Step 4] Save Master Sheet
    |-- Downloads updated sheet from API (base64)
    |-- Overwrites original master sheet
    |
    v
[Step 4a] Highlight Transactions
    |-- RED background: unmatched rows
    |-- YELLOW background: low confidence (<65%) rows
    |-- "NEW" in Inflow Status: successfully matched
    |
    v
[Step 4b] Sync Debits (Chronological Order)
    |-- Scans bank statement for ALL debit transactions:
    |     |-- Bounced cheques (CHEQUE RETURNED, OUTWARD REJECT)
    |     |-- Reimbursements / profit withdrawals
    |     |-- 5% retention transfers
    |     |-- Trust-to-retention transfers
    |-- Inserts debits at correct date position (interleaved with credits)
    |-- Verifies final running balance matches bank statement
    |
    v
[Step 4c] Validate Account Names
    |-- Checks for junk names ("CHQ NO", "TRANSFERIPI TT", etc.)
    |-- Fix: reuse name from existing rows for same unit
    |-- Fallback: query Salesforce for correct buyer name
    |-- Multi-buyer units: always include ALL buyer names
    |     |-- Unit 301 Group 1: Jitin Joshi + Nitin Mirchandani
    |     |-- Unit 301 Group 2: Ibrahim Bakr + Mohamed Fawzy
    |
    v
[Step 5] Salesforce Queue (Escrow only)
    |-- Shows units ready for SF update
    |-- Asks: "Update Salesforce for these units?"
    |-- If yes: queues for /sf-update
    |
    v
DONE -- Master sheet updated, balance verified
```

---

## 3. Salesforce Update (`/sf-update`)

```
/sf-update
    |
    v
Check pending units from reconciliation
    |
    v
For EACH unit:
    |
    |-- [A] Navigate Salesforce (Chrome + Claude extension)
    |     |-- Open Fam Properties (Revamp) app
    |     |-- Search unit number --> filter by project
    |     |-- Go to Payments tab
    |     |-- Find booking payment (BP-xxxxx)
    |     |-- Update "Amount Paid" if needed
    |
    |-- [B] Generate Receipt
    |     |-- Click "Generate Invoice"
    |     |-- Wait for PDF in Files section
    |
    |-- [C] Generate Statement
    |     |-- Go to Account Statements tab
    |     |-- Verify latest statement exists
    |
    |-- [D] Send Email to Buyer
    |     |-- Activity panel --> Email
    |     |-- To: buyer email
    |     |-- Subject: "Payment Receipt for [Project] Unit No. [Unit] | [Period]"
    |     |-- Attach: Receipt PDF + Statement PDF
    |     |-- Send
    |
    v
Mark receipt as "Done" in master sheet
    |
    v
DONE -- "X units updated in Salesforce, receipts generated and emailed"
```

---

## 4. Salesforce Sync (`/sf-sync`)

```
/sf-sync
    |
    v
Navigate to Salesforce --> Inventory tab
    |
    v
For each sold unit in project:
    |-- Extract: unit_no, purchaser_name, email, price, status
    |-- Extract payments: amount, paid, remaining, due_date, status
    |
    v
POST to API --> saves to knowledge base
    |
    v
DONE -- "Synced X units and Y payments for PROJECT"
```

*One-time per project. Refresh periodically for better matching.*

---

## 5. Email Monitoring (`/check-emails`)

```
/check-emails
    |
    v
Search Gmail for payment emails (last 24-48 hours)
    |
    v
Categorize each email:
    |-- Payment Proof Received --> draft acknowledgment
    |-- Receipt/SOA Request --> draft "will send once confirmed"
    |-- Payment Extension --> draft escalation
    |-- Bounced Cheque --> draft acknowledgment + internal review
    |-- Utility Activation --> draft next steps
    |
    v
Show drafts to user for approval
    |
    v
Send approved replies (CC: ma.crm@famproperties.com)
    |
    v
DONE
```

---

## 6. Receipt Verification (`/check-receipts`)

```
/check-receipts
    |
    v
Read master sheet Receipt column
    |
    v
Report:
    |-- Done: X units (receipt sent)
    |-- Pending: Y units (needs receipt) --> list them
    |-- Not Matched: Z transactions
    |
    v
Offer: "Process pending units? Run /sf-update"
```

---

## Key Rules

| Rule | Detail |
|------|--------|
| Debit order | Always chronological, interleaved with credits |
| Running balance | Must match bank statement after every update |
| Multi-buyer units | All names in every transaction (Unit 301 has 2 groups) |
| Junk names | Never saved -- resolved via master sheet or Salesforce |
| Auto-update | All skills pull latest from GitHub before running |
| Highlighting | RED = unmatched, YELLOW = review, "NEW" = matched |
| Corporate only | Skip Salesforce updates |
| Receipts | Generated and sent through Salesforce, not Gmail |

---

## File Structure

```
Payments-agent/
  CLAUDE.md                    -- Project description
  WORKFLOW.md                  -- This file
  payments-agent.config.json   -- User config (created by /setup)
  .claude/commands/
    reconcile.md               -- /reconcile skill
    setup.md                   -- /setup skill
    sf-update.md               -- /sf-update skill
    sf-sync.md                 -- /sf-sync skill
    check-emails.md            -- /check-emails skill
    check-receipts.md          -- /check-receipts skill
  api/                         -- Vercel API functions
  agents/                      -- Agent logic
  processors/                  -- File processing
  services/                    -- Gmail, Salesforce services
  utils/                       -- Utilities
```
