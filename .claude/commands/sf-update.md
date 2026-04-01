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

#### Part A — Update Payment in Fam Properties (Revamp) app
1. Use Chrome MCP tools to navigate Salesforce
2. Switch to "Fam Properties (Revamp)" app
3. Search for the unit number in global search
4. Click the Inventory result for the correct project
5. Click "Payments" tab on the unit record
6. Find the booking payment (BP-xxxxx) matching the period/amount
7. Click into the payment record
8. Check: does Amount Paid already match the bank amount?
   - If yes: skip (already up to date)
   - If no: click edit pencil on "Amount Paid" → update → save

#### Part A2 — Handle Overpayment (bank amount > installment amount)
If the bank payment received is MORE than the current installment's remaining amount:
1. Calculate: excess = bank_amount - remaining_on_current_installment
2. Update current installment: set Amount Paid = Sub Total (fully paid)
3. Navigate back to Payments tab
4. Find the NEXT upcoming installment (next BP-xxxxx by due date)
5. Click into the next payment record
6. Update Amount Paid on the next installment: add the excess amount
7. Report to user: "AED [bank_amount] received — AED [current_remaining] applied to [current BP], AED [excess] applied to [next BP]"
8. If the excess also exceeds the next installment, repeat the process for subsequent installments until the full bank amount is allocated

**Example:**
- Bank received: AED 200,000
- Current BP-00123 remaining: AED 150,000
- Next BP-00124 sub total: AED 150,000
- Action: BP-00123 Amount Paid = full (150,000), BP-00124 Amount Paid += 50,000
- Report: "AED 200,000 — AED 150,000 to BP-00123 (fully paid), AED 50,000 to BP-00124"

#### Part B — Generate Receipt(s)
9. For EACH installment that was updated (including overpayment splits):
   - Navigate to that payment record (BP-xxxxx)
   - Click "Generate Invoice" button
   - Wait for receipt PDF to appear in Files section
   - If overpayment was split across 2+ installments, generate a receipt for EACH one
10. Collect all generated receipt PDFs

#### Part C — Generate Statement
11. Navigate back to unit → "Account Statements" tab
12. Verify latest statement entry exists (reflects all updated payments)

#### Part D — Send Email
13. Use Activity panel (right side) → Email button
14. To: buyer email (from purchaser record or KB)
15. Subject: "Payment Receipt for [Project] Unit No. [Unit] | [Period]"
16. Body:
    "Dear Valued Client,

    Good day!

    Please find the attached payment receipt for [period] of [Project] Unit No. [Unit]. Also attached is the updated Statement of Account for your reference.

    Kindly acknowledge receipt of this email.

    Thank you."

    If overpayment was split, adjust the body:
    "Please find the attached payment receipts for [Project] Unit No. [Unit].
    AED [amount1] has been applied to [BP-1 period] and AED [amount2] has been applied to [BP-2 period].
    Also attached is the updated Statement of Account for your reference."

17. Attach: ALL generated Receipt PDFs + Statement PDF
18. Send

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
