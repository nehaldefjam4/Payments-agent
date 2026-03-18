"""
fam Properties — Document Checker Agent (Web API)
FastAPI application for Vercel serverless deployment.
"""

import os
import sys
import json
import uuid
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    DOCUMENT_REQUIREMENTS, VALIDATION_RULES, APPROVAL_LEVELS, AGENT_IDENTITY,
    SUPABASE_URL, SUPABASE_ANON_KEY,
)
from agents.doc_checker import DocumentCheckerAgent

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
    title="fam Properties Document Checker",
    description="AI-powered document validation for Dubai real estate transactions",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _doc_id_to_name(doc_id: str) -> str:
    """Convert a document type ID to a human-readable name."""
    if not doc_id:
        return "Unclassified"
    for reqs in DOCUMENT_REQUIREMENTS.values():
        for d in reqs["required"] + reqs.get("optional", []):
            if d["id"] == doc_id:
                return d["name"]
    return doc_id.replace("_", " ").title()


def _save_submission_to_supabase(result: dict, file_results: list):
    """Persist a submission and its file results to Supabase."""
    sb = get_supabase()
    if not sb:
        return

    try:
        sb.table("submissions").upsert({
            "id": result["submission_id"],
            "transaction_type": result["transaction_type"],
            "transaction_label": DOCUMENT_REQUIREMENTS.get(
                result["transaction_type"], {}
            ).get("label", result["transaction_type"]),
            "broker_name": result["broker"]["name"],
            "broker_email": result["broker"]["email"],
            "property_ref": result.get("property_ref", ""),
            "status": result["status"],
            "completeness_pct": result.get("completeness", {}).get("completeness_pct", 0),
            "files_processed": result.get("files_processed", 0),
            "approval_level": result.get("approval_level"),
            "approval_label": APPROVAL_LEVELS.get(
                result.get("approval_level", ""), {}
            ).get("label"),
            "result": json.loads(json.dumps(result, default=str)),
            "claude_analysis": result.get("claude_analysis"),
            "updated_at": datetime.now().isoformat(),
        }).execute()

        # Save file results
        if file_results:
            sb.table("file_results").insert(file_results).execute()

    except Exception as e:
        print(f"[Supabase] Error saving submission: {e}")


def _save_agent_step(submission_id: str, step_number: int, step_type: str,
                     tool_name: str, description: str, data: dict):
    """Write a single agent step to Supabase for real-time tracking."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("agent_steps").insert({
            "submission_id": submission_id,
            "step_number": step_number,
            "step_type": step_type,
            "tool_name": tool_name,
            "description": description,
            "data": json.loads(json.dumps(data, default=str)),
        }).execute()
    except Exception as e:
        print(f"[Supabase] Error saving agent step: {e}")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    sb = get_supabase()
    return {
        "status": "ok",
        "agent": AGENT_IDENTITY,
        "claude_enabled": bool(api_key),
        "supabase_connected": sb is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/transaction-types")
async def transaction_types():
    """List all supported transaction types and their document requirements."""
    result = {}
    for key, val in DOCUMENT_REQUIREMENTS.items():
        result[key] = {
            "label": val["label"],
            "required_count": len(val["required"]),
            "optional_count": len(val.get("optional", [])),
            "required": [{"id": d["id"], "name": d["name"], "description": d["description"]} for d in val["required"]],
            "optional": [{"id": d["id"], "name": d["name"], "description": d["description"]} for d in val.get("optional", [])],
        }
    return result


@app.get("/api/requirements/{transaction_type}")
async def get_requirements(transaction_type: str):
    """Get document requirements for a specific transaction type."""
    reqs = DOCUMENT_REQUIREMENTS.get(transaction_type)
    if not reqs:
        raise HTTPException(status_code=404, detail=f"Unknown transaction type: {transaction_type}")
    return reqs


@app.post("/api/check")
async def check_documents(
    transaction_type: str = Form(...),
    broker_name: str = Form("Broker"),
    broker_email: str = Form("broker@agency.ae"),
    property_ref: str = Form(""),
    files: list[UploadFile] = File(...),
):
    """Upload documents and run the checker agent (agentic loop or rule-based)."""
    if transaction_type not in DOCUMENT_REQUIREMENTS:
        raise HTTPException(status_code=400, detail=f"Invalid transaction type: {transaction_type}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="fam_docs_"))
    try:
        for f in files:
            dest = tmp_dir / f.filename
            content = await f.read()
            dest.write_bytes(content)

        # Create agent and run the full pipeline
        agent = DocumentCheckerAgent()

        # Create a step_callback that writes to Supabase
        submission_id_holder = [None]

        def step_callback(step_number, step_type, tool_name, description, data):
            if submission_id_holder[0]:
                _save_agent_step(
                    submission_id_holder[0], step_number,
                    step_type, tool_name, description, data,
                )

        result = agent.process_submission(
            folder_path=str(tmp_dir),
            transaction_type=transaction_type,
            broker_name=broker_name,
            broker_email=broker_email,
            property_ref=property_ref,
            step_callback=step_callback,
        )

        # Update the holder so future callbacks work
        submission_id_holder[0] = result["submission_id"]

        # Build file results for Supabase
        file_results = []
        for f_info in agent.processor.processed_files:
            file_results.append({
                "submission_id": result["submission_id"],
                "file_name": f_info["file_name"],
                "classified_as": f_info["classified_as"],
                "classified_label": _doc_id_to_name(f_info["classified_as"]),
                "confidence": f_info["classification_confidence"],
                "size_mb": f_info["file_size_mb"],
                "issues": f_info["validation_issues"],
            })

        # Add file_results to the API response
        result["file_results"] = [
            {
                "file_name": fr["file_name"],
                "classified_as": fr["classified_as"],
                "classified_label": fr["classified_label"],
                "confidence": fr["confidence"],
                "size_mb": fr["size_mb"],
                "issues": fr["issues"],
            }
            for fr in file_results
        ]

        # Persist to Supabase
        _save_submission_to_supabase(result, file_results)

        return result

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/api/submissions")
async def list_submissions():
    """List all submissions (from Supabase if available)."""
    sb = get_supabase()
    if sb:
        try:
            resp = sb.table("submissions") \
                .select("id, transaction_type, transaction_label, broker_name, status, completeness_pct, files_processed, created_at, approval_level, approval_label") \
                .order("created_at", desc=True) \
                .limit(50) \
                .execute()
            return {
                "count": len(resp.data),
                "submissions": resp.data,
            }
        except Exception as e:
            return {"count": 0, "submissions": [], "error": str(e)}

    return {"count": 0, "submissions": [], "note": "Supabase not configured"}


@app.get("/api/submissions/{submission_id}")
async def get_submission(submission_id: str):
    """Get details of a specific submission."""
    sb = get_supabase()
    if sb:
        try:
            resp = sb.table("submissions") \
                .select("*") \
                .eq("id", submission_id) \
                .single() \
                .execute()

            # Also get file results
            files_resp = sb.table("file_results") \
                .select("*") \
                .eq("submission_id", submission_id) \
                .execute()

            data = resp.data
            data["file_results"] = files_resp.data
            return data
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Submission not found: {e}")

    raise HTTPException(status_code=404, detail="Supabase not configured")


@app.get("/api/submissions/{submission_id}/steps")
async def get_submission_steps(submission_id: str):
    """Get agent steps for real-time progress tracking."""
    sb = get_supabase()
    if sb:
        try:
            # Get submission status
            sub_resp = sb.table("submissions") \
                .select("status") \
                .eq("id", submission_id) \
                .single() \
                .execute()

            # Get all steps
            steps_resp = sb.table("agent_steps") \
                .select("*") \
                .eq("submission_id", submission_id) \
                .order("step_number") \
                .execute()

            return {
                "submission_id": submission_id,
                "status": sub_resp.data.get("status", "unknown"),
                "steps": steps_resp.data,
                "total_steps": len(steps_resp.data),
            }
        except Exception as e:
            return {"submission_id": submission_id, "status": "unknown", "steps": [], "error": str(e)}

    return {"submission_id": submission_id, "status": "unknown", "steps": []}
