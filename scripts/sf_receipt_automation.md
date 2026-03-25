# Salesforce Receipt Automation (Browser Session)

## How to use

After running reconciliation on https://payments-agent.vercel.app/, ask Claude Code:

> "Generate receipts in Salesforce for these units: [list from needs_receipt]"

Claude will:
1. Open each unit in Salesforce via Chrome
2. Navigate to the Payments tab
3. Find the matching payment record
4. Click "Generate Invoice"
5. Confirm and note the receipt was created
6. Report back which units were processed

## Requirements
- You must be logged into Salesforce in Chrome
- Claude in Chrome MCP must be active
