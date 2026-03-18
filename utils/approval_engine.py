"""
Approval Engine — Multi-level approval workflow with SLA tracking.
Handles auto-approval, agent review, manager review, and director escalation.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from config.settings import APPROVAL_LEVELS


class ApprovalRequest:
    """Represents a single approval request."""

    def __init__(self, submission_id: str, level: str, reason: str, context: dict = None):
        self.id = str(uuid.uuid4())[:8]
        self.submission_id = submission_id
        self.level = level
        self.reason = reason
        self.context = context or {}
        self.status = "pending"  # pending, approved, rejected, escalated, expired
        self.created_at = datetime.now()
        self.resolved_at = None
        self.resolved_by = None
        self.resolution_notes = ""
        self.sla_deadline = self._calculate_sla()

    def _calculate_sla(self) -> datetime:
        level_config = APPROVAL_LEVELS.get(self.level, {})
        sla_minutes = level_config.get("sla_minutes", 60)
        return self.created_at + timedelta(minutes=sla_minutes)

    def approve(self, approved_by: str, notes: str = ""):
        self.status = "approved"
        self.resolved_at = datetime.now()
        self.resolved_by = approved_by
        self.resolution_notes = notes

    def reject(self, rejected_by: str, notes: str = ""):
        self.status = "rejected"
        self.resolved_at = datetime.now()
        self.resolved_by = rejected_by
        self.resolution_notes = notes

    def escalate(self, reason: str = ""):
        self.status = "escalated"
        self.resolution_notes = f"Escalated: {reason}"

    @property
    def is_overdue(self) -> bool:
        return self.status == "pending" and datetime.now() > self.sla_deadline

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "level": self.level,
            "level_label": APPROVAL_LEVELS.get(self.level, {}).get("label", self.level),
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "sla_deadline": self.sla_deadline.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "is_overdue": self.is_overdue,
            "context": self.context,
        }


class ApprovalEngine:
    """Manages the approval workflow for document submissions."""

    def __init__(self):
        self.requests: dict[str, ApprovalRequest] = {}
        self.audit_log: list[dict] = []

    def determine_approval_level(self, check_result: dict) -> str:
        """Determine what approval level is needed based on check results."""
        completeness = check_result.get("completeness_pct", 0)
        critical_issues = check_result.get("critical_issues", 0)
        warnings = check_result.get("warnings", 0)
        expired_docs = check_result.get("expired_docs", 0)
        missing_required = check_result.get("missing_required", 0)

        # Auto-approve: everything is perfect
        if completeness == 100 and critical_issues == 0 and expired_docs == 0:
            return "auto"

        # Director: multiple critical issues
        if critical_issues >= 3 or (missing_required >= 3 and expired_docs >= 2):
            return "director"

        # Manager: missing required docs or expired docs
        if missing_required > 0 or expired_docs > 0:
            return "manager"

        # Agent: minor issues (only warnings or missing optional docs)
        return "agent"

    def create_request(self, submission_id: str, level: str, reason: str, context: dict = None) -> ApprovalRequest:
        """Create a new approval request."""
        request = ApprovalRequest(submission_id, level, reason, context)
        self.requests[request.id] = request

        self._log_event("approval_requested", {
            "request_id": request.id,
            "submission_id": submission_id,
            "level": level,
            "reason": reason,
        })

        return request

    def process_approval(self, request_id: str, action: str, by: str, notes: str = "") -> dict:
        """Process an approval decision."""
        request = self.requests.get(request_id)
        if not request:
            return {"error": f"Request {request_id} not found"}

        if request.status != "pending":
            return {"error": f"Request {request_id} is already {request.status}"}

        if action == "approve":
            request.approve(by, notes)
        elif action == "reject":
            request.reject(by, notes)
        elif action == "escalate":
            request.escalate(notes)
            # Create new request at next level
            next_level = self._get_next_level(request.level)
            if next_level:
                new_req = self.create_request(
                    request.submission_id, next_level,
                    f"Escalated from {request.level}: {notes}",
                    request.context,
                )
                return {"status": "escalated", "new_request": new_req.to_dict()}
        else:
            return {"error": f"Invalid action: {action}"}

        self._log_event(f"approval_{action}", {
            "request_id": request_id,
            "by": by,
            "notes": notes,
        })

        return {"status": request.status, "request": request.to_dict()}

    def check_sla_violations(self) -> list:
        """Check for any overdue approval requests."""
        overdue = []
        for req_id, req in self.requests.items():
            if req.is_overdue:
                overdue.append(req.to_dict())
                self._log_event("sla_violation", {
                    "request_id": req_id,
                    "level": req.level,
                    "overdue_by_minutes": int((datetime.now() - req.sla_deadline).total_seconds() / 60),
                })
        return overdue

    def get_pending_requests(self) -> list:
        """Get all pending approval requests."""
        return [r.to_dict() for r in self.requests.values() if r.status == "pending"]

    def get_submission_approvals(self, submission_id: str) -> list:
        """Get all approval requests for a submission."""
        return [r.to_dict() for r in self.requests.values() if r.submission_id == submission_id]

    def _get_next_level(self, current_level: str) -> str | None:
        level_order = ["auto", "agent", "manager", "director"]
        try:
            idx = level_order.index(current_level)
            if idx < len(level_order) - 1:
                return level_order[idx + 1]
        except ValueError:
            pass
        return None

    def _log_event(self, event_type: str, data: dict):
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            **data,
        })

    def get_audit_log(self) -> list:
        return self.audit_log

    def get_stats(self) -> dict:
        total = len(self.requests)
        pending = sum(1 for r in self.requests.values() if r.status == "pending")
        approved = sum(1 for r in self.requests.values() if r.status == "approved")
        rejected = sum(1 for r in self.requests.values() if r.status == "rejected")
        escalated = sum(1 for r in self.requests.values() if r.status == "escalated")
        overdue = sum(1 for r in self.requests.values() if r.is_overdue)

        return {
            "total_requests": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "escalated": escalated,
            "overdue": overdue,
        }
