# n8n Workflow Setup — Payments Agent

## How to Import

1. Open n8n (self-hosted or cloud)
2. Go to **Workflows** → **Import from File**
3. Select `n8n-workflow.json`
4. Configure credentials (see below)

## Workflow Overview

```
[Schedule: Every 4 Hours] ──┐
                             ├──> [API Health Check] ──> [API Healthy?]
[Manual Trigger] ───────────┘         │                      │
                                      │                 YES  │  NO
                                      │                  │   │
                                      │                  v   v
                                      │          [Load Config]  [Alert: API Down]
                                      │               │
                                      │          ┌────┴────┐
                                      │          v         v
                                      │   [Reconcile   [Reconcile
                                      │    Escrow]      Corporate]
                                      │       │
                                      │       v
                                      │  [New Transactions?]
                                      │     │           │
                                      │    YES          NO
                                      │     │           │
                                      │     v           v
                                      │ [Parse      [Notify: No
                                      │  Results]    New Trans.]
                                      │     │
                                      │     v
                                      │ [Has Unmatched?]
                                      │   │           │
                                      │  YES          NO
                                      │   │           │
                                      │   v           v
                                      │ [Alert:    [Notify:
                                      │  Unmatched] Recon Done]
                                      │   │           │
                                      │   └─────┬─────┘
                                      │         v
                                      │  [Queue Salesforce
                                      │   Updates]
                                      │
                                      │  (parallel branch)
                                      │       │
                                      │       v
                                      │ [Process Match Details]
                                      │       │
                                      │       v
                                      │ [Extract Updated
                                      │  Master Sheet]
```

## Nodes Explained

| Node | Purpose |
|------|---------|
| **Check Every 4 Hours** | Scheduled trigger — runs automatically |
| **Manual Trigger** | Click to run on demand |
| **API Health Check** | Pings `payments-agent.vercel.app/api/health` |
| **API Healthy?** | Routes to config or alert |
| **Load Config** | Sets project name, paths, API URL |
| **Reconcile Escrow** | POSTs master + escrow to reconciliation API |
| **Reconcile Corporate** | POSTs master + corporate to reconciliation API |
| **New Transactions?** | Checks if API found new transactions |
| **Parse Results** | Extracts matched/unmatched/review counts |
| **Has Unmatched?** | Routes to alert or success notification |
| **Alert: Unmatched** | Emails team about RED-flagged transactions |
| **Notify: Recon Done** | Emails summary of successful reconciliation |
| **Queue Salesforce** | Sends matched units to SF update queue |
| **Process Match Details** | Extracts detailed match info for logging |
| **Extract Master Sheet** | Decodes updated master sheet from API response |
| **Alert: API Down** | Emails team if API is unreachable |

## Required Credentials

### 1. Gmail (for notifications)
- Go to **Credentials** → **New** → **Gmail OAuth2**
- Connect your Google account (ma.crm@famproperties.com or your email)
- Used by: Notify nodes, Alert nodes

### 2. Environment Variables
Set these in n8n Settings → Variables:
- `MASTER_SHEET_PATH` = path to your master Excel file
- `BANK_STATEMENT_FOLDER` = path where bank statements are saved

## Customization

### Change Schedule
- Click "Check Every 4 Hours" node
- Change interval (e.g., every 1 hour, daily at 9am)

### Change Project
- Click "Load Config" node
- Change `project` value from "CENTURY" to your project

### Add WhatsApp Trigger
Replace the schedule trigger with a WhatsApp webhook:
1. Add **Webhook** node
2. Set URL in your WhatsApp Business API to trigger on new file messages
3. Connect to API Health Check

### Add Google Drive Integration
To auto-detect bank statements from Google Drive:
1. Add **Google Drive Trigger** node (watch folder for new files)
2. Add **Google Drive Download** node
3. Connect to Reconcile nodes

### Add Slack Notifications
Replace Gmail notify nodes with Slack:
1. Add **Slack** node
2. Configure channel (#payments-reconciliation)
3. Send match summary as Slack message

## Email Notifications

The workflow sends 3 types of emails:

1. **Reconciliation Done** — summary table with matched/unmatched counts
2. **Unmatched Alert** — RED flag warning with details
3. **API Down** — infrastructure alert

## Testing

1. Import the workflow
2. Click **Manual Trigger** → **Execute Workflow**
3. Check if API Health Check passes
4. Upload test files (RAED TEST files) manually
5. Verify email notifications arrive
