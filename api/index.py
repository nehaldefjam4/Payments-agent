"""
fam Master Agency — Payments Agent (Web API)
FastAPI application for Vercel serverless deployment.
Agentic reconciliation: upload documents → autonomous processing → results.
"""

import os
import sys
import json
import shutil
import tempfile
import traceback
from datetime import datetime
from typing import Optional

import base64
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY, ANTHROPIC_API_KEY, SF_WRITE_MODE, EMAIL_LIVE_MODE


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------
_supabase_client = None

def get_supabase():
    global _supabase_client
    url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
    key = os.environ.get("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)
    if not url or not key:
        return None
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(url, key)
    return _supabase_client


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="fam Payments Agent",
    description="Agentic Payment Reconciliation for Century project - fam Master Agency",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    # Read HTML from static file to avoid Python .pyc caching on Vercel
    html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(
        content=html_content,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    api_key = os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
    sb = get_supabase()

    # SF uses browser session mode — always connected
    sf_status = {
        "connected": True,
        "mode": "browser",
        "instance": "momentum-ability-3447.lightning.force.com",
        "write_mode": SF_WRITE_MODE,
        "email_live_mode": EMAIL_LIVE_MODE,
    }

    return {
        "status": "ok",
        "agent": {
            "name": "Payments Agent",
            "role": "Autonomous AI payment reconciliation & Salesforce integration",
            "organization": "fam Master Agency",
            "version": "3.0.0",
        },
        "claude_enabled": bool(api_key),
        "supabase_connected": sb is not None,
        "salesforce": sf_status,
        "timestamp": datetime.now().isoformat(),
    }


# ===========================================================================
# AGENTIC RECONCILIATION ENDPOINT
# ===========================================================================
from processors.daily_reconciler import DailyReconciler

@app.post("/api/reconcile")
async def reconcile_endpoint(
    master_file: UploadFile = File(...),
    escrow_file: UploadFile = File(None),
    corporate_file: UploadFile = File(None),
    project: str = Form("auto"),
):
    """
    Autonomous agentic reconciliation:
    1. Upload files → parse & build KB
    2. Rule-based matching (unit, name, fuzzy)
    3. Claude AI matching for unmatched transactions
    4. Salesforce sync (read payment schedules, identify installments)
    5. Generate receipts + update master sheet
    All SF writes and emails are in DRY RUN mode unless explicitly enabled.
    """
    tmp_dir = tempfile.mkdtemp(prefix="fam_recon_")
    steps = []

    try:
        # ── Step 1: Save uploaded files ──
        steps.append({"step": 1, "action": "Receiving uploaded documents...", "status": "done"})

        master_path = os.path.join(tmp_dir, master_file.filename)
        with open(master_path, "wb") as f:
            shutil.copyfileobj(master_file.file, f)

        escrow_path = None
        if escrow_file and escrow_file.filename:
            escrow_path = os.path.join(tmp_dir, escrow_file.filename)
            with open(escrow_path, "wb") as f:
                shutil.copyfileobj(escrow_file.file, f)

        corporate_path = None
        if corporate_file and corporate_file.filename:
            corporate_path = os.path.join(tmp_dir, corporate_file.filename)
            with open(corporate_path, "wb") as f:
                shutil.copyfileobj(corporate_file.file, f)

        # ── Step 2: Load master sheet → build knowledge base ──
        reconciler = DailyReconciler()
        master_stats = reconciler.load_master_sheet(master_path)

        # Enrich KB with Salesforce data (if project KB exists in Supabase)
        project_name = project if project != "auto" else "CENTURY"
        sf_kb_stats = reconciler.load_sf_knowledge_base(project_name)
        sf_enriched = sf_kb_stats.get("sf_units", 0)

        kb_msg = f"Loaded knowledge base: {master_stats.get('units_known', 0)} units, {master_stats.get('names_known', 0)} client names"
        if sf_enriched > 0:
            kb_msg += f" + {sf_enriched} units from Salesforce KB ({sf_kb_stats.get('unique_amounts', 0)} unique installment amounts)"
        steps.append({
            "step": 2,
            "action": kb_msg,
            "status": "done",
        })

        # ── Step 3: Parse new statements → find new transactions ──
        stmt_results = reconciler.process_new_statements(
            escrow_path=escrow_path,
            corporate_path=corporate_path,
        )
        initial_matched = len([t for t in reconciler.new_transactions if t.unit_no])
        initial_unmatched = len([t for t in reconciler.new_transactions if not t.unit_no])
        steps.append({
            "step": 3,
            "action": f"Found {stmt_results.get('total_new', 0)} new transactions. Rule-based matching: {initial_matched} matched, {initial_unmatched} unmatched",
            "status": "done",
        })

        # ── Step 4: Claude AI matching for unmatched ──
        ai_results = []
        if initial_unmatched > 0:
            steps.append({
                "step": 4,
                "action": f"Running Claude AI analysis on {initial_unmatched} unmatched transactions...",
                "status": "running",
            })
            ai_results = reconciler.run_ai_matching()
            ai_matched = len([r for r in ai_results if r.get("applied")])
            steps[-1]["action"] = f"AI matching complete: {ai_matched} additional matches found"
            steps[-1]["status"] = "done"
        else:
            steps.append({
                "step": 4,
                "action": "All transactions matched — AI analysis not needed",
                "status": "done",
            })

        # ── Step 5: Salesforce sync (read-only check + dry-run actions) ──
        sf_actions = []
        sf_status = {"connected": False}
        # Only attempt SF sync if escrow file was uploaded
        is_corporate_only = corporate_path and not escrow_path
        if is_corporate_only:
            steps.append({
                "step": 5,
                "action": "Salesforce sync skipped — corporate transactions only (no SF action needed)",
                "status": "skipped",
            })
        else:
            try:
                from services.salesforce_service import SalesforceService
                sf_service = SalesforceService()
                if sf_service.connect():
                    sf_status = sf_service.get_status()
                    project_name = project if project != "auto" else "CENTURY"
                    sf_actions = reconciler.sync_with_salesforce(sf_service, project_name)
                    steps.append({
                        "step": 5,
                        "action": f"Salesforce sync: {len(sf_actions)} units processed",
                        "status": "done",
                    })
                else:
                    steps.append({
                        "step": 5,
                        "action": f"Salesforce not connected: {sf_service.connection_error}",
                        "status": "skipped",
                    })
            except Exception as e:
                steps.append({
                    "step": 5,
                    "action": f"Salesforce sync skipped: {e}",
                    "status": "skipped",
                })

        # ── Step 6: Update master sheet with matched data ──
        output_path = os.path.join(tmp_dir, "Updated_Output.xlsx")
        update_result = reconciler.update_master_sheet(master_path, output_path)
        steps.append({
            "step": 6,
            "action": f"Updated master sheet: {update_result.get('total_added', 0)} rows added, {update_result.get('unreconciled_updated', 0)} previously-unreconciled resolved",
            "status": "done",
        })

        # ── Step 7: Generate receipts (escrow only) ──
        receipts = []
        if is_corporate_only:
            steps.append({
                "step": 7,
                "action": "Receipt generation skipped — corporate transactions only",
                "status": "skipped",
            })
        else:
            receipt_dir = os.path.join(tmp_dir, "receipts")
            receipts = reconciler.generate_receipts(receipt_dir)
            steps.append({
                "step": 7,
                "action": f"Generated {len(receipts)} payment receipts",
                "status": "done",
            })

        # ── Build response ──
        summary = reconciler.get_summary()
        ur = summary.get("unreconciled", {})

        # Combine new transaction matches + unreconciled matches for total
        total_matched = summary.get("matched", 0) + ur.get("now_matched", 0)
        total_unmatched = summary.get("unmatched", 0) + ur.get("still_unmatched", 0)

        # Encode updated master sheet as base64 for download
        master_download = None
        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                master_download = base64.b64encode(f.read()).decode("utf-8")

        # Determine which file types were processed
        has_escrow = escrow_path is not None
        has_corporate = corporate_path is not None
        file_mode = "escrow" if has_escrow and not has_corporate else "corporate" if has_corporate and not has_escrow else "both" if has_escrow and has_corporate else "none"

        return {
            "status": "ok",
            "file_mode": file_mode,
            "agent_steps": steps,
            "master_stats": {
                "units_known": master_stats.get("units_known", 0),
                "names_known": master_stats.get("names_known", 0),
                "cutoff_escrow": master_stats.get("cutoff_escrow", "N/A"),
                "cutoff_corporate": master_stats.get("cutoff_corporate", "N/A"),
            },
            "matching": {
                "total_new": summary.get("total_new_transactions", 0),
                "matched": total_matched,
                "unmatched": total_unmatched,
                "new_matched": summary.get("matched", 0),
                "new_unmatched": summary.get("unmatched", 0),
                "prev_unreconciled_matched": ur.get("now_matched", 0),
                "prev_unreconciled_still": ur.get("still_unmatched", 0),
                "by_account": summary.get("by_account", {}),
                "by_method": summary.get("by_method", {}),
            },
            "ai_matching": {
                "results": ai_results,
                "ai_matched_count": len([r for r in ai_results if r.get("applied")]),
            },
            "salesforce": {
                "status": sf_status,
                "actions": sf_actions,
                "write_mode": SF_WRITE_MODE,
                "email_live_mode": EMAIL_LIVE_MODE,
            },
            "matched_details": summary.get("matched_details", []),
            "unmatched_details": summary.get("unmatched_details", []),
            "receipts": summary.get("receipts", []),
            "unreconciled": summary.get("unreconciled", {}),
            "needs_receipt": summary.get("needs_receipt", []),
            "download": {
                "master_sheet_base64": master_download,
                "filename": "Updated_Master_Sheet.xlsx",
            },
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


@app.post("/api/reconcile/stream")
async def reconcile_stream_endpoint(
    master_file: UploadFile = File(...),
    escrow_file: UploadFile = File(None),
    corporate_file: UploadFile = File(None),
):
    """
    Streaming version: returns Server-Sent Events so the frontend
    can show real-time agent progress.
    """
    import asyncio

    tmp_dir = tempfile.mkdtemp(prefix="fam_recon_")

    async def event_generator():
        try:
            def send_event(step: int, action: str, data: dict = None):
                payload = json.dumps({"step": step, "action": action, "data": data or {}})
                return f"data: {payload}\n\n"

            # Save files
            master_path = os.path.join(tmp_dir, master_file.filename)
            with open(master_path, "wb") as f:
                shutil.copyfileobj(master_file.file, f)

            escrow_path = None
            if escrow_file and escrow_file.filename:
                escrow_path = os.path.join(tmp_dir, escrow_file.filename)
                with open(escrow_path, "wb") as f:
                    shutil.copyfileobj(escrow_file.file, f)

            corporate_path = None
            if corporate_file and corporate_file.filename:
                corporate_path = os.path.join(tmp_dir, corporate_file.filename)
                with open(corporate_path, "wb") as f:
                    shutil.copyfileobj(corporate_file.file, f)

            yield send_event(1, "Loading master sheet and building knowledge base...")

            reconciler = DailyReconciler()
            master_stats = reconciler.load_master_sheet(master_path)
            yield send_event(1, f"Knowledge base ready: {master_stats.get('units_known', 0)} units, {master_stats.get('names_known', 0)} names", master_stats)

            yield send_event(2, "Parsing bank statements and identifying new transactions...")

            stmt_results = reconciler.process_new_statements(
                escrow_path=escrow_path,
                corporate_path=corporate_path,
            )
            yield send_event(2, f"Found {stmt_results.get('total_new', 0)} new transactions", stmt_results)

            yield send_event(3, "Matching transactions to units and updating master sheet...")

            output_path = os.path.join(tmp_dir, "Century_Updated_Output.xlsx")
            update_result = reconciler.update_master_sheet(master_path, output_path)
            yield send_event(3, f"Master sheet updated: {update_result.get('total_added', 0)} rows added", update_result)

            yield send_event(4, "Generating payment receipts...")

            receipt_dir = os.path.join(tmp_dir, "receipts")
            receipts = reconciler.generate_receipts(receipt_dir)
            yield send_event(4, f"Generated {len(receipts)} receipts", {})

            # Final result
            summary = reconciler.get_summary()
            final = {
                "status": "ok",
                "master_stats": {
                    "units_known": master_stats.get("units_known", 0),
                    "names_known": master_stats.get("names_known", 0),
                    "cutoff_escrow": master_stats.get("cutoff_escrow", "N/A"),
                    "cutoff_corporate": master_stats.get("cutoff_corporate", "N/A"),
                },
                "matching": {
                    "total_new": summary.get("total_new_transactions", 0),
                    "matched": summary.get("matched", 0),
                    "unmatched": summary.get("unmatched", 0),
                    "by_account": summary.get("by_account", {}),
                },
                "matched_details": summary.get("matched_details", []),
                "unmatched_details": summary.get("unmatched_details", []),
                "receipts": summary.get("receipts", []),
                "unreconciled": summary.get("unreconciled", {}),
            }
            yield f"data: {json.dumps({'step': 5, 'action': 'complete', 'data': final})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'step': -1, 'action': 'error', 'data': {'error': str(e)}})}\n\n"

        finally:
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ===========================================================================
# AMIT AGENT ENDPOINTS
# ===========================================================================
from agents.amit_agent import AmitAgent, WORKFLOW_LABELS
from services.gmail_service import SupabaseGmailBridge
from config.payment_settings import (
    EMAIL_TEMPLATES, STAKEHOLDERS, CENTURY_PROJECT,
    CALENDLY_PAYMENT, CALENDLY_HOME_ORIENTATION,
)

_amit_agent = None
_gmail_bridge = None

def _get_amit_agent():
    global _amit_agent
    if _amit_agent is None:
        _amit_agent = AmitAgent()
    return _amit_agent

def _get_gmail_bridge():
    global _gmail_bridge
    if _gmail_bridge is None:
        _gmail_bridge = SupabaseGmailBridge()
    return _gmail_bridge


@app.post("/api/agent/classify")
async def classify_email_endpoint(request: Request):
    """Classify a single email into a workflow and get a draft response."""
    body = await request.json()
    result = _get_amit_agent().process_gmail_message(body)
    return result.to_dict()


@app.post("/api/agent/scan")
async def scan_inbox_endpoint(request: Request):
    """Classify a batch of emails from the inbox."""
    body = await request.json()
    emails = body.get("emails", [])
    results = _get_amit_agent().scan_inbox(emails)
    return {
        "total": len(results),
        "classified": [r.to_dict() for r in results],
        "summary": _get_amit_agent().get_dashboard(),
    }


@app.get("/api/agent/dashboard")
async def agent_dashboard():
    """Get the agent's current dashboard (in-memory)."""
    return _get_amit_agent().get_dashboard()


@app.post("/api/agent/reset")
async def reset_agent():
    """Reset the agent state."""
    global _amit_agent
    _amit_agent = AmitAgent()
    return {"status": "reset"}


# ===========================================================================
# AMIT DASHBOARD API (Supabase-backed)
# ===========================================================================

@app.get("/api/amit/inbox")
async def amit_inbox(workflow: str = None, status: str = None,
                     limit: int = 50, offset: int = 0):
    """Get classified emails from Supabase with optional filters."""
    emails = _get_gmail_bridge().get_inbox(
        workflow=workflow, status=status, limit=limit, offset=offset
    )
    return {"emails": emails, "count": len(emails)}


@app.get("/api/amit/inbox/{email_id}")
async def amit_email_detail(email_id: str):
    """Get a single classified email with its drafts."""
    email = _get_gmail_bridge().get_email(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@app.post("/api/amit/inbox/{email_id}/status")
async def amit_update_email_status(email_id: str, request: Request):
    """Update an email's status (new, reviewed, actioned, archived)."""
    body = await request.json()
    new_status = body.get("status", "reviewed")
    result = _get_gmail_bridge().update_email_status(email_id, new_status)
    return result


@app.get("/api/amit/drafts")
async def amit_drafts(status: str = "pending"):
    """Get draft responses filtered by status."""
    drafts = _get_gmail_bridge().get_drafts(status=status)
    return {"drafts": drafts, "count": len(drafts)}


@app.post("/api/amit/drafts/{draft_id}/approve")
async def amit_approve_draft(draft_id: str):
    """Approve a draft for sending."""
    result = _get_gmail_bridge().approve_draft(draft_id)
    return {"status": "approved", "draft": result}


@app.post("/api/amit/drafts/{draft_id}/reject")
async def amit_reject_draft(draft_id: str):
    """Reject a draft."""
    result = _get_gmail_bridge().reject_draft(draft_id)
    return {"status": "rejected", "draft": result}


@app.post("/api/amit/drafts/{draft_id}/edit")
async def amit_edit_draft(draft_id: str, request: Request):
    """Edit a draft before sending."""
    body = await request.json()
    new_body = body.get("body", "")
    result = _get_gmail_bridge().edit_draft(draft_id, new_body)
    return {"status": "edited", "draft": result}


@app.post("/api/amit/drafts/{draft_id}/mark-sent")
async def amit_mark_sent(draft_id: str, request: Request):
    """Mark a draft as sent (called after Gmail MCP sends it)."""
    body = await request.json()
    gmail_draft_id = body.get("gmail_draft_id", "")
    result = _get_gmail_bridge().mark_sent(draft_id, gmail_draft_id)
    return {"status": "sent", "draft": result}


@app.get("/api/amit/stats")
async def amit_stats():
    """Get dashboard statistics."""
    stats = _get_gmail_bridge().get_stats()
    return stats


@app.get("/api/amit/activity")
async def amit_activity(limit: int = 50):
    """Get recent activity log."""
    activity = _get_gmail_bridge().get_activity(limit=limit)
    return {"activity": activity, "count": len(activity)}


@app.get("/api/amit/workflows")
async def amit_workflows():
    """Get all workflow types and their labels."""
    return {"workflows": WORKFLOW_LABELS}


@app.get("/api/amit/stakeholders")
async def amit_stakeholders():
    """Get the Century project stakeholder directory."""
    return {
        "project": CENTURY_PROJECT,
        "stakeholders": STAKEHOLDERS,
        "calendly": {
            "payment": CALENDLY_PAYMENT,
            "home_orientation": CALENDLY_HOME_ORIENTATION,
        },
    }


@app.get("/api/amit/templates")
async def amit_templates():
    """Get all email templates."""
    return {
        name: {"subject": t["subject"], "body": t["body"]}
        for name, t in EMAIL_TEMPLATES.items()
    }


# ===========================================================================
# SALESFORCE API ENDPOINTS
# ===========================================================================
from services.salesforce_service import SalesforceService

_sf_service = None

def _get_sf_service():
    global _sf_service
    if _sf_service is None:
        _sf_service = SalesforceService()
    return _sf_service


@app.get("/api/salesforce/status")
async def sf_status():
    """Get Salesforce connection status — uses browser session mode."""
    sf = _get_sf_service()
    if not sf.is_connected:
        sf.connect()
    return {
        "connected": True,
        "mode": "browser",
        "message": "Salesforce uses browser session via Claude Cowork. Ensure you are logged into Salesforce in a browser tab.",
        "instance": "momentum-ability-3447.lightning.force.com",
        "write_mode": SF_WRITE_MODE,
        "email_live_mode": EMAIL_LIVE_MODE,
        "actions_available": [
            "Search unit by number",
            "View payment schedule",
            "Update payment amount",
            "Generate Invoice/Receipt",
            "Generate Statement",
            "Send email to buyer"
        ],
    }


@app.get("/api/salesforce/projects")
async def sf_projects():
    """Get list of available projects from Salesforce."""
    sf = _get_sf_service()
    try:
        if not sf.is_connected:
            sf.connect()
        projects = sf.get_available_projects()
        return {"projects": projects}
    except Exception as e:
        return {"projects": [], "error": str(e)}


@app.get("/api/salesforce/unit/{unit_name}")
async def sf_unit_details(unit_name: str, project: str = None):
    """Get unit details + payment schedule from Salesforce."""
    sf = _get_sf_service()
    try:
        if not sf.is_connected:
            sf.connect()

        unit = sf.get_unit_details(unit_name, project)
        if not unit:
            raise HTTPException(status_code=404, detail=f"Unit {unit_name} not found")

        payments = sf.get_unit_payments(unit_name, project)

        return {
            "unit": unit.to_dict(),
            "payments": [p.to_dict() for p in payments],
            "total_installments": len(payments),
            "paid": len([p for p in payments if p.status == "Paid"]),
            "unpaid": len([p for p in payments if p.status != "Paid"]),
            "total_remaining": sum(p.remaining for p in payments),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/salesforce/project/{project_name}/payments")
async def sf_project_payments(project_name: str):
    """Get payment summary for all units in a project."""
    sf = _get_sf_service()
    try:
        if not sf.is_connected:
            sf.connect()
        summary = sf.get_project_payment_summary(project_name)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/salesforce/match-installments")
async def sf_match_installments(request: Request):
    """Given a unit and bank amount, identify which installment(s) it covers."""
    body = await request.json()
    unit_name = body.get("unit_name", "")
    amount = float(body.get("amount", 0))
    project = body.get("project", None)

    sf = _get_sf_service()
    try:
        if not sf.is_connected:
            sf.connect()
        installments = sf.identify_installments_for_amount(unit_name, amount, project)
        return {
            "unit": unit_name,
            "bank_amount": amount,
            "installments": [
                {
                    "payment_id": i["payment"].sf_id,
                    "payment_name": i["payment"].name,
                    "type": i["payment"].payment_type,
                    "allocated_amount": i["allocated_amount"],
                    "match_type": i["match_type"],
                    "remaining_before": i["payment"].remaining,
                }
                for i in installments
            ],
            "total_matched": len(installments),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# SF BROWSER AUTOMATION PLAN
# ===========================================================================
from agents.sf_browser_agent import plan_sf_automation

@app.post("/api/salesforce/plan")
async def sf_automation_plan(request: Request):
    """Save confirmed units to Supabase queue for Claude Cowork browser automation.
    Uses dual-app approach: fam app for payments, fam revamp for receipts/emails."""
    body = await request.json()
    needs_receipt = body.get("needs_receipt", [])

    if not needs_receipt:
        return {"plan": None, "message": "No units need receipts", "queued": 0}

    # Save each unit to Supabase queue
    sb = get_supabase()
    queued = 0
    if sb:
        for item in needs_receipt:
            unit_no = item.get("unit_no") or item.get("unit") or ""
            if not unit_no:
                continue
            try:
                sb.table("sf_action_queue").insert({
                    "unit_no": str(unit_no),
                    "amount": float(item.get("credit") or item.get("amount") or 0),
                    "client_name": item.get("account_name") or item.get("client_name") or item.get("client") or "",
                    "date": item.get("date") or item.get("value_date") or "",
                    "narration": item.get("narration") or item.get("description") or "",
                    "period": item.get("period") or "",
                    "action_type": "update_payment",
                    "status": "pending",
                    "sf_app": "fam",
                }).execute()
                queued += 1
            except Exception as e:
                print(f"Failed to queue unit {unit_no}: {e}")

    # Also generate the plan for reference
    plan = plan_sf_automation(needs_receipt)
    plan["queued"] = queued
    plan["message"] = f"{queued} unit(s) queued for Salesforce update. Claude Cowork will process them automatically."
    return plan


@app.get("/api/salesforce/pending")
async def sf_pending_actions():
    """Check for pending SF actions in the queue. Used by Claude Cowork polling."""
    sb = get_supabase()
    if not sb:
        return {"pending": [], "count": 0, "error": "Supabase not connected"}

    try:
        result = sb.table("sf_action_queue").select("*").eq("status", "pending").order("created_at").execute()
        items = result.data or []
        return {"pending": items, "count": len(items)}
    except Exception as e:
        return {"pending": [], "count": 0, "error": str(e)}


@app.post("/api/salesforce/queue/{item_id}/status")
async def sf_update_queue_status(item_id: str, request: Request):
    """Update status of a queued SF action. Used by Claude Cowork after execution."""
    body = await request.json()
    new_status = body.get("status", "completed")
    error_msg = body.get("error_message", "")

    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")

    try:
        update_data = {
            "status": new_status,
            "updated_at": "now()",
        }
        if new_status == "completed":
            update_data["completed_at"] = "now()"
        if error_msg:
            update_data["error_message"] = error_msg

        sb.table("sf_action_queue").update(update_data).eq("id", item_id).execute()
        return {"success": True, "id": item_id, "status": new_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# TESTING ENDPOINTS — for validating SF queue flow
# ===========================================================================

@app.post("/api/salesforce/test/reset-queue")
async def sf_test_reset_queue():
    """Reset all queue items back to 'pending' for re-testing."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")
    try:
        sb.table("sf_action_queue").update({
            "status": "pending",
            "error_message": None,
            "completed_at": None,
            "updated_at": "now()",
        }).neq("status", "____never____").execute()
        result = sb.table("sf_action_queue").select("id, unit_no, status").execute()
        return {"reset": True, "count": len(result.data or []), "items": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/salesforce/test/simulate-complete")
async def sf_test_simulate_complete(request: Request):
    """Simulate Claude Cowork completing one pending item (marks oldest pending as completed)."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")
    try:
        pending = sb.table("sf_action_queue").select("*").eq("status", "pending").order("created_at").limit(1).execute()
        if not pending.data:
            return {"message": "No pending items", "completed": None}
        item = pending.data[0]
        sb.table("sf_action_queue").update({
            "status": "completed",
            "completed_at": "now()",
            "updated_at": "now()",
        }).eq("id", item["id"]).execute()
        return {"message": f"Simulated completion for Unit {item['unit_no']}", "completed": item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/salesforce/test/queue-status")
async def sf_test_queue_status():
    """View full queue status for testing."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")
    try:
        result = sb.table("sf_action_queue").select("*").order("created_at").execute()
        items = result.data or []
        by_status = {}
        for item in items:
            s = item.get("status", "unknown")
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "total": len(items),
            "by_status": by_status,
            "items": items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/salesforce/test/clear-queue")
async def sf_test_clear_queue():
    """Delete all items from the queue (full reset for fresh test)."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")
    try:
        sb.table("sf_action_queue").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        return {"cleared": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# PROJECT KNOWLEDGE BASE (pulled from Salesforce, stored in Supabase)
# ===========================================================================

@app.get("/api/project-kb/{project_name}")
async def get_project_kb(project_name: str):
    """Get the stored knowledge base for a project (units, payments, clients)."""
    sb = get_supabase()
    if not sb:
        return {"units": [], "payments": [], "error": "Supabase not connected"}
    try:
        units = sb.table("project_kb").select("*").eq("project_name", project_name.upper()).execute()
        payments = sb.table("project_kb_payments").select("*").eq("project_name", project_name.upper()).execute()
        return {
            "project": project_name.upper(),
            "units": units.data or [],
            "payments": payments.data or [],
            "unit_count": len(units.data or []),
            "payment_count": len(payments.data or []),
        }
    except Exception as e:
        return {"units": [], "payments": [], "error": str(e)}


@app.post("/api/project-kb/{project_name}/sync")
async def sync_project_kb(project_name: str, request: Request):
    """Save/update project KB data from Salesforce browser scrape.
    Called by Claude Cowork after browsing SF inventory for a project."""
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")

    body = await request.json()
    units = body.get("units", [])
    payments = body.get("payments", [])
    project = project_name.upper()

    synced_units = 0
    synced_payments = 0

    for u in units:
        try:
            sb.table("project_kb").upsert({
                "project_name": project,
                "unit_no": str(u.get("unit_no", "")),
                "unit_sf_id": u.get("sf_id", ""),
                "purchaser_name": u.get("purchaser_name", ""),
                "purchaser_email": u.get("purchaser_email", ""),
                "purchaser_phone": u.get("purchaser_phone", ""),
                "unit_price": float(u.get("price", 0)) if u.get("price") else None,
                "unit_status": u.get("status", ""),
                "building": u.get("building", ""),
                "floor": u.get("floor", ""),
                "bedroom": u.get("bedroom", ""),
                "updated_at": "now()",
            }, on_conflict="project_name,unit_no").execute()
            synced_units += 1
        except Exception as e:
            print(f"Failed to sync unit {u.get('unit_no')}: {e}")

    for p in payments:
        try:
            sb.table("project_kb_payments").insert({
                "project_name": project,
                "unit_no": str(p.get("unit_no", "")),
                "payment_name": p.get("payment_name", ""),
                "payment_sf_id": p.get("sf_id", ""),
                "payment_description": p.get("description", ""),
                "sub_total": float(p.get("sub_total", 0)) if p.get("sub_total") else None,
                "amount_paid": float(p.get("amount_paid", 0)) if p.get("amount_paid") else None,
                "remaining": float(p.get("remaining", 0)) if p.get("remaining") else None,
                "due_date": p.get("due_date", ""),
                "status": p.get("status", ""),
                "payment_type": p.get("payment_type", ""),
                "updated_at": "now()",
            }).execute()
            synced_payments += 1
        except Exception as e:
            print(f"Failed to sync payment {p.get('payment_name')}: {e}")

    return {
        "project": project,
        "synced_units": synced_units,
        "synced_payments": synced_payments,
    }


@app.get("/api/project-kb/list")
async def list_project_kbs():
    """List all projects that have KB data."""
    sb = get_supabase()
    if not sb:
        return {"projects": []}
    try:
        result = sb.table("project_kb").select("project_name").execute()
        projects = list(set(r["project_name"] for r in (result.data or [])))
        return {"projects": sorted(projects)}
    except Exception as e:
        return {"projects": [], "error": str(e)}


# ===========================================================================
# SALESFORCE CREDENTIALS MANAGEMENT (stored in Supabase)
# ===========================================================================

@app.post("/api/settings/salesforce")
async def save_sf_credentials(request: Request):
    """Save Salesforce credentials to Supabase for persistence."""
    body = await request.json()
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=500, detail="Supabase not connected")

    creds = {
        "key": "sf_credentials",
        "value": json.dumps({
            "client_id": body.get("client_id", ""),
            "client_secret": body.get("client_secret", ""),
            "username": body.get("username", ""),
            "password": body.get("password", ""),
            "security_token": body.get("security_token", ""),
            "instance_url": body.get("instance_url", "momentum-ability-3447.my.salesforce.com"),
        }),
        "updated_at": datetime.now().isoformat(),
    }

    try:
        sb.table("agent_settings").upsert(creds, on_conflict="key").execute()

        os.environ["SF_CLIENT_ID"] = body.get("client_id", "")
        os.environ["SF_CLIENT_SECRET"] = body.get("client_secret", "")
        os.environ["SF_USERNAME"] = body.get("username", "")
        os.environ["SF_PASSWORD"] = body.get("password", "")
        os.environ["SF_SECURITY_TOKEN"] = body.get("security_token", "")

        global _sf_service
        _sf_service = None
        sf = _get_sf_service()
        connected = sf.connect()

        return {
            "status": "saved",
            "connected": connected,
            "error": sf.connection_error if not connected else "",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/settings/salesforce")
async def get_sf_credentials():
    """Get current SF connection status (credentials masked)."""
    sf = _get_sf_service()
    status = sf.get_status()

    stored = False
    sb = get_supabase()
    if sb:
        try:
            result = sb.table("agent_settings").select("*").eq("key", "sf_credentials").execute()
            if result.data:
                stored = True
                creds = json.loads(result.data[0]["value"])
                if creds.get("client_id") and not os.environ.get("SF_CLIENT_ID"):
                    os.environ["SF_CLIENT_ID"] = creds["client_id"]
                    os.environ["SF_CLIENT_SECRET"] = creds.get("client_secret", "")
                    os.environ["SF_USERNAME"] = creds.get("username", "")
                    os.environ["SF_PASSWORD"] = creds.get("password", "")
                    os.environ["SF_SECURITY_TOKEN"] = creds.get("security_token", "")
                    status["has_credentials"] = True
        except Exception:
            pass

    status["stored_in_supabase"] = stored
    username = os.environ.get("SF_USERNAME", "")
    status["username_masked"] = f"{username[:3]}***{username[-4:]}" if len(username) > 7 else ("***" if username else "")
    return status
