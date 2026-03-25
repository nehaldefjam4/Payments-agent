"""
Payment Matching Engine -- Matches bank statement credit transactions
to Century units/clients using a multi-phase approach:

Phase 1: Unit number in transaction description (highest confidence)
Phase 2: Payer name matching against known client database
Phase 3: Amount matching against expected installments
Phase 4: Email proof of payment cross-reference

Each phase produces a confidence score. Transactions above the auto-match
threshold are matched automatically; those between review and auto thresholds
are flagged for human review; those below are left unmatched.
"""

import re
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher

from config.payment_settings import MATCHING_RULES
from processors.bank_statement_parser import Transaction


@dataclass
class ExpectedPayment:
    """An installment payment we expect to receive."""
    unit_no: str = ""
    client_name: str = ""
    client_email: str = ""
    installment_id: str = ""       # e.g., "post_q6"
    installment_label: str = ""    # e.g., "Q6 - 18 months from Handover"
    amount_due: float = 0.0
    due_date: str = ""
    status: str = "pending"        # pending, partial, paid, overdue
    nationality: str = ""
    dob: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchResult:
    """Result of attempting to match a transaction to a unit/client."""
    transaction_date: str = ""
    transaction_amount: float = 0.0
    transaction_description: str = ""
    matched_unit: str = ""
    matched_client: str = ""
    matched_installment: str = ""
    confidence: float = 0.0
    match_method: str = ""         # "unit_in_desc", "payer_name", "amount_match", "email_proof"
    status: str = "unmatched"      # "matched", "review", "unmatched"
    notes: str = ""
    # If multiple possible matches
    alternatives: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class PaymentMatcher:
    """Multi-phase payment matching engine."""

    def __init__(self, expected_payments: list[ExpectedPayment] = None):
        self.expected_payments = expected_payments or []
        self.match_results: list[MatchResult] = []

    def match_transactions(self, credits: list[Transaction]) -> list[MatchResult]:
        """
        Run the full matching pipeline on a list of credit transactions.
        Returns a MatchResult for each transaction.
        """
        self.match_results = []

        for tx in credits:
            result = self._match_single(tx)
            self.match_results.append(result)

        return self.match_results

    def _match_single(self, tx: Transaction) -> MatchResult:
        """Match a single credit transaction through all phases."""
        result = MatchResult(
            transaction_date=tx.date,
            transaction_amount=tx.credit,
            transaction_description=tx.description,
        )

        # Phase 1: Unit number in description
        unit, conf = self._phase1_unit_in_description(tx)
        if conf >= MATCHING_RULES["auto_match_confidence"]:
            result.matched_unit = unit
            result.confidence = conf
            result.match_method = "unit_in_desc"
            result.status = "matched"
            # Try to find the client for this unit
            client = self._find_client_for_unit(unit)
            if client:
                result.matched_client = client.client_name
                result.matched_installment = self._find_due_installment(unit, tx.credit)
            return result

        # Phase 2: Payer name matching
        client_match, name_conf = self._phase2_payer_name(tx)
        if name_conf >= MATCHING_RULES["auto_match_confidence"]:
            result.matched_unit = client_match.unit_no
            result.matched_client = client_match.client_name
            result.confidence = name_conf
            result.match_method = "payer_name"
            result.status = "matched"
            result.matched_installment = self._find_due_installment(
                client_match.unit_no, tx.credit
            )
            return result

        # Phase 3: Amount matching against expected payments
        amount_matches = self._phase3_amount_match(tx)
        if amount_matches:
            best = amount_matches[0]
            if best["confidence"] >= MATCHING_RULES["auto_match_confidence"]:
                result.matched_unit = best["unit_no"]
                result.matched_client = best["client_name"]
                result.matched_installment = best["installment_label"]
                result.confidence = best["confidence"]
                result.match_method = "amount_match"
                result.status = "matched"
            elif best["confidence"] >= MATCHING_RULES["review_confidence"]:
                result.matched_unit = best["unit_no"]
                result.matched_client = best["client_name"]
                result.matched_installment = best["installment_label"]
                result.confidence = best["confidence"]
                result.match_method = "amount_match"
                result.status = "review"
                result.notes = f"Amount matches {len(amount_matches)} possible unit(s)"
                result.alternatives = amount_matches[1:5]  # Top 5 alternatives
            return result

        # Partial matches -- combine signals
        combined_conf = 0.0
        if unit and conf > 0:
            result.matched_unit = unit
            combined_conf += conf * 0.5
        if client_match:
            result.matched_client = client_match.client_name
            if not result.matched_unit:
                result.matched_unit = client_match.unit_no
            combined_conf += name_conf * 0.3
        if amount_matches:
            combined_conf += amount_matches[0]["confidence"] * 0.2

        if combined_conf >= MATCHING_RULES["review_confidence"]:
            result.confidence = combined_conf
            result.match_method = "combined"
            result.status = "review"
            result.notes = "Multiple weak signals combined"
        else:
            result.status = "unmatched"
            result.confidence = combined_conf
            result.notes = "No confident match found"

        return result

    def _phase1_unit_in_description(self, tx: Transaction) -> tuple[str, float]:
        """Phase 1: Extract unit number from transaction description."""
        from processors.bank_statement_parser import BankStatementParser
        parser = BankStatementParser()
        return parser.extract_unit_from_description(tx.description)

    def _phase2_payer_name(self, tx: Transaction) -> tuple[ExpectedPayment | None, float]:
        """Phase 2: Match payer name in description against known clients."""
        if not self.expected_payments or not tx.description:
            return (None, 0.0)

        desc_upper = tx.description.upper()
        best_match = None
        best_score = 0.0

        for ep in self.expected_payments:
            if not ep.client_name:
                continue

            name_upper = ep.client_name.upper()

            # Exact substring match
            if name_upper in desc_upper:
                score = 0.95
            else:
                # Fuzzy match
                score = SequenceMatcher(None, name_upper, desc_upper).ratio()

                # Also try matching individual name parts
                name_parts = name_upper.split()
                parts_found = sum(1 for part in name_parts if part in desc_upper and len(part) > 2)
                if name_parts:
                    parts_score = parts_found / len(name_parts)
                    score = max(score, parts_score * 0.9)

            if score > best_score:
                best_score = score
                best_match = ep

        return (best_match, best_score)

    def _phase3_amount_match(self, tx: Transaction) -> list[dict]:
        """Phase 3: Match transaction amount against expected installment amounts."""
        if not self.expected_payments:
            return []

        tolerance = MATCHING_RULES["amount_tolerance_aed"]
        matches = []

        for ep in self.expected_payments:
            if ep.status == "paid":
                continue  # Skip already-paid installments

            diff = abs(tx.credit - ep.amount_due)
            if diff <= tolerance:
                # Exact or near-exact match
                confidence = max(0.0, 1.0 - (diff / max(ep.amount_due, 1)) * 10)
                # If only one unit expects this exact amount, higher confidence
                same_amount_count = sum(
                    1 for other in self.expected_payments
                    if other.status != "paid" and abs(other.amount_due - ep.amount_due) <= tolerance
                )
                if same_amount_count == 1:
                    confidence = min(confidence + 0.2, 1.0)
                elif same_amount_count > 3:
                    confidence *= 0.6  # Many units expect same amount = less confident

                matches.append({
                    "unit_no": ep.unit_no,
                    "client_name": ep.client_name,
                    "installment_label": ep.installment_label,
                    "amount_due": ep.amount_due,
                    "difference": diff,
                    "confidence": round(confidence, 3),
                })

        # Sort by confidence descending
        matches.sort(key=lambda m: m["confidence"], reverse=True)
        return matches

    def _find_client_for_unit(self, unit_no: str) -> ExpectedPayment | None:
        """Find the client record for a given unit number."""
        for ep in self.expected_payments:
            if ep.unit_no == unit_no:
                return ep
        return None

    def _find_due_installment(self, unit_no: str, amount: float) -> str:
        """Find which installment this payment likely corresponds to."""
        tolerance = MATCHING_RULES["amount_tolerance_aed"]
        for ep in self.expected_payments:
            if ep.unit_no == unit_no and ep.status != "paid":
                if abs(ep.amount_due - amount) <= tolerance:
                    return ep.installment_label
        # If no exact match, return the next due installment for this unit
        for ep in self.expected_payments:
            if ep.unit_no == unit_no and ep.status == "pending":
                return ep.installment_label
        return "Unknown installment"

    def get_summary(self) -> dict:
        """Return a summary of matching results."""
        matched = [r for r in self.match_results if r.status == "matched"]
        review = [r for r in self.match_results if r.status == "review"]
        unmatched = [r for r in self.match_results if r.status == "unmatched"]

        return {
            "total_transactions": len(self.match_results),
            "matched": len(matched),
            "needs_review": len(review),
            "unmatched": len(unmatched),
            "total_matched_amount": round(sum(r.transaction_amount for r in matched), 2),
            "total_review_amount": round(sum(r.transaction_amount for r in review), 2),
            "total_unmatched_amount": round(sum(r.transaction_amount for r in unmatched), 2),
            "by_method": {
                "unit_in_desc": len([r for r in matched if r.match_method == "unit_in_desc"]),
                "payer_name": len([r for r in matched if r.match_method == "payer_name"]),
                "amount_match": len([r for r in matched if r.match_method == "amount_match"]),
                "combined": len([r for r in matched if r.match_method == "combined"]),
            },
        }
