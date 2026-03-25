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
# v3.1 - cache bust
@app.get("/", response_class=HTMLResponse)
async def root():
    from api._amit_html import AMIT_DASHBOARD_HTML
    return HTMLResponse(content=AMIT_DASHBOARD_HTML, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    api_key = os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
    sb = get_supabase()

    # Check SF connection
    sf_status = {"connected": False, "write_mode": SF_WRITE_MODE, "email_live_mode": EMAIL_LIVE_MODE}
    try:
        from services.salesforce_service import SalesforceService
        sf = SalesforceService()
        sf_status = sf.get_status()
    except Exception:
        pass

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
        "safety": {
            "sf_write_mode": SF_WRITE_MODE,
            "email_live_mode": EMAIL_LIVE_MODE,
        },
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
        steps.append({
            "step": 2,
            "action": f"Loaded knowledge base: {master_stats.get('units_known', 0)} units, {master_stats.get('names_known', 0)} client names",
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
        try:
            from services.salesforce_service import SalesforceService
            sf_service = SalesforceService()
            if sf_service.connect():
                sf_status = sf_service.get_status()
                project_name = project if project != "auto" else "CENTURY"
                sf_actions = reconciler.sync_with_salesforce(sf_service, project_name)
                steps.append({
                    "step": 5,
                    "action": f"Salesforce sync: {len(sf_actions)} units processed (write_mode={'ON' if SF_WRITE_MODE else 'DRY RUN'})",
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

        # ── Step 7: Generate receipts ──
        receipt_dir = os.path.join(tmp_dir, "receipts")
        receipts = reconciler.generate_receipts(receipt_dir)
        steps.append({
            "step": 7,
            "action": f"Generated {len(receipts)} payment receipts",
            "status": "done",
        })

        # ── Build response ──
        summary = reconciler.get_summary()

        # Encode updated master sheet as base64 for download
        master_download = None
        if os.path.exists(output_path):
            with open(output_path, "rb") as f:
                master_download = base64.b64encode(f.read()).decode("utf-8")

        return {
            "status": "ok",
            "agent_steps": steps,
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
    """Get Salesforce connection status and safety flags."""
    sf = _get_sf_service()
    status = sf.get_status()
    if not sf.is_connected:
        try:
            sf.connect()
            status = sf.get_status()
        except Exception:
            pass
    return status


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
