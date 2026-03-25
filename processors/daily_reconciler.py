"""
Daily Reconciler -- The core engine that Amit runs daily.

Input:  Two new bank statements (Escrow + Corporate) from Geo
        + The master Excel sheet with historical reconciled data

Process:
1. Load master sheet to build knowledge base (unit->name, ref->unit, name->unit)
2. Parse new Escrow and Corporate statements
3. Find NEW transactions (not already in master sheet, matched by Transaction Reference)
4. Match new transactions to units using: knowledge base + narration patterns + cross-reference
5. Append matched new transactions to the master sheet
6. Generate receipt PDFs for each matched new credit

Output: Updated master Excel + receipt PDFs + summary
"""

import os
import re
import copy
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from processors.bank_statement_parser import BankStatementParser, Transaction
from processors.pdf_generator import generate_receipt
from config.payment_settings import NAME_VARIANTS

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@dataclass
class NewTransaction:
    """A new transaction found in the daily statement that's not in the master sheet."""
    account: str = ""           # "escrow" or "corporate"
    date: str = ""
    value_date: str = ""
    narration: str = ""
    reference: str = ""
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    # Matching results
    unit_no: str = ""
    account_name: str = ""      # Client/buyer name
    match_method: str = ""
    match_confidence: float = 0.0
    receipt_generated: bool = False
    receipt_path: str = ""

    def to_dict(self):
        return asdict(self)


class DailyReconciler:
    """
    The daily reconciliation engine.
    Replaces Amit's manual process of checking bank statements and updating the master sheet.
    """

    def __init__(self):
        # Knowledge base built from master sheet
        self.kb_ref_to_unit: dict[str, str] = {}       # transaction_ref -> unit
        self.kb_ref_to_name: dict[str, str] = {}       # transaction_ref -> client name
        self.kb_name_to_unit: dict[str, str] = {}       # normalized_name -> unit
        self.kb_unit_to_name: dict[str, str] = {}       # unit -> client name
        self.existing_refs_escrow: set[str] = set()     # refs already in escrow sheet
        self.existing_refs_corporate: set[str] = set()  # refs already in corporate sheet
        self.latest_date_escrow: datetime = None        # latest date in escrow sheet
        self.latest_date_corporate: datetime = None     # latest date in corporate sheet

        self.new_transactions: list[NewTransaction] = []
        self.receipts_generated: list[dict] = []

    # =================================================================
    # STEP 1: Load master sheet and build knowledge base
    # =================================================================

    def load_master_sheet(self, master_path: str) -> dict:
        """Load the master Excel and build the knowledge base from existing data."""
        wb = openpyxl.load_workbook(master_path, data_only=True)

        stats = {"escrow_rows": 0, "corporate_rows": 0, "units_known": 0, "names_known": 0}

        # Load Escrow sheet
        if "Updated Sheet_Escrow Account" in wb.sheetnames:
            ws = wb["Updated Sheet_Escrow Account"]
            stats["escrow_rows"] = self._load_sheet_to_kb(ws, "escrow", has_account_name=True)

        # Load Corporate sheet
        if "Updated Sheet_Corporate" in wb.sheetnames:
            ws = wb["Updated Sheet_Corporate"]
            stats["corporate_rows"] = self._load_sheet_to_kb(ws, "corporate", has_account_name=True)

        # Also check Corporate Recon sheet
        if "Corporate Recon as of 250524" in wb.sheetnames:
            ws = wb["Corporate Recon as of 250524"]
            self._load_recon_sheet(ws)

        stats["units_known"] = len(self.kb_unit_to_name)
        stats["names_known"] = len(self.kb_name_to_unit)
        stats["refs_escrow"] = len(self.existing_refs_escrow)
        stats["refs_corporate"] = len(self.existing_refs_corporate)
        stats["cutoff_escrow"] = self.latest_date_escrow.strftime("%d-%m-%Y") if self.latest_date_escrow else "N/A"
        stats["cutoff_corporate"] = self.latest_date_corporate.strftime("%d-%m-%Y") if self.latest_date_corporate else "N/A"

        # Find unreconciled rows and try to match them
        self._unreconciled_rows = []
        self._scan_unreconciled(wb)
        stats["unreconciled_found"] = len(self._unreconciled_rows)
        stats["unreconciled_matched"] = sum(1 for u in self._unreconciled_rows if u.get("unit_no"))

        return stats

    def _scan_unreconciled(self, wb):
        """Scan master sheet for rows without a unit assignment and try to match them."""
        from processors.bank_statement_parser import BankStatementParser
        parser = BankStatementParser()

        for sheet_name, unit_col, narr_col, credit_col, acct_type in [
            ("Updated Sheet_Escrow Account", 8, 3, 6, "escrow"),
            ("Updated Sheet_Corporate", 7, 2, 5, "corporate"),
        ]:
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]

            for r in range(2, ws.max_row + 1):
                credit = ws.cell(r, credit_col).value
                if not credit:
                    continue
                try:
                    credit_float = float(str(credit).replace(",", ""))
                except (ValueError, TypeError):
                    continue
                if credit_float <= 0:
                    continue

                unit_val = ws.cell(r, unit_col).value
                unit_str = str(unit_val).strip() if unit_val else ""

                # Skip rows that already have a unit
                if unit_str and unit_str not in ("0", "0.0", "None", "", "UNMATCHED"):
                    continue

                narr = str(ws.cell(r, narr_col).value or "")
                date_val = ws.cell(r, 1).value

                # Try to match using narration patterns
                unit, conf = parser.extract_unit_from_description(narr)
                name = parser.extract_name_from_description(narr)
                match_method = ""

                if unit and conf >= 0.80:
                    match_method = "unit_in_narration"
                elif name:
                    normalized = self._normalize_name(name)
                    if normalized in self.kb_name_to_unit:
                        unit = self.kb_name_to_unit[normalized]
                        conf = 0.85
                        match_method = "name_from_kb"

                self._unreconciled_rows.append({
                    "row": r,
                    "sheet": sheet_name,
                    "account": acct_type,
                    "date": str(date_val) if date_val else "",
                    "narration": narr[:80],
                    "credit": credit_float,
                    "unit_no": unit,
                    "account_name": name or (self.kb_unit_to_name.get(unit, "") if unit else ""),
                    "match_method": match_method,
                    "match_confidence": conf if unit else 0.0,
                })

    def _load_sheet_to_kb(self, ws, account_type: str, has_account_name: bool = False) -> int:
        """Load a sheet and extract knowledge base entries."""
        rows_loaded = 0

        for r in range(2, ws.max_row + 1):
            # Get transaction reference (column D for escrow, column C for corporate)
            if account_type == "escrow":
                date_val = ws.cell(r, 1).value  # Column A
                ref_val = ws.cell(r, 4).value   # Column D
                unit_val = ws.cell(r, 8).value  # Column H: "Unit No. / Remarks"
                name_val = ws.cell(r, 9).value  # Column I: "Account Name"
            else:  # corporate
                date_val = ws.cell(r, 1).value  # Column A
                ref_val = ws.cell(r, 3).value   # Column C
                unit_val = ws.cell(r, 7).value  # Column G: "Unit No. / Remarks"
                name_val = ws.cell(r, 8).value  # Column H: "Account Name"

            if not ref_val:
                continue

            ref = str(ref_val).strip()
            if not ref:
                continue

            # Track latest date
            parsed_date = self._parse_date(date_val)
            if parsed_date:
                if account_type == "escrow":
                    if not self.latest_date_escrow or parsed_date > self.latest_date_escrow:
                        self.latest_date_escrow = parsed_date
                else:
                    if not self.latest_date_corporate or parsed_date > self.latest_date_corporate:
                        self.latest_date_corporate = parsed_date

            # Track existing refs
            if account_type == "escrow":
                self.existing_refs_escrow.add(ref)
            else:
                self.existing_refs_corporate.add(ref)

            rows_loaded += 1

            # Extract unit number
            unit = ""
            if unit_val:
                unit_str = str(unit_val).strip()
                # Handle formats: "1701.0", "802 - Johanna", "1308 - Sagal", "1002.0"
                m = re.match(r'(\d{3,4})', unit_str)
                if m:
                    unit = m.group(1)

            # Extract client name
            name = ""
            if name_val:
                name = str(name_val).strip().split('\n')[0]  # Take first line

            # Build knowledge base
            if unit:
                self.kb_ref_to_unit[ref] = unit
                if name:
                    self.kb_ref_to_name[ref] = name
                    self.kb_unit_to_name[unit] = name
                    normalized = self._normalize_name(name)
                    if len(normalized) > 3:
                        self.kb_name_to_unit[normalized] = unit

        return rows_loaded

    def _load_recon_sheet(self, ws):
        """Load Corporate Recon sheet for additional unit-name mappings."""
        for r in range(2, ws.max_row + 1):
            remarks = ws.cell(r, 8).value  # Column H: Remarks "Unit No. 1308 - Sivan Hanouchian"
            ref = ws.cell(r, 4).value       # Column D: Transaction Reference

            if not remarks:
                continue

            remarks_str = str(remarks).strip()
            m = re.match(r'Unit\s*No\.?\s*(\d{3,4})\s*-\s*(.+)', remarks_str)
            if m:
                unit = m.group(1)
                name = m.group(2).strip()
                if unit and name:
                    self.kb_unit_to_name[unit] = name
                    normalized = self._normalize_name(name)
                    if len(normalized) > 3:
                        self.kb_name_to_unit[normalized] = unit
                    if ref:
                        self.kb_ref_to_unit[str(ref).strip()] = unit
                        self.kb_ref_to_name[str(ref).strip()] = name

    # =================================================================
    # STEP 2: Parse new statements and find new transactions
    # =================================================================

    def process_new_statements(
        self,
        escrow_path: str = None,
        corporate_path: str = None,
    ) -> dict:
        """Parse new bank statements and find transactions not in the master sheet."""
        results = {"escrow_new": 0, "corporate_new": 0, "total_new": 0}

        if escrow_path:
            parser = BankStatementParser()
            result = parser.parse(escrow_path)
            if not result.get("error"):
                new_count = self._find_new_transactions(parser, "escrow")
                results["escrow_new"] = new_count
                results["escrow_total"] = result["total_transactions"]

        if corporate_path:
            parser = BankStatementParser()
            result = parser.parse(corporate_path)
            if not result.get("error"):
                new_count = self._find_new_transactions(parser, "corporate")
                results["corporate_new"] = new_count
                results["corporate_total"] = result["total_transactions"]

        results["total_new"] = len(self.new_transactions)
        return results

    def _find_new_transactions(self, parser: BankStatementParser, account_type: str) -> int:
        """Find transactions not already in the master sheet. Only looks at transactions AFTER the latest date."""
        existing_refs = self.existing_refs_escrow if account_type == "escrow" else self.existing_refs_corporate
        cutoff_date = self.latest_date_escrow if account_type == "escrow" else self.latest_date_corporate
        new_count = 0

        for tx in parser.transactions:
            ref = tx.reference.strip()

            # DATE FILTER: only consider transactions on or after the latest date in master
            if cutoff_date:
                tx_date = self._parse_date(tx.date)
                if tx_date and tx_date < cutoff_date:
                    continue  # Skip older transactions, master sheet is correct till cutoff

            # Check if this reference already exists in the master sheet
            is_existing = False
            if ref in existing_refs:
                is_existing = True
            else:
                # Fuzzy: check if the ref's first 15 chars match any existing ref
                ref_prefix = ref[:15] if len(ref) > 15 else ref
                for existing in existing_refs:
                    if existing.startswith(ref_prefix) or ref.startswith(existing[:15]):
                        is_existing = True
                        break

            if is_existing:
                continue

            # This is a NEW transaction
            new_tx = NewTransaction(
                account=account_type,
                date=tx.date,
                value_date=tx.value_date,
                narration=tx.description[:80],
                reference=ref,
                debit=tx.debit,
                credit=tx.credit,
                balance=tx.balance,
            )

            # Match to unit using multiple methods
            self._match_new_transaction(new_tx, parser)

            self.new_transactions.append(new_tx)
            new_count += 1

        return new_count

    # =================================================================
    # STEP 3: Match new transactions to units
    # =================================================================

    def _match_new_transaction(self, tx: NewTransaction, parser: BankStatementParser):
        """Match a new transaction to a unit using all available methods."""

        # Method 1: Unit number in narration
        unit, conf = parser.extract_unit_from_description(tx.narration)
        if unit and conf >= 0.80:
            tx.unit_no = unit
            tx.match_confidence = conf
            tx.match_method = "unit_in_narration"
            # Look up name from knowledge base
            tx.account_name = self.kb_unit_to_name.get(unit, "")
            return

        # Method 2: Name in narration -> match to known unit
        name = parser.extract_name_from_description(tx.narration)
        if name and len(name) > 3:
            normalized = self._normalize_name(name)

            # Exact KB match
            if normalized in self.kb_name_to_unit:
                tx.unit_no = self.kb_name_to_unit[normalized]
                tx.account_name = name
                tx.match_confidence = 0.85
                tx.match_method = "name_from_kb"
                return

            # Partial KB match: check if extracted name is a substring of any KB name or vice versa
            for kb_name, kb_unit in self.kb_name_to_unit.items():
                if len(normalized) > 5 and len(kb_name) > 5:
                    if normalized in kb_name or kb_name in normalized:
                        tx.unit_no = kb_unit
                        tx.account_name = name
                        tx.match_confidence = 0.82
                        tx.match_method = "name_substring"
                        return

            # Fuzzy name match (improved with Arabic variants)
            best_unit, best_score = self._fuzzy_name_match(normalized)
            if best_unit and best_score >= 0.4:
                tx.unit_no = best_unit
                tx.account_name = name
                tx.match_confidence = round(min(0.80, best_score * 0.85), 2)
                tx.match_method = "name_fuzzy"
                return

            # Store the extracted name even if no unit match
            tx.account_name = name

        # Method 2b: Direct narration scan — search all KB names in the narration
        narr_upper = tx.narration.upper()
        for kb_name, kb_unit in self.kb_name_to_unit.items():
            # Only try names with at least 2 significant parts
            parts = [p for p in kb_name.split() if len(p) > 2]
            if len(parts) < 2:
                continue
            # Check if last name (most distinctive) + any other part appears in narration
            last = parts[-1]
            if last in narr_upper and any(p in narr_upper for p in parts[:-1]):
                tx.unit_no = kb_unit
                tx.account_name = self.kb_unit_to_name.get(kb_unit, kb_name)
                tx.match_confidence = 0.75
                tx.match_method = "name_in_narration"
                return

        # Method 3: IBAN/account matching from narration
        iban = parser.extract_iban_from_description(tx.narration)
        if iban:
            # Check if we've seen this IBAN before with a unit
            for ref, known_unit in self.kb_ref_to_unit.items():
                # This is a simplistic check; in practice you'd track IBANs
                pass

        # No match found
        tx.match_method = "unmatched"
        tx.match_confidence = 0.0

    def _fuzzy_name_match(self, normalized_name: str) -> tuple[str, float]:
        """Fuzzy match a name against the knowledge base with Arabic name variant support."""
        parts = normalized_name.split()
        if len(parts) < 2:
            return ("", 0.0)

        # Expand parts with Arabic name variants
        expanded_parts = set(parts)
        for p in parts:
            for canonical, variants in NAME_VARIANTS.items():
                if p == canonical or p in variants:
                    expanded_parts.add(canonical)
                    expanded_parts.update(variants)

        best_unit = ""
        best_score = 0.0

        for kb_name, kb_unit in self.kb_name_to_unit.items():
            kb_parts = set(kb_name.split())

            # Expand KB parts with variants too
            kb_expanded = set(kb_parts)
            for kp in kb_parts:
                for canonical, variants in NAME_VARIANTS.items():
                    if kp == canonical or kp in variants:
                        kb_expanded.add(canonical)
                        kb_expanded.update(variants)

            # Token overlap
            matches = sum(
                1 for p in expanded_parts
                if any(
                    p == kp or (len(p) > 2 and len(kp) > 2 and (p in kp or kp in p))
                    for kp in kb_expanded
                ) and len(p) > 2
            )
            significant_parts = [p for p in parts if len(p) > 2]
            if not significant_parts:
                continue

            score = matches / max(len(significant_parts), len([k for k in kb_parts if len(k) > 2]))

            # Bonus: if last name matches (most distinctive part)
            if len(parts) >= 2 and len(kb_parts) >= 2:
                if parts[-1] in kb_expanded or any(parts[-1] == kp for kp in kb_expanded):
                    score = min(1.0, score + 0.15)

            if score > best_score and score >= 0.4:
                best_score = score
                best_unit = kb_unit

        return (best_unit, best_score)

    # =================================================================
    # STEP 4: Update master sheet with new transactions
    # =================================================================

    def update_master_sheet(self, master_path: str, output_path: str) -> dict:
        """Append new transactions to the master sheet and save."""
        wb = openpyxl.load_workbook(master_path)

        escrow_added = 0
        corporate_added = 0

        # Styles for new rows
        new_fill = PatternFill(start_color="FFF9E6", end_color="FFF9E6", fill_type="solid")
        matched_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        unmatched_fill = PatternFill(start_color="FFEBEE", end_color="FFEBEE", fill_type="solid")

        for tx in self.new_transactions:
            if tx.account == "escrow" and "Updated Sheet_Escrow Account" in wb.sheetnames:
                ws = wb["Updated Sheet_Escrow Account"]
                next_row = ws.max_row + 1
                ws.cell(next_row, 1, tx.date)
                ws.cell(next_row, 2, tx.value_date)
                ws.cell(next_row, 3, tx.narration)
                ws.cell(next_row, 4, tx.reference)
                ws.cell(next_row, 5, tx.debit if tx.debit else 0)
                ws.cell(next_row, 6, tx.credit if tx.credit else 0)
                ws.cell(next_row, 7, tx.balance)
                ws.cell(next_row, 8, f"{tx.unit_no}" if tx.unit_no else "UNMATCHED")
                ws.cell(next_row, 9, tx.account_name)
                ws.cell(next_row, 10, "")  # Receipt
                ws.cell(next_row, 11, "NEW" if tx.unit_no else "PENDING")

                fill = matched_fill if tx.unit_no else unmatched_fill
                for c in range(1, 12):
                    ws.cell(next_row, c).fill = fill

                escrow_added += 1

            elif tx.account == "corporate" and "Updated Sheet_Corporate" in wb.sheetnames:
                ws = wb["Updated Sheet_Corporate"]
                next_row = ws.max_row + 1
                ws.cell(next_row, 1, tx.date)
                ws.cell(next_row, 2, tx.narration)
                ws.cell(next_row, 3, tx.reference)
                ws.cell(next_row, 4, tx.debit if tx.debit else 0)
                ws.cell(next_row, 5, tx.credit if tx.credit else 0)
                ws.cell(next_row, 6, tx.balance)
                ws.cell(next_row, 7, f"{tx.unit_no}" if tx.unit_no else "UNMATCHED")
                ws.cell(next_row, 8, tx.account_name)

                fill = matched_fill if tx.unit_no else unmatched_fill
                for c in range(1, 9):
                    ws.cell(next_row, c).fill = fill

                corporate_added += 1

        # Also update previously unreconciled rows that we matched
        updated_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")  # light blue
        unreconciled_updated = 0

        for ur in self._unreconciled_rows:
            if not ur.get("unit_no"):
                continue
            sheet = ur["sheet"]
            row = ur["row"]
            if sheet in wb.sheetnames:
                ws = wb[sheet]
                unit_col = 8 if sheet.startswith("Updated Sheet_E") else 7
                name_col = 9 if sheet.startswith("Updated Sheet_E") else 8

                ws.cell(row, unit_col, str(ur["unit_no"]))
                ws.cell(row, name_col, ur.get("account_name", ""))

                for c in range(1, name_col + 1):
                    ws.cell(row, c).fill = updated_fill

                unreconciled_updated += 1

        wb.save(output_path)
        return {
            "escrow_added": escrow_added,
            "corporate_added": corporate_added,
            "total_added": escrow_added + corporate_added,
            "unreconciled_updated": unreconciled_updated,
            "output_path": output_path,
        }

    # =================================================================
    # STEP 5: Generate receipts for matched credits
    # =================================================================

    def generate_receipts(self, output_dir: str) -> list[dict]:
        """Generate receipt PDFs for all matched new credit transactions."""
        os.makedirs(output_dir, exist_ok=True)
        self.receipts_generated = []

        for tx in self.new_transactions:
            if not tx.unit_no or tx.credit <= 0:
                continue

            receipt_no = f"REC-{tx.date.replace('-', '')}-{tx.unit_no}-{tx.reference[:8]}"
            filename = f"Receipt_{tx.unit_no}_{tx.date.replace('-', '')}_{receipt_no[-6:]}.pdf"
            filepath = os.path.join(output_dir, filename)

            try:
                generate_receipt(
                    output_path=filepath,
                    receipt_no=receipt_no,
                    unit_no=tx.unit_no,
                    client_name=tx.account_name or "Valued Client",
                    payment_date=tx.date,
                    amount=tx.credit,
                    installment_type=self._guess_installment_type(tx),
                    payment_method="Bank Transfer",
                    reference=tx.reference,
                    narration=tx.narration,
                )

                tx.receipt_generated = True
                tx.receipt_path = filepath

                self.receipts_generated.append({
                    "unit_no": tx.unit_no,
                    "client_name": tx.account_name,
                    "amount": tx.credit,
                    "receipt_no": receipt_no,
                    "filepath": filepath,
                    "account": tx.account,
                })
            except Exception as e:
                print(f"  Error generating receipt for Unit {tx.unit_no}: {e}")

        return self.receipts_generated

    def _guess_installment_type(self, tx: NewTransaction) -> str:
        """Guess the installment type from the narration."""
        narr = tx.narration.upper()
        if "DLD" in narr or "REGISTRATION" in narr:
            return "DLD Registration Fee"
        if "BOOKING" in narr or "DOWN PAYMENT" in narr:
            return "Booking / Down Payment"
        if "HANDOVER" in narr:
            return "On Handover"
        if re.search(r'Q[1-8]', narr):
            m = re.search(r'(Q[1-8])', narr)
            return f"{m.group(1)} Installment"
        if tx.account == "corporate":
            return "Commission / DLD Fee"
        return "Installment Payment"

    # =================================================================
    # STEP 6: Claude AI Matching for remaining unmatched
    # =================================================================

    def run_ai_matching(self, api_key: str = None) -> list[dict]:
        """
        Use Claude to analyze unmatched transactions and suggest matches.
        Returns list of AI match suggestions with reasoning.
        """
        from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, AI_MATCHING_PROMPT

        key = api_key or os.environ.get("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
        if not key or not HAS_ANTHROPIC:
            return []

        unmatched = [t for t in self.new_transactions if not t.unit_no and t.credit > 0]
        if not unmatched:
            return []

        # Build context for Claude
        kb_summary = []
        for unit, name in sorted(self.kb_unit_to_name.items()):
            kb_summary.append(f"  Unit {unit}: {name}")

        tx_list = []
        for i, tx in enumerate(unmatched):
            tx_list.append(
                f"  [{i}] Date: {tx.date} | Amount: AED {tx.credit:,.2f} | "
                f"Narration: {tx.narration} | Ref: {tx.reference} | "
                f"Extracted name: {tx.account_name or 'none'}"
            )

        prompt = f"""Analyze these unmatched bank transactions and match them to units.

KNOWLEDGE BASE — Unit to Client Mappings:
{chr(10).join(kb_summary[:150])}

UNMATCHED TRANSACTIONS:
{chr(10).join(tx_list)}

For each transaction, respond with a JSON array where each element has:
- "index": transaction index from the list above
- "unit_no": matched unit number (string) or "" if no match
- "confidence": 0.0 to 1.0
- "reasoning": brief explanation
- "match_method": "ai_name_match" or "ai_amount_match" or "ai_pattern" or "ai_no_match"

Only return the JSON array, no other text."""

        try:
            client = anthropic.Anthropic(api_key=key)
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=AI_MATCHING_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            text = response.content[0].text.strip()
            # Extract JSON from response (handle markdown code blocks)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            suggestions = json.loads(text)
            ai_results = []

            for suggestion in suggestions:
                idx = suggestion.get("index", -1)
                unit_no = suggestion.get("unit_no", "")
                confidence = float(suggestion.get("confidence", 0))
                reasoning = suggestion.get("reasoning", "")
                method = suggestion.get("match_method", "ai_match")

                if 0 <= idx < len(unmatched) and unit_no and confidence >= 0.6:
                    tx = unmatched[idx]
                    tx.unit_no = unit_no
                    tx.match_confidence = confidence
                    tx.match_method = method
                    # Look up name from KB if not already set
                    if not tx.account_name:
                        tx.account_name = self.kb_unit_to_name.get(unit_no, "")

                ai_results.append({
                    "index": idx,
                    "narration": unmatched[idx].narration if 0 <= idx < len(unmatched) else "",
                    "amount": unmatched[idx].credit if 0 <= idx < len(unmatched) else 0,
                    "unit_no": unit_no,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "method": method,
                    "applied": bool(unit_no and confidence >= 0.6),
                })

            return ai_results

        except Exception as e:
            print(f"  AI matching error: {e}")
            return [{"error": str(e)}]

    # =================================================================
    # Salesforce Integration
    # =================================================================

    def sync_with_salesforce(self, sf_service=None, project_name: str = None) -> list[dict]:
        """
        For each matched transaction, look up the unit in Salesforce,
        identify which installment(s) the payment covers, and prepare
        SF actions (update payment status, create receipt, send email).
        All actions respect SF_WRITE_MODE and EMAIL_LIVE_MODE flags.
        """
        if sf_service is None:
            return []

        sf_actions = []
        matched = [t for t in self.new_transactions if t.unit_no and t.credit > 0]

        for tx in matched:
            try:
                # Identify installments covered by this payment
                installments = sf_service.identify_installments_for_amount(
                    unit_name=tx.unit_no,
                    bank_amount=tx.credit,
                    project_name=project_name,
                )

                if not installments:
                    sf_actions.append({
                        "unit": tx.unit_no,
                        "amount": tx.credit,
                        "action": "no_sf_match",
                        "message": f"No matching installment found in SF for AED {tx.credit:,.2f}",
                        "results": [],
                    })
                    continue

                tx_actions = []
                for inst in installments:
                    payment = inst["payment"]
                    allocated = inst["allocated_amount"]
                    match_type = inst["match_type"]

                    # Update payment amount_paid
                    new_paid = payment.amount_paid + allocated
                    update_result = sf_service.update_payment_amount_paid(
                        booking_payment_id=payment.sf_id,
                        new_amount_paid=new_paid,
                        notes=f"Bank ref: {tx.reference} | {tx.narration[:50]}",
                    )
                    tx_actions.append(update_result.to_dict())

                    # Create receipt
                    receipt_result = sf_service.create_receipt_record(
                        inventory_id=payment.inventory_id,
                        amount=allocated,
                        payment_type=payment.payment_type,
                        payment_date=tx.date,
                        reference=tx.reference,
                    )
                    tx_actions.append(receipt_result.to_dict())

                sf_actions.append({
                    "unit": tx.unit_no,
                    "amount": tx.credit,
                    "action": "sf_sync",
                    "installments_matched": len(installments),
                    "match_type": installments[0]["match_type"] if installments else "",
                    "message": f"Matched {len(installments)} installment(s)",
                    "results": tx_actions,
                })

            except Exception as e:
                sf_actions.append({
                    "unit": tx.unit_no,
                    "amount": tx.credit,
                    "action": "error",
                    "message": str(e),
                    "results": [],
                })

        return sf_actions

    # =================================================================
    # SUMMARY
    # =================================================================

    def get_summary(self) -> dict:
        """Get a summary of the daily reconciliation."""
        matched = [t for t in self.new_transactions if t.unit_no]
        unmatched = [t for t in self.new_transactions if not t.unit_no]

        # Break down by match method
        by_method = {}
        for t in matched:
            m = t.match_method or "unknown"
            by_method[m] = by_method.get(m, 0) + 1

        # Unreconciled rows from master sheet
        ur_matched = [u for u in self._unreconciled_rows if u.get("unit_no")]
        ur_still = [u for u in self._unreconciled_rows if not u.get("unit_no")]

        return {
            "total_new_transactions": len(self.new_transactions),
            "matched": len(matched),
            "unmatched": len(unmatched),
            "receipts_generated": len(self.receipts_generated),
            "by_account": {
                "escrow": len([t for t in self.new_transactions if t.account == "escrow"]),
                "corporate": len([t for t in self.new_transactions if t.account == "corporate"]),
            },
            "by_method": by_method,
            "matched_details": [t.to_dict() for t in matched],
            "unmatched_details": [t.to_dict() for t in unmatched],
            "receipts": self.receipts_generated,
            "unreconciled": {
                "total_found": len(self._unreconciled_rows),
                "now_matched": len(ur_matched),
                "still_unmatched": len(ur_still),
                "matched_details": ur_matched,
                "unmatched_details": ur_still,
            },
        }

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a name for matching."""
        n = name.upper().strip()
        n = re.sub(r'\b([A-Z])\s+(?=[A-Z]{2,})', r'\1', n)
        n = re.sub(r'\s+', ' ', n)
        return n

    @staticmethod
    def _parse_date(val) -> datetime:
        """Parse a date value from Excel (string or datetime object).
        Handles DD-MM-YYYY strings and Excel datetime objects where
        openpyxl may have swapped month/day."""
        if not val:
            return None

        today = datetime.now()

        if isinstance(val, datetime):
            # If the date is in the future, month and day may be swapped
            # e.g., datetime(2026, 7, 3) should be March 7 not July 3
            if val > today and val.day <= 12:
                try:
                    swapped = val.replace(month=val.day, day=val.month)
                    if swapped <= today:
                        return swapped
                except ValueError:
                    pass
            return val

        s = str(val).strip()
        # Try DD-MM-YYYY first (most common in ENBD statements)
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y"):
            try:
                return datetime.strptime(s.split(" ")[0] if " " in s else s, fmt)
            except ValueError:
                continue
        # Then ISO format
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s.split(" ")[0] if " " in s else s, fmt)
            except ValueError:
                continue
        return None
