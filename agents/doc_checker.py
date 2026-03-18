"""
Document Checker Agent — The core intelligence layer.
Uses Claude API with a proper tool-use agentic loop when available,
falls back to rule-based logic otherwise.
"""

import os
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

from config.settings import (
    DOCUMENT_REQUIREMENTS, VALIDATION_RULES, APPROVAL_LEVELS,
    AGENT_IDENTITY, ANTHROPIC_API_KEY, CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS, AGENT_MAX_TURNS,
)
from processors.document_processor import DocumentProcessor
from utils.approval_engine import ApprovalEngine
from utils.email_service import EmailService

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are the Document Checker Agent for fam Properties, a leading real estate brokerage in Dubai, UAE.

Your role is to:
1. Receive and classify documents submitted by brokers for property transactions
2. Check completeness against Dubai real estate requirements (DLD, RERA, Ejari)
3. Validate document authenticity, expiry dates, and quality
4. Flag missing or problematic documents
5. Route submissions through the appropriate approval workflow
6. Communicate clearly with brokers about what's needed

You are thorough, professional, and knowledgeable about Dubai real estate documentation requirements including:
- Emirates ID, passport, and visa requirements
- Title deeds and DLD registration
- RERA Forms (Form A for buyers/tenants, Form F for listings)
- NOC from developers
- Sale & Purchase Agreements (SPA)
- Ejari tenancy contracts
- Mortgage clearance letters
- Company documentation (trade license, MOA/AOA, board resolutions)
- Off-plan documentation (Oqood, reservation forms, payment plans)

When analyzing documents, you provide specific, actionable feedback. You never approve incomplete submissions without flagging what's missing. You escalate appropriately based on severity.

IMPORTANT: Use the tools provided to complete each step of your workflow. After completing all steps, provide your final analysis as JSON with keys: verdict, risk, recommendations (array), red_flags (array), approval_level, completeness_pct."""

TOOLS = [
    {
        "name": "get_submission_summary",
        "description": "Retrieve the processed file data for the current submission, including file classifications, extracted text previews, validation issues, and metadata. Call this first to understand what documents have been submitted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {
                    "type": "string",
                    "description": "The submission ID to retrieve data for"
                }
            },
            "required": ["submission_id"]
        }
    },
    {
        "name": "check_completeness",
        "description": "Check if all required documents are present for a given transaction type",
        "input_schema": {
            "type": "object",
            "properties": {
                "transaction_type": {
                    "type": "string",
                    "enum": ["residential_sale", "residential_rent", "commercial_sale", "off_plan_sale"],
                    "description": "The type of real estate transaction"
                },
                "submitted_documents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of document type IDs that have been submitted"
                }
            },
            "required": ["transaction_type", "submitted_documents"]
        }
    },
    {
        "name": "validate_document",
        "description": "Validate a specific document for issues like expiry, quality, or completeness",
        "input_schema": {
            "type": "object",
            "properties": {
                "document_type": {"type": "string", "description": "The document type ID"},
                "document_info": {"type": "object", "description": "Extracted document metadata"},
            },
            "required": ["document_type", "document_info"]
        }
    },
    {
        "name": "request_approval",
        "description": "Submit a document package for approval at the appropriate level",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "level": {"type": "string", "enum": ["auto", "agent", "manager", "director"]},
                "reason": {"type": "string"},
                "context": {"type": "object"},
            },
            "required": ["submission_id", "level", "reason"]
        }
    },
    {
        "name": "send_broker_notification",
        "description": "Send an email notification to the broker about their submission status",
        "input_schema": {
            "type": "object",
            "properties": {
                "broker_email": {"type": "string"},
                "broker_name": {"type": "string"},
                "notification_type": {"type": "string", "enum": ["receipt", "completeness_report", "approval_result"]},
                "submission_id": {"type": "string"},
                "details": {"type": "object"},
            },
            "required": ["broker_email", "broker_name", "notification_type", "submission_id"]
        }
    },
]


class DocumentCheckerAgent:
    """The main Document Checker Agent — orchestrates the full workflow."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
        self.use_claude = bool(self.api_key) and HAS_ANTHROPIC
        self.client = anthropic.Anthropic(api_key=self.api_key) if self.use_claude else None

        self.processor = DocumentProcessor()
        self.approval_engine = ApprovalEngine()
        self.email_service = EmailService(live_mode=False)

        self.submissions: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_submission(
        self,
        folder_path: str,
        transaction_type: str,
        broker_name: str,
        broker_email: str,
        property_ref: str = "",
        step_callback=None,
    ) -> dict:
        """Process a complete document submission end-to-end."""
        submission_id = f"SUB-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

        print(f"\n{'='*60}")
        print(f"  DOCUMENT CHECKER AGENT — Processing Submission")
        print(f"{'='*60}")
        print(f"  Submission ID:    {submission_id}")
        print(f"  Transaction Type: {transaction_type}")
        print(f"  Broker:           {broker_name} ({broker_email})")
        print(f"  Property Ref:     {property_ref or 'N/A'}")
        print(f"  Folder:           {folder_path}")
        print(f"  Mode:             {'Agentic (Claude)' if self.use_claude else 'Rule-based'}")
        print(f"{'='*60}\n")

        # Step 1: Process all files (always done upfront — Claude needs this data)
        print("[1] Scanning and processing documents...")
        processed = self.processor.process_submission(folder_path)
        file_count = processed["total_files"]
        print(f"    Found {file_count} document(s)")

        for f in processed["files"]:
            classified = f["classified_as"] or "unclassified"
            confidence = f["classification_confidence"]
            print(f"    - {f['file_name']}: '{classified}' (confidence: {confidence})")

        # Build submission context (shared data for tool handlers)
        submission_context = {
            "submission_id": submission_id,
            "transaction_type": transaction_type,
            "broker_name": broker_name,
            "broker_email": broker_email,
            "property_ref": property_ref,
            "processed": processed,
        }

        # Branch: agentic loop vs rule-based fallback
        if self.use_claude:
            print(f"\n[2] Running Claude agentic loop...")
            loop_result = self._run_agentic_loop(submission_context, step_callback)

            if loop_result and not loop_result.get("error"):
                claude_analysis = self._parse_final_analysis(loop_result.get("final_response", ""))
                approval_level = claude_analysis.get("approval_level", "agent")
                # Normalize approval_level
                if approval_level not in APPROVAL_LEVELS:
                    approval_level = "agent"

                # Find the approval request if one was created during the loop
                approval_request = None
                for tc in loop_result.get("tool_calls", []):
                    if tc["tool"] == "request_approval" and tc["result"].get("request_id"):
                        req_id = tc["result"]["request_id"]
                        approval_request = self.approval_engine.requests.get(req_id)

                # Find completeness data from tool calls
                completeness = {}
                for tc in loop_result.get("tool_calls", []):
                    if tc["tool"] == "check_completeness" and not tc["result"].get("error"):
                        completeness = tc["result"]
                        break

                result = {
                    "submission_id": submission_id,
                    "status": "approved" if approval_level == "auto" else "pending_approval",
                    "transaction_type": transaction_type,
                    "broker": {"name": broker_name, "email": broker_email},
                    "property_ref": property_ref,
                    "files_processed": file_count,
                    "completeness": completeness,
                    "approval_level": approval_level,
                    "approval_request": approval_request.to_dict() if approval_request else None,
                    "claude_analysis": claude_analysis,
                    "agentic_loop": {
                        "turns": loop_result.get("turns", 0),
                        "tool_calls_count": len(loop_result.get("tool_calls", [])),
                    },
                    "emails_sent": self.email_service.email_count,
                    "audit_trail": self.approval_engine.get_audit_log(),
                    "processed_at": datetime.now().isoformat(),
                }
            else:
                print(f"    Agentic loop failed: {loop_result.get('error', 'unknown') if loop_result else 'no result'}")
                print(f"    Falling back to rule-based processing...")
                result = self._rule_based_processing(
                    submission_id, transaction_type, broker_name,
                    broker_email, property_ref, processed, file_count,
                )
        else:
            print(f"\n[2] Claude API not configured — using rule-based processing")
            result = self._rule_based_processing(
                submission_id, transaction_type, broker_name,
                broker_email, property_ref, processed, file_count,
            )

        self.submissions[submission_id] = result

        # Print summary
        print(f"\n{'='*60}")
        print(f"  PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"  Submission ID:  {submission_id}")
        print(f"  Status:         {result['status'].upper()}")
        cpct = result.get('completeness', {}).get('completeness_pct', 'N/A')
        print(f"  Completeness:   {cpct}%")
        print(f"  Approval Level: {result['approval_level'].upper()}")
        print(f"  Emails Sent:    {self.email_service.email_count}")
        if result.get("agentic_loop"):
            print(f"  Agentic Turns:  {result['agentic_loop']['turns']}")
            print(f"  Tool Calls:     {result['agentic_loop']['tool_calls_count']}")
        print(f"{'='*60}\n")

        return result

    # ------------------------------------------------------------------
    # Agentic loop
    # ------------------------------------------------------------------

    def _run_agentic_loop(self, submission_context: dict, step_callback=None) -> dict:
        """Run the Claude agentic loop. Claude drives the workflow via tool calls."""
        if not self.client:
            return None

        user_message = self._build_initial_prompt(submission_context)
        messages = [{"role": "user", "content": user_message}]

        turn_count = 0
        all_tool_results = []

        while turn_count < AGENT_MAX_TURNS:
            turn_count += 1
            print(f"      [Agentic loop] Turn {turn_count}/{AGENT_MAX_TURNS}")

            try:
                response = self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=CLAUDE_MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )
            except Exception as e:
                print(f"      [Agentic loop] API error: {e}")
                return {"error": str(e), "turns": turn_count, "tool_calls": all_tool_results}

            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # If stop_reason is "end_turn", Claude is done
            if response.stop_reason == "end_turn":
                print(f"      [Agentic loop] Claude finished after {turn_count} turns")
                final_text = ""
                for block in assistant_content:
                    if block.type == "text":
                        final_text += block.text
                return {
                    "final_response": final_text,
                    "turns": turn_count,
                    "tool_calls": all_tool_results,
                }

            # If stop_reason is "tool_use", execute each tool call
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        print(f"      [Tool] {tool_name}({json.dumps(tool_input)[:80]}...)")

                        result = self._handle_tool_call(
                            tool_name, tool_input, submission_context
                        )

                        all_tool_results.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result,
                        })

                        # Notify callback for real-time progress
                        if step_callback:
                            step_callback(
                                len(all_tool_results),
                                "tool_call",
                                tool_name,
                                f"Called {tool_name}",
                                {"input": tool_input, "result": result},
                            )

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result),
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason (e.g., max_tokens)
                print(f"      [Agentic loop] Stop reason: {response.stop_reason}")
                final_text = ""
                for block in assistant_content:
                    if block.type == "text":
                        final_text += block.text
                return {
                    "final_response": final_text,
                    "turns": turn_count,
                    "tool_calls": all_tool_results,
                    "stop_reason": response.stop_reason,
                }

        print(f"      [Agentic loop] Max turns ({AGENT_MAX_TURNS}) reached")
        return {"error": "max_turns_exceeded", "turns": turn_count, "tool_calls": all_tool_results}

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def _handle_tool_call(self, tool_name: str, tool_input: dict,
                          submission_context: dict) -> dict:
        """Execute a tool call and return the result as a dict."""
        try:
            if tool_name == "get_submission_summary":
                ctx = submission_context
                return {
                    "submission_id": ctx["submission_id"],
                    "transaction_type": ctx["transaction_type"],
                    "broker_name": ctx["broker_name"],
                    "broker_email": ctx["broker_email"],
                    "property_ref": ctx["property_ref"],
                    "total_files": ctx["processed"]["total_files"],
                    "files": [
                        {
                            "file_name": f["file_name"],
                            "classified_as": f["classified_as"],
                            "classification_confidence": f["classification_confidence"],
                            "file_size_mb": f["file_size_mb"],
                            "text_preview": (f["extracted_text"] or "")[:500],
                            "validation_issues": f["validation_issues"],
                            "detected_dates": f.get("metadata", {}).get("detected_dates", []),
                        }
                        for f in ctx["processed"]["files"]
                    ],
                }

            elif tool_name == "check_completeness":
                return self._check_completeness(
                    tool_input["transaction_type"],
                    tool_input["submitted_documents"],
                )

            elif tool_name == "validate_document":
                doc_type = tool_input["document_type"]
                for f in submission_context["processed"]["files"]:
                    if f["classified_as"] == doc_type:
                        return {
                            "document_type": doc_type,
                            "file_name": f["file_name"],
                            "validation_issues": f["validation_issues"],
                            "text_preview": (f["extracted_text"] or "")[:300],
                            "detected_dates": f.get("metadata", {}).get("detected_dates", []),
                            "status": "invalid" if f["validation_issues"] else "valid",
                        }
                return {"error": f"No file classified as '{doc_type}' found in submission"}

            elif tool_name == "request_approval":
                submission_id = tool_input["submission_id"]
                level = tool_input["level"]
                reason = tool_input["reason"]
                context = tool_input.get("context", {})

                if level == "auto":
                    return {
                        "status": "auto_approved",
                        "submission_id": submission_id,
                        "message": "All checks passed — submission auto-approved",
                    }

                request = self.approval_engine.create_request(
                    submission_id, level, reason, context,
                )
                approver_email = APPROVAL_LEVELS[level].get(
                    "approver_email", "ops.manager@famproperties.com"
                )
                self.email_service.send_approval_request(
                    approver_email, submission_id, level, reason, context,
                )
                return {
                    "status": "approval_requested",
                    "request_id": request.id,
                    "level": level,
                    "approver_email": approver_email,
                    "sla_deadline": request.sla_deadline.isoformat(),
                }

            elif tool_name == "send_broker_notification":
                broker_email = tool_input["broker_email"]
                broker_name = tool_input["broker_name"]
                notification_type = tool_input["notification_type"]
                submission_id = tool_input["submission_id"]
                details = tool_input.get("details", {})

                if notification_type == "receipt":
                    email = self.email_service.send_document_receipt(
                        broker_email, broker_name, submission_id,
                        details.get("file_count", 0),
                        details.get("transaction_type", ""),
                    )
                elif notification_type == "completeness_report":
                    email = self.email_service.send_completeness_report(
                        broker_email, broker_name, submission_id, details,
                    )
                elif notification_type == "approval_result":
                    subject = f"[fam Properties] Submission Update — {submission_id}"
                    body = f"Dear {broker_name},\n\n"
                    body += details.get("message", "Your submission status has been updated.")
                    body += f"\n\nBest regards,\nDocument Checker Agent\nfam Properties"
                    email = self.email_service.send(broker_email, subject, body)
                else:
                    return {"error": f"Unknown notification type: {notification_type}"}

                return {
                    "status": "sent",
                    "email_id": email["id"],
                    "to": broker_email,
                    "notification_type": notification_type,
                }

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": str(e), "tool": tool_name}

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    def _build_initial_prompt(self, ctx: dict) -> str:
        """Build the initial user message that kicks off the agentic loop."""
        files_summary = []
        submitted_doc_types = []
        for f in ctx["processed"]["files"]:
            files_summary.append({
                "name": f["file_name"],
                "classified_as": f["classified_as"],
                "confidence": f["classification_confidence"],
                "size_mb": f["file_size_mb"],
            })
            if f["classified_as"]:
                submitted_doc_types.append(f["classified_as"])

        return f"""You have a new document submission to process. Here are the details:

Submission ID: {ctx["submission_id"]}
Transaction Type: {ctx["transaction_type"]}
Broker Name: {ctx["broker_name"]}
Broker Email: {ctx["broker_email"]}
Property Reference: {ctx["property_ref"] or "N/A"}
Files Uploaded: {ctx["processed"]["total_files"]} file(s)

Files summary:
{json.dumps(files_summary, indent=2)}

Document types identified: {json.dumps(submitted_doc_types)}

Please process this submission by following these steps:

1. Call `get_submission_summary` to review the uploaded documents and their classifications.
2. Call `send_broker_notification` with type "receipt" to acknowledge receipt of the documents.
   Include details: {{"file_count": {ctx["processed"]["total_files"]}, "transaction_type": "{ctx["transaction_type"]}"}}
3. Call `check_completeness` to verify all required documents are present for "{ctx["transaction_type"]}".
   Pass the submitted_documents list: {json.dumps(submitted_doc_types)}
4. For any documents with validation issues or low classification confidence, call `validate_document`.
5. Based on completeness and validation results, determine the approval level:
   - "auto" if 100% complete with no critical issues
   - "agent" for minor issues (warnings only)
   - "manager" for missing required documents or expired docs
   - "director" for multiple critical issues (3+ critical or 3+ missing + 2+ expired)
6. Call `request_approval` with the determined level and a clear reason.
7. Call `send_broker_notification` with type "completeness_report" including the completeness details.

After completing all steps, provide your final summary as JSON with keys:
verdict, risk, recommendations (array), red_flags (array), approval_level, completeness_pct"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_final_analysis(self, text: str) -> dict:
        """Parse Claude's final text response into a structured dict."""
        if not text:
            return {"verdict": "NEEDS_ATTENTION", "risk": "MEDIUM", "recommendations": []}
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                match = re.search(r'\{[^{}]*("verdict"|"risk")[^{}]*\}', text, re.DOTALL)
                if match:
                    json_str = match.group(0)
                else:
                    json_str = text.strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError):
            return {
                "verdict": "NEEDS_ATTENTION",
                "risk": "MEDIUM",
                "recommendations": [text[:500]],
                "raw_response": text[:1000],
            }

    # ------------------------------------------------------------------
    # Rule-based fallback (no Claude API)
    # ------------------------------------------------------------------

    def _rule_based_processing(self, submission_id, transaction_type, broker_name,
                               broker_email, property_ref, processed, file_count) -> dict:
        """Fallback: the original hardcoded processing logic when Claude is not available."""

        # Send receipt
        print(f"    [Rule-based] Sending receipt...")
        self.email_service.send_document_receipt(
            broker_email, broker_name, submission_id, file_count, transaction_type,
        )

        # Check completeness
        print(f"    [Rule-based] Checking completeness...")
        submitted_doc_types = [f["classified_as"] for f in processed["files"] if f["classified_as"]]
        completeness = self._check_completeness(transaction_type, submitted_doc_types)
        print(f"    Completeness: {completeness['completeness_pct']}%")

        if completeness["missing_documents"]:
            print(f"    Missing ({len(completeness['missing_documents'])}):")
            for doc in completeness["missing_documents"]:
                print(f"      - {doc['name']}")

        # Determine approval level
        check_result = {
            "completeness_pct": completeness["completeness_pct"],
            "critical_issues": len([i for i in completeness["validation_issues"] if i["severity"] == "error"]),
            "warnings": len([i for i in completeness["validation_issues"] if i["severity"] == "warning"]),
            "expired_docs": completeness.get("expired_docs_count", 0),
            "missing_required": len(completeness["missing_documents"]),
        }

        approval_level = self.approval_engine.determine_approval_level(check_result)
        print(f"    Approval level: {approval_level.upper()}")

        approval_request = None
        if approval_level != "auto":
            reason = self._build_approval_reason(completeness, check_result)
            context = {
                "transaction_type": transaction_type,
                "broker_name": broker_name,
                "broker_email": broker_email,
                "completeness_pct": completeness["completeness_pct"],
                "missing_documents": completeness["missing_documents"],
            }
            approval_request = self.approval_engine.create_request(
                submission_id, approval_level, reason, context,
            )
            approver_email = APPROVAL_LEVELS[approval_level].get(
                "approver_email", "ops.manager@famproperties.com"
            )
            self.email_service.send_approval_request(
                approver_email, submission_id, approval_level, reason, context,
            )

        # Send completeness report
        report_data = {
            "completeness_pct": completeness["completeness_pct"],
            "transaction_type": transaction_type,
            "missing_documents": completeness["missing_documents"],
            "validation_issues": completeness["validation_issues"],
        }
        self.email_service.send_completeness_report(
            broker_email, broker_name, submission_id, report_data,
        )

        # Ops manager notification
        self.email_service.send_ops_manager_notification(
            f"Submission {'Auto-Approved' if approval_level == 'auto' else 'Pending Approval'}",
            submission_id,
            f"Broker: {broker_name}\nType: {transaction_type}\n"
            f"Completeness: {completeness['completeness_pct']}%\n"
            f"Approval Level: {approval_level.upper()}",
        )

        # Build rule-based analysis
        pct = completeness["completeness_pct"]
        if pct == 100 and check_result["critical_issues"] == 0:
            verdict, risk = "APPROVE", "LOW"
        elif pct >= 70:
            verdict, risk = "NEEDS_ATTENTION", "MEDIUM"
        else:
            verdict, risk = "REJECT", "HIGH"

        recommendations = []
        if completeness["missing_documents"]:
            recommendations.append(
                f"Submit {len(completeness['missing_documents'])} missing required document(s): "
                + ", ".join(d["name"] for d in completeness["missing_documents"][:3])
            )
        for issue in completeness["validation_issues"][:5]:
            recommendations.append(f"[{issue['severity'].upper()}] {issue['message']}")

        claude_analysis = {
            "verdict": verdict,
            "risk": risk,
            "recommendations": recommendations,
            "red_flags": [i["message"] for i in completeness["validation_issues"] if i["severity"] == "error"],
            "approval_level": approval_level,
            "completeness_pct": pct,
            "mode": "rule_based",
        }

        return {
            "submission_id": submission_id,
            "status": "approved" if approval_level == "auto" else "pending_approval",
            "transaction_type": transaction_type,
            "broker": {"name": broker_name, "email": broker_email},
            "property_ref": property_ref,
            "files_processed": file_count,
            "completeness": completeness,
            "approval_level": approval_level,
            "approval_request": approval_request.to_dict() if approval_request else None,
            "claude_analysis": claude_analysis,
            "emails_sent": self.email_service.email_count,
            "audit_trail": self.approval_engine.get_audit_log(),
            "processed_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Completeness check (used by both agentic and rule-based paths)
    # ------------------------------------------------------------------

    def _check_completeness(self, transaction_type: str, submitted_types: list) -> dict:
        """Check document completeness against requirements."""
        requirements = DOCUMENT_REQUIREMENTS.get(transaction_type)
        if not requirements:
            return {"error": f"Unknown transaction type: {transaction_type}"}

        required = requirements["required"]
        optional = requirements.get("optional", [])
        submitted_set = set(submitted_types)

        present_required = [d for d in required if d["id"] in submitted_set]
        missing_required = [d for d in required if d["id"] not in submitted_set]
        present_optional = [d for d in optional if d["id"] in submitted_set]
        missing_optional = [d for d in optional if d["id"] not in submitted_set]

        total_required = len(required)
        present_count = len(present_required)
        completeness_pct = round((present_count / total_required) * 100) if total_required > 0 else 0

        # Collect validation issues from file processing
        validation_issues = []
        for f in self.processor.processed_files:
            for issue in f.get("validation_issues", []):
                issue["file"] = f["file_name"]
                validation_issues.append(issue)

        # Check for unclassified files
        unclassified = [f for f in self.processor.processed_files if not f["classified_as"]]
        for f in unclassified:
            validation_issues.append({
                "severity": "warning",
                "code": "UNCLASSIFIED_DOCUMENT",
                "message": f"Could not classify '{f['file_name']}' — please verify manually",
                "file": f["file_name"],
            })

        return {
            "transaction_type": transaction_type,
            "transaction_label": requirements["label"],
            "completeness_pct": completeness_pct,
            "required_total": total_required,
            "required_present": present_count,
            "required_missing": len(missing_required),
            "present_documents": [d["name"] for d in present_required],
            "missing_documents": [{"name": d["name"], "description": d["description"], "id": d["id"]} for d in missing_required],
            "optional_present": [d["name"] for d in present_optional],
            "optional_missing": [d["name"] for d in missing_optional],
            "validation_issues": validation_issues,
            "expired_docs_count": 0,
        }

    def _build_approval_reason(self, completeness: dict, check_result: dict) -> str:
        """Build a human-readable approval reason."""
        reasons = []
        if check_result["missing_required"] > 0:
            missing_names = [d["name"] for d in completeness["missing_documents"]]
            reasons.append(f"Missing {check_result['missing_required']} required doc(s): {', '.join(missing_names[:3])}")
        if check_result["expired_docs"] > 0:
            reasons.append(f"{check_result['expired_docs']} expired document(s)")
        if check_result["critical_issues"] > 0:
            reasons.append(f"{check_result['critical_issues']} critical validation issue(s)")
        if check_result["warnings"] > 0:
            reasons.append(f"{check_result['warnings']} warning(s)")
        return "; ".join(reasons) if reasons else "Review required"

    # ------------------------------------------------------------------
    # Approval handling
    # ------------------------------------------------------------------

    def handle_approval_response(self, request_id: str, action: str,
                                    by: str, notes: str = "") -> dict:
        """Handle an incoming approval decision."""
        result = self.approval_engine.process_approval(request_id, action, by, notes)

        request = self.approval_engine.requests.get(request_id)
        if request and request.status in ("approved", "rejected"):
            sub_id = request.submission_id
            submission = self.submissions.get(sub_id)
            if submission:
                broker = submission["broker"]
                if request.status == "approved":
                    self.email_service.send(
                        broker["email"],
                        f"[fam Properties] Submission APPROVED — {sub_id}",
                        f"Dear {broker['name']},\n\nYour document submission {sub_id} has been approved.\n"
                        f"Approved by: {by}\nNotes: {notes or 'None'}\n\n"
                        f"Your transaction can now proceed to the next stage.\n\n"
                        f"Best regards,\nDocument Checker Agent\nfam Properties",
                    )
                else:
                    self.email_service.send(
                        broker["email"],
                        f"[fam Properties] Submission REQUIRES REVISION — {sub_id}",
                        f"Dear {broker['name']},\n\nYour document submission {sub_id} requires revision.\n"
                        f"Reason: {notes or 'See previous completeness report'}\n\n"
                        f"Please address the issues and resubmit.\n\n"
                        f"Best regards,\nDocument Checker Agent\nfam Properties",
                    )

        return result

    # ------------------------------------------------------------------
    # Status and dashboard
    # ------------------------------------------------------------------

    def get_submission_status(self, submission_id: str) -> dict:
        submission = self.submissions.get(submission_id)
        if not submission:
            return {"error": f"Submission {submission_id} not found"}
        approvals = self.approval_engine.get_submission_approvals(submission_id)
        return {
            "submission_id": submission_id,
            "status": submission["status"],
            "completeness": submission["completeness"].get("completeness_pct", 0),
            "approval_level": submission["approval_level"],
            "approvals": approvals,
            "emails_sent": submission["emails_sent"],
        }

    def get_dashboard(self) -> dict:
        return {
            "total_submissions": len(self.submissions),
            "by_status": {
                "approved": sum(1 for s in self.submissions.values() if s["status"] == "approved"),
                "pending": sum(1 for s in self.submissions.values() if s["status"] == "pending_approval"),
            },
            "approval_stats": self.approval_engine.get_stats(),
            "email_stats": self.email_service.get_email_stats(),
            "pending_approvals": self.approval_engine.get_pending_requests(),
            "sla_violations": self.approval_engine.check_sla_violations(),
        }
