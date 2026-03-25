"""
Gmail Service Abstraction Layer.
Designed for MCP-first approach with future Gmail API swap.

MCP Mode (current): Gmail operations happen in Claude Code session,
results are pushed to Supabase. Dashboard reads from Supabase.

API Mode (future): Direct Gmail API calls via OAuth2.
"""

import os
import json
from datetime import datetime
from typing import Optional


class GmailServiceBase:
    """Abstract interface for Gmail operations."""

    def search(self, query: str, max_results: int = 20) -> list[dict]:
        raise NotImplementedError

    def read_message(self, message_id: str) -> dict:
        raise NotImplementedError

    def read_thread(self, thread_id: str) -> list[dict]:
        raise NotImplementedError

    def create_draft(self, to: str, subject: str, body: str,
                     cc: str = "", thread_id: str = "") -> dict:
        raise NotImplementedError

    def send_draft(self, draft_id: str) -> dict:
        raise NotImplementedError

    def get_profile(self) -> dict:
        raise NotImplementedError


class SupabaseGmailBridge(GmailServiceBase):
    """
    Bridge that reads/writes email data from Supabase.

    Flow:
    1. Claude Code scans Gmail via MCP -> pushes emails to Supabase
    2. Dashboard reads from Supabase via this bridge
    3. User approves drafts -> status updated in Supabase
    4. Claude Code picks up approved drafts -> sends via Gmail MCP
    """

    def __init__(self, supabase_client=None):
        self._sb = supabase_client

    @property
    def sb(self):
        if self._sb is None:
            try:
                from supabase import create_client
                from config.settings import SUPABASE_URL, SUPABASE_ANON_KEY
                url = os.environ.get("SUPABASE_URL", SUPABASE_URL)
                key = os.environ.get("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)
                if url and key:
                    self._sb = create_client(url, key)
            except Exception as e:
                print(f"[GmailBridge] Supabase init error: {e}")
        return self._sb

    def store_classified_email(self, email_data: dict, classification: dict) -> dict:
        """Store a classified email in Supabase."""
        if not self.sb:
            return {"error": "Supabase not connected"}

        record = {
            "message_id": email_data.get("message_id", ""),
            "thread_id": email_data.get("thread_id", ""),
            "from_addr": email_data.get("from_addr", ""),
            "from_name": email_data.get("from_name", ""),
            "to_addr": email_data.get("to_addr", ""),
            "subject": email_data.get("subject", ""),
            "body_preview": email_data.get("body_preview", "")[:2000],
            "date": email_data.get("date"),
            "workflow": classification.get("workflow", "unknown"),
            "workflow_label": classification.get("workflow_label", ""),
            "confidence": classification.get("confidence", 0),
            "suggested_action": classification.get("suggested_action", "escalate"),
            "extracted_data": classification.get("extracted_data", {}),
            "status": "new",
        }

        resp = self.sb.table("amit_emails").upsert(
            record, on_conflict="message_id"
        ).execute()
        return resp.data[0] if resp.data else record

    def store_draft(self, email_id: str, draft_data: dict) -> dict:
        """Store a draft response in Supabase."""
        if not self.sb:
            return {"error": "Supabase not connected"}

        record = {
            "email_id": email_id,
            "draft_subject": draft_data.get("subject", ""),
            "draft_body": draft_data.get("body", ""),
            "to_addr": draft_data.get("to", ""),
            "cc_addr": draft_data.get("cc", ""),
            "reply_to_thread_id": draft_data.get("thread_id", ""),
            "status": "pending",
        }

        resp = self.sb.table("amit_drafts").insert(record).execute()
        return resp.data[0] if resp.data else record

    def log_action(self, email_id: str = None, draft_id: str = None,
                   action_type: str = "", details: dict = None,
                   performed_by: str = "agent") -> dict:
        """Log an action to the activity feed."""
        if not self.sb:
            return {}

        record = {
            "email_id": email_id,
            "draft_id": draft_id,
            "action_type": action_type,
            "details": details or {},
            "performed_by": performed_by,
        }

        resp = self.sb.table("amit_actions").insert(record).execute()
        return resp.data[0] if resp.data else record

    def get_inbox(self, workflow: str = None, status: str = None,
                  limit: int = 50, offset: int = 0) -> list[dict]:
        """Get classified emails from Supabase."""
        if not self.sb:
            return []

        query = self.sb.table("amit_emails").select(
            "*, amit_drafts(id, status, draft_subject)"
        ).order("created_at", desc=True).limit(limit).offset(offset)

        if workflow:
            query = query.eq("workflow", workflow)
        if status:
            query = query.eq("status", status)

        resp = query.execute()
        return resp.data or []

    def get_email(self, email_id: str) -> dict:
        """Get a single classified email with its drafts."""
        if not self.sb:
            return {}

        resp = self.sb.table("amit_emails").select(
            "*, amit_drafts(*)"
        ).eq("id", email_id).single().execute()
        return resp.data or {}

    def get_drafts(self, status: str = "pending", limit: int = 50) -> list[dict]:
        """Get draft responses filtered by status."""
        if not self.sb:
            return []

        resp = self.sb.table("amit_drafts").select(
            "*, amit_emails(from_addr, from_name, subject, workflow, workflow_label)"
        ).eq("status", status).order("created_at", desc=True).limit(limit).execute()
        return resp.data or []

    def approve_draft(self, draft_id: str) -> dict:
        """Mark a draft as approved."""
        if not self.sb:
            return {}

        resp = self.sb.table("amit_drafts").update({
            "status": "approved",
            "approved_at": datetime.now().isoformat(),
        }).eq("id", draft_id).execute()

        self.log_action(draft_id=draft_id, action_type="approve",
                        performed_by="user")
        return resp.data[0] if resp.data else {}

    def reject_draft(self, draft_id: str) -> dict:
        """Mark a draft as rejected."""
        if not self.sb:
            return {}

        resp = self.sb.table("amit_drafts").update({
            "status": "rejected",
        }).eq("id", draft_id).execute()

        self.log_action(draft_id=draft_id, action_type="reject",
                        performed_by="user")
        return resp.data[0] if resp.data else {}

    def edit_draft(self, draft_id: str, new_body: str) -> dict:
        """Edit a draft's body before sending."""
        if not self.sb:
            return {}

        resp = self.sb.table("amit_drafts").update({
            "edited_body": new_body,
            "status": "edited",
        }).eq("id", draft_id).execute()

        self.log_action(draft_id=draft_id, action_type="edit",
                        performed_by="user")
        return resp.data[0] if resp.data else {}

    def mark_sent(self, draft_id: str, gmail_draft_id: str = "") -> dict:
        """Mark a draft as sent."""
        if not self.sb:
            return {}

        resp = self.sb.table("amit_drafts").update({
            "status": "sent",
            "gmail_draft_id": gmail_draft_id,
            "sent_at": datetime.now().isoformat(),
        }).eq("id", draft_id).execute()

        self.log_action(draft_id=draft_id, action_type="send",
                        performed_by="agent")
        return resp.data[0] if resp.data else {}

    def update_email_status(self, email_id: str, status: str) -> dict:
        """Update email status (new, reviewed, actioned, archived)."""
        if not self.sb:
            return {}

        resp = self.sb.table("amit_emails").update({
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }).eq("id", email_id).execute()
        return resp.data[0] if resp.data else {}

    def get_stats(self) -> dict:
        """Get dashboard statistics."""
        if not self.sb:
            return {}

        # Total emails by workflow
        emails = self.sb.table("amit_emails").select(
            "workflow, status, confidence, created_at"
        ).execute().data or []

        drafts = self.sb.table("amit_drafts").select(
            "status"
        ).execute().data or []

        by_workflow = {}
        by_status = {}
        today_count = 0
        today = datetime.now().date().isoformat()

        for e in emails:
            wf = e.get("workflow", "unknown")
            st = e.get("status", "new")
            by_workflow[wf] = by_workflow.get(wf, 0) + 1
            by_status[st] = by_status.get(st, 0) + 1
            if e.get("created_at", "").startswith(today):
                today_count += 1

        draft_status = {}
        for d in drafts:
            st = d.get("status", "pending")
            draft_status[st] = draft_status.get(st, 0) + 1

        return {
            "total_emails": len(emails),
            "today_count": today_count,
            "by_workflow": by_workflow,
            "by_status": by_status,
            "drafts": draft_status,
            "pending_drafts": draft_status.get("pending", 0),
            "sent_count": draft_status.get("sent", 0),
        }

    def get_activity(self, limit: int = 50) -> list[dict]:
        """Get recent activity log."""
        if not self.sb:
            return []

        resp = self.sb.table("amit_actions").select(
            "*, amit_emails(subject, from_name, workflow_label), amit_drafts(draft_subject, status)"
        ).order("created_at", desc=True).limit(limit).execute()
        return resp.data or []
