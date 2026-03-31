# Payments Agent — fam Master Agency

Automatically matches bank transactions to unit payments, updates the master escrow/corporate sheet with credits and debits, validates buyer names, and syncs payment status to Salesforce.

## How It Works

1. **Save bank statement** — Download the escrow/corporate bank statement (`.xls` or `.xlsx`) from WhatsApp to your configured folder
2. **Run `/reconcile`** — The agent finds the new bank statement files and the master sheet
3. **Credit matching** — Sends both files to the reconciliation API which uses AI to match each credit transaction to a unit/buyer using narration text, unit numbers, buyer names, amounts, and Salesforce knowledge base data
4. **Review matches** — Shows all matched transactions with confidence scores. High-confidence matches (>65%) are auto-accepted. Low-confidence matches are flagged for your review with alternative suggestions
5. **Debit sync** — Scans the bank statement for debit transactions (bounced cheques, reimbursements, profit withdrawals, trust-to-retention transfers) and inserts them into the master sheet in the correct chronological position — interleaved with credits so the running balance stays accurate row-by-row
6. **Name validation** — Checks every Account Name for junk/garbage text. If the name looks wrong, it pulls the correct name from existing master sheet rows or queries Salesforce
7. **Master sheet update** — Saves the updated master sheet with all new credits and debits, then verifies the final balance matches the bank statement
8. **Salesforce update** — Optionally queues matched escrow payments for Salesforce status updates

## Getting Started

1. Run `/setup` to configure your environment (master sheet path, bank statement folder, project name, Salesforce access)
2. Run `/reconcile` whenever you have new bank statements to process

## Available Commands

- `/setup` — First-time setup. Configures paths and saves to `payments-agent.config.json`
- `/reconcile` — Main reconciliation workflow (credits + debits + name validation + balance verification)
- `/sf-update` — Update Salesforce with reconciled payment data
- `/sf-sync` — Sync Salesforce project data to the local knowledge base for better matching
- `/check-emails` — Monitor payment-related emails and auto-draft replies
- `/check-receipts` — Verify receipt status in Salesforce

## Key Rules

- The master sheet has two tabs: "Updated Sheet_Escrow Account" and "Updated Sheet_Corporate"
- Debit transactions are always inserted in chronological order (never appended at the end)
- The running balance must match the bank statement's balance after every update
- Multi-buyer units (e.g., Unit 301) must always have ALL buyer names in the Account Name cell
- If the Account Name can't be determined from the narration, check existing rows or query Salesforce
- Corporate-only reconciliation skips Salesforce updates
