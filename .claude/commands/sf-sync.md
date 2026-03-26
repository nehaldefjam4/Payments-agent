# /sf-sync — Sync Salesforce Project Data to Knowledge Base

You are a Salesforce Knowledge Base Builder. Your job is to browse Salesforce and extract all unit/payment data for a project, then store it for future reconciliation matching.

## Prerequisites
- User must be logged into Salesforce in their browser (Chrome with Claude extension)
- Project name must be known (e.g., CENTURY, CBC, THE 100)

## Workflow

### Step 1: Identify project
- Read `payments-agent.config.json` for project name
- Or ask: "Which project should I sync from Salesforce?"

### Step 2: Navigate to Salesforce
- Use Chrome MCP tools to navigate to: https://momentum-ability-3447.lightning.force.com
- Switch to "Fam Properties (Revamp)" app via App Launcher
- Go to Inventory tab

### Step 3: Scrape all units for the project
- Search/filter inventory by project name
- For each unit, extract:
  - unit_no, purchaser_name, purchaser_email, price, status, building, floor, bedroom
- Navigate into each unit's Payments tab:
  - Extract all booking payments: payment_name, sub_total, amount_paid, remaining, due_date, status, payment_type

### Step 4: Save to Knowledge Base
- POST to https://payments-agent.vercel.app/api/project-kb/{PROJECT}/sync
- Body: { "units": [...], "payments": [...] }
- Report: "Synced X units and Y payments for PROJECT"

### Step 5: Verify
- GET https://payments-agent.vercel.app/api/project-kb/{PROJECT}
- Show summary to user

## Important
- This is a ONE-TIME setup per project (can be refreshed periodically)
- Don't modify any SF data — this is READ ONLY
- If a unit has no purchaser (unsold), skip it
- Be patient with Salesforce page loads — wait 3-5 seconds between navigations
