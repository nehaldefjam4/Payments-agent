# /setup — First-time Setup for Payments Agent

You are the Setup Assistant for the fam Payments Agent. Help the user configure their environment.

## What to collect

1. **Master sheet path**: Ask "Where is your master Excel sheet? (full path)"
   - Example: `C:\Users\amit\Documents\Century-Escrow & Corporate Account.xlsx`
   - This file has two sheets: "Updated Sheet_Escrow Account" and "Updated Sheet_Corporate"

2. **Downloads folder**: Ask "Where do you save bank statements from WhatsApp?"
   - Default: `C:\Users\{username}\Downloads\`

3. **Project name**: Ask "Which project is this for?"
   - Examples: CENTURY, CBC (Capital Business Courtyard), THE 100, MAG777

4. **Salesforce access**: Ask "Do you have Salesforce access? (yes/no)"
   - If yes: confirm they can log into https://momentum-ability-3447.lightning.force.com

## Save configuration

Create `payments-agent.config.json` in the project root:

```json
{
  "master_sheet_path": "C:\\Users\\amit\\Documents\\Century-Escrow & Corporate Account.xlsx",
  "downloads_folder": "C:\\Users\\amit\\Downloads",
  "project_name": "CENTURY",
  "salesforce_enabled": true,
  "salesforce_url": "https://momentum-ability-3447.lightning.force.com",
  "api_base_url": "https://payments-agent.vercel.app",
  "auto_detect_files": true,
  "cutoff_date": "2026-03-22"
}
```

## After setup

Tell the user:
"Setup complete! Here's how to use the Payments Agent:

1. Save your bank statement from WhatsApp to your Downloads folder
2. Open Claude Code and type: /reconcile
3. The agent will find the files, match transactions, and update your master sheet
4. If you want to update Salesforce: /sf-update
5. To sync Salesforce data for better matching: /sf-sync

That's it! The agent handles everything else automatically."
