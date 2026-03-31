# Payments Agent — fam Master Agency

This is the Payments Reconciliation Agent for fam Master Agency, a Dubai real estate developer. It reconciles bank statements (escrow & corporate) against the master payment sheet and updates Salesforce.

## Getting Started

1. Run `/setup` to configure your environment (master sheet path, downloads folder, project name, Salesforce access)
2. Run `/reconcile` to reconcile bank statements against the master sheet

## Available Commands

- `/setup` — First-time setup. Configures master sheet path, downloads folder, project name, and Salesforce access. Saves to `payments-agent.config.json`.
- `/reconcile` — Main reconciliation workflow. Finds bank statement files, matches transactions to units, updates the master sheet (credits via API + debits via openpyxl in chronological order), and optionally queues Salesforce updates.
- `/sf-update` — Update Salesforce with reconciled payment data.
- `/sf-sync` — Sync Salesforce project data to the local knowledge base for better matching.

## Key Files

- `payments-agent.config.json` — User configuration (created by `/setup`)
- `.claude/commands/` — Skill definitions for each command
- `api/` — Vercel serverless API functions
- `agents/` — Agent logic (matching, Salesforce integration)
- `processors/` — File processing (Excel parsing)

## API

The reconciliation API is hosted at `https://payments-agent.vercel.app/api/reconcile`

## Notes

- The master sheet has two tabs: "Updated Sheet_Escrow Account" and "Updated Sheet_Corporate"
- Debit transactions (bounced cheques, transfers) are synced in chronological order to keep the running balance accurate
- Multi-buyer units (e.g., Unit 301) must always have all buyer names in the Account Name cell
- If the API can't determine the correct Account Name, check existing master sheet rows or query Salesforce
