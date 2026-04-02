# /sf-update — Update Salesforce with Reconciled Payments

You are a Salesforce Payment Update Agent. Your job is to update payment records in Salesforce for units that have been reconciled and confirmed.

## Prerequisites
- User must be logged into Salesforce in their browser
- Reconciliation must have been run already (units confirmed)
- Or user can specify units manually

## Auto-update
Before starting, run `git pull origin main` to get the latest skill updates. If it fails, continue anyway.

## Workflow

### Step 1: Check pending queue
- GET https://payments-agent.vercel.app/api/salesforce/pending
- If no pending items, ask user which units to update
- Show pending units: Unit | Amount | Client | Status

### Step 2: For each confirmed unit

#### Part A — Navigate to Unit in Fam Properties (Revamp) app
1. Use Chrome MCP tools to navigate Salesforce
2. Switch to "Fam Properties (Revamp)" app
3. Search for the unit number in global search
4. Click the Inventory result for the correct project
5. You are now on the unit record page

#### Part B — Generate Receipt (this is how payments are recorded + receipts generated)
6. Click **"Generate Receipt"** button on the unit record page
7. On the Receipt Form — **Page 1:**
   - **Amount**: Enter the bank transaction amount (e.g., AED 150,000)
   - **Payment Method**: Select based on the bank narration:
     - "INWARD REMITTANCE" or "BANKNET TRANSFER" → **Bank Transfer**
     - "OUTWARD CLEARING" or "CHQ" → **Cheque**
     - If narration says "CASH" → **Cash**
   - **Select BP(s)**: Choose which booking payment(s) this amount belongs to:
     - If the amount matches ONE BP exactly → select that single BP
     - If the amount covers MULTIPLE BPs → select all applicable BPs (e.g., paid 2 installments together)
     - If the amount is a PARTIAL payment → select the BP and the system will record partial
     - If the amount EXCEEDS the current BP (overpayment) → select the current BP AND the next BP(s) to allocate the excess
8. Click **Next**
9. On the Receipt Form — **Page 2:**
   - **Actual Amount Paid**: Confirm the amount (should match the bank amount)
   - **Description**: Enter the transaction narration from the bank statement (e.g., "INWARD REMITTANCETT REF: 530P5EB4FCD5BB58 AED 150000 RAED")
10. Click **Next** → Receipt is generated automatically

**Overpayment Example:**
- Bank received: AED 200,000
- BP-00123 remaining: AED 150,000
- BP-00124 sub total: AED 150,000
- On Page 1: Select BOTH BP-00123 and BP-00124
- System allocates: AED 150,000 to BP-00123 (fully paid), AED 50,000 to BP-00124
- Receipt generated covering both

**Multiple payments in one transaction:**
- Sometimes a buyer pays 2-3 installments together in one bank transfer
- Select ALL the BPs that the payment covers
- The receipt will reflect the total amount across all selected BPs

#### Part B2 — Verify Receipt PDF
After receipt is generated, verify it before proceeding:
11. Check the generated receipt PDF in the Files section on the unit/payment record
12. Verify it contains:
    - Correct **Client Name** (matches purchaser)
    - Correct **Unit** number
    - Correct **Amount** (AED)
    - Correct **Mode of Payment** (Bank Transfer / Cheque / Cash)
    - Correct **Description** (e.g., "Payment Receipt for Q5, Unit No. 301" or "Partial Payment Receipt for On Handover, Unit No.803")
13. If anything looks wrong, flag it to the user before sending

#### Part C — Generate Statement of Account (SOA)
14. Navigate back to unit → "Account Statements" tab
15. Click to generate/view the latest SOA
16. Verify the SOA shows the latest receipt entry (the one just generated) in the transaction list
17. The SOA PDF should show: all Payment Notices, all Receipts (including the new one), running balance, and bank details at the bottom

#### Part D — Send Email via Salesforce CRM
**IMPORTANT: Always send emails THROUGH SALESFORCE, never through Gmail directly.**
The buyer's email address is found inside the **Purchaser record** in Salesforce (click on the Purchaser name on the unit record → their email is on the contact/person account page).

13. On the unit record page, use the **Activity panel** (right side) → click **Email** button
14. **To**: The buyer's email from the Purchaser record in Salesforce
    - Navigate to the unit → click the Purchaser name → find the email address
    - Copy it into the To field, or Salesforce may auto-populate it
15. **Subject**: "Payment Receipt for [Project] Unit No. [Unit] | [Period]"
16. **Body**:
    "Dear Valued Client,

    Good day!

    Please find the attached payment receipt for [period] of [Project] Unit No. [Unit]. Also attached is the updated Statement of Account for your reference.

    Kindly acknowledge receipt of this email.

    Thank you."

    If payment covered multiple BPs, adjust the body:
    "Please find the attached payment receipt for [Project] Unit No. [Unit].
    AED [total_amount] has been applied to [BP-1 period] and [BP-2 period].
    Also attached is the updated Statement of Account for your reference."

17. **Attach**: Receipt PDF + Statement PDF from the Files section on the unit/payment record
18. **Send** — this sends through Salesforce CRM, keeping the email logged in the Activity History

### Step 3: Mark complete
- POST to https://payments-agent.vercel.app/api/salesforce/queue/{id}/status
  - Body: {"status": "completed"}
- Update master sheet Receipt column to "Done"

### Step 4: Report
- Show user: "X units updated in Salesforce, receipts generated and emailed"

## Navigation tips for Salesforce
- Global search: click the search bar at top, type unit number, press Enter
- Multiple units with same number: filter by project name in search results
- Salesforce is SLOW — always wait 3-5 seconds after each navigation
- If page doesn't load, try refreshing once
- Use `find` tool to locate buttons/links rather than coordinate clicking
