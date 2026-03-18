"""
Email Service — Handles all agent email communication.
Supports SMTP sending when configured, otherwise logs emails for review.
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config.settings import EMAIL_CONFIG


class EmailService:
    """Handles email sending and logging for the Document Checker agent."""

    def __init__(self, live_mode: bool = False):
        self.live_mode = live_mode and bool(EMAIL_CONFIG.get("smtp_host"))
        self.sent_emails: list[dict] = []
        self.email_count = 0

    def send(self, to: str, subject: str, body: str, cc: str = None,
             from_addr: str = None, reply_to: str = None, html: bool = False) -> dict:
        """Send an email (or log it if not in live mode)."""
        self.email_count += 1

        email_record = {
            "id": f"EMAIL-{self.email_count:04d}",
            "timestamp": datetime.now().isoformat(),
            "from": from_addr or EMAIL_CONFIG["notifications_from"],
            "to": to,
            "cc": cc,
            "subject": subject,
            "body": body,
            "html": html,
            "status": "pending",
        }

        if self.live_mode:
            try:
                result = self._send_smtp(email_record)
                email_record["status"] = "sent"
                email_record["smtp_result"] = result
            except Exception as e:
                email_record["status"] = "failed"
                email_record["error"] = str(e)
        else:
            email_record["status"] = "logged"

        self.sent_emails.append(email_record)
        return email_record

    def send_document_receipt(self, broker_email: str, broker_name: str,
                               submission_id: str, file_count: int,
                               transaction_type: str) -> dict:
        """Send acknowledgment email when documents are received."""
        subject = f"[fam Properties] Documents Received — {submission_id}"
        body = f"""Dear {broker_name},

Thank you for submitting your documents for the {transaction_type} transaction.

Submission Reference: {submission_id}
Documents Received: {file_count} file(s)
Received At: {datetime.now().strftime('%d %b %Y, %I:%M %p')}

Our Document Checker Agent is now reviewing your submission for completeness and validity. You will receive a detailed status update shortly.

If any documents are missing or have issues, we'll let you know exactly what's needed.

Best regards,
Document Checker Agent
fam Properties"""

        return self.send(broker_email, subject, body)

    def send_completeness_report(self, broker_email: str, broker_name: str,
                                   submission_id: str, report: dict) -> dict:
        """Send completeness check results to broker."""
        completeness = report.get("completeness_pct", 0)
        missing = report.get("missing_documents", [])
        issues = report.get("validation_issues", [])

        status_emoji = "COMPLETE" if completeness == 100 else "ACTION REQUIRED"
        subject = f"[fam Properties] Document Review: {status_emoji} — {submission_id}"

        body = f"""Dear {broker_name},

Document Review Summary for {submission_id}
{'=' * 50}

Completeness: {completeness}%
Transaction Type: {report.get('transaction_type', 'N/A')}
"""

        if missing:
            body += f"\n--- MISSING DOCUMENTS ({len(missing)}) ---\n"
            for doc in missing:
                body += f"  - {doc['name']}: {doc['description']}\n"

        if issues:
            body += f"\n--- VALIDATION ISSUES ({len(issues)}) ---\n"
            for issue in issues:
                severity = issue.get('severity', 'info').upper()
                body += f"  [{severity}] {issue['message']}\n"

        if completeness == 100 and not issues:
            body += "\nAll documents are present and validated. Your submission is approved for processing.\n"
        else:
            body += "\nPlease address the above items and resubmit the missing/corrected documents.\n"
            body += f"Reply to this email or send documents to {EMAIL_CONFIG['doc_checker_inbox']}\n"

        body += f"""
Best regards,
Document Checker Agent
fam Properties"""

        return self.send(broker_email, subject, body)

    def send_approval_request(self, approver_email: str, submission_id: str,
                                level: str, reason: str, context: dict = None) -> dict:
        """Send approval request to the appropriate reviewer."""
        subject = f"[APPROVAL REQUIRED] Document Review — {submission_id} ({level.upper()})"
        body = f"""APPROVAL REQUEST
{'=' * 50}

Submission: {submission_id}
Approval Level: {level.upper()}
Reason: {reason}
Requested At: {datetime.now().strftime('%d %b %Y, %I:%M %p')}
"""

        if context:
            body += f"\nTransaction Type: {context.get('transaction_type', 'N/A')}"
            body += f"\nBroker: {context.get('broker_name', 'N/A')}"
            body += f"\nCompleteness: {context.get('completeness_pct', 'N/A')}%"

            if context.get("missing_documents"):
                body += f"\n\nMissing Documents:"
                for doc in context["missing_documents"]:
                    body += f"\n  - {doc['name']}"

            if context.get("critical_issues"):
                body += f"\n\nCritical Issues:"
                for issue in context["critical_issues"]:
                    body += f"\n  - {issue}"

        body += f"""

--- ACTIONS ---
Reply with:
  APPROVE — to approve this submission
  APPROVE WITH CONDITIONS — to approve with specific conditions
  REJECT — to reject with reason
  ESCALATE — to escalate to next level

Document Checker Agent
fam Properties"""

        return self.send(
            approver_email, subject, body,
            cc=EMAIL_CONFIG["ops_manager_inbox"],
        )

    def send_ops_manager_notification(self, event_type: str, submission_id: str,
                                        details: str) -> dict:
        """Notify Operations Manager of significant events."""
        subject = f"[OPS] {event_type} — {submission_id}"
        body = f"""Operations Manager Notification
{'=' * 50}

Event: {event_type}
Submission: {submission_id}
Time: {datetime.now().strftime('%d %b %Y, %I:%M %p')}

Details:
{details}

Document Checker Agent
fam Properties"""

        return self.send(EMAIL_CONFIG["ops_manager_inbox"], subject, body)

    def get_all_emails(self) -> list:
        """Return all sent/logged emails."""
        return self.sent_emails

    def get_email_stats(self) -> dict:
        """Return email statistics."""
        return {
            "total_sent": self.email_count,
            "by_status": {
                "sent": sum(1 for e in self.sent_emails if e["status"] == "sent"),
                "logged": sum(1 for e in self.sent_emails if e["status"] == "logged"),
                "failed": sum(1 for e in self.sent_emails if e["status"] == "failed"),
            },
        }

    def _send_smtp(self, email_record: dict) -> str:
        """Actually send via SMTP."""
        msg = MIMEMultipart()
        msg["From"] = email_record["from"]
        msg["To"] = email_record["to"]
        msg["Subject"] = email_record["subject"]
        if email_record.get("cc"):
            msg["Cc"] = email_record["cc"]

        content_type = "html" if email_record.get("html") else "plain"
        msg.attach(MIMEText(email_record["body"], content_type))

        with smtplib.SMTP(EMAIL_CONFIG["smtp_host"], EMAIL_CONFIG["smtp_port"]) as server:
            server.starttls()
            server.login(EMAIL_CONFIG["smtp_user"], EMAIL_CONFIG["smtp_pass"])
            recipients = [email_record["to"]]
            if email_record.get("cc"):
                recipients.append(email_record["cc"])
            server.send_message(msg)

        return "OK"
