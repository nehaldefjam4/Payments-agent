"""
Document Processor — Extracts metadata, classifies documents, and validates them.
Uses Claude for intelligent document understanding when API key is available,
falls back to rule-based processing otherwise.
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


class DocumentProcessor:
    """Processes uploaded documents — extracts text, classifies type, validates."""

    DOCUMENT_SIGNATURES = {
        "emirates_id": ["emirates id", "identity card", "id card", "هوية"],
        "passport": ["passport", "travel document", "جواز سفر"],
        "title_deed": ["title deed", "ملكية", "land department", "دائرة الأراضي"],
        "noc_developer": ["no objection", "noc", "عدم ممانعة"],
        "spa": ["sale and purchase", "sale & purchase", "spa", "عقد بيع"],
        "form_f": ["form f", "listing agreement", "نموذج ف"],
        "form_a": ["form a", "buyer agreement", "tenant agreement", "نموذج أ"],
        "valuation_report": ["valuation", "appraisal", "تقييم"],
        "mortgage_clearance": ["mortgage clearance", "liability letter", "رهن"],
        "agency_agreement": ["agency agreement", "brokerage agreement", "اتفاقية وساطة"],
        "tenancy_contract": ["tenancy contract", "ejari", "عقد إيجار", "rental agreement"],
        "visa_copy": ["visa", "residence permit", "إقامة", "تأشيرة"],
        "salary_certificate": ["salary certificate", "employment letter", "شهادة راتب"],
        "bank_statement": ["bank statement", "account statement", "كشف حساب"],
        "company_trade_license": ["trade license", "commercial license", "رخصة تجارية"],
        "board_resolution": ["board resolution", "corporate resolution", "قرار مجلس"],
        "power_of_attorney": ["power of attorney", "poa", "توكيل"],
        "reservation_form": ["reservation", "booking form", "حجز"],
        "oqood_registration": ["oqood", "off-plan registration", "عقود"],
        "payment_plan": ["payment plan", "payment schedule", "خطة الدفع"],
        "security_deposit_receipt": ["security deposit", "deposit receipt", "تأمين"],
        "moa_aoa": ["memorandum of association", "articles of association", "moa", "aoa"],
    }

    def __init__(self):
        self.processed_files = []

    def process_file(self, file_path: str) -> dict:
        """Process a single document file and return metadata."""
        path = Path(file_path)

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        file_info = {
            "file_path": str(path.absolute()),
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
            "file_size_bytes": path.stat().st_size,
            "file_size_mb": round(path.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "checksum": self._compute_checksum(path),
            "extracted_text": "",
            "classified_as": None,
            "classification_confidence": 0.0,
            "validation_issues": [],
            "metadata": {},
        }

        # Extract text based on file type
        text = self._extract_text(path)
        file_info["extracted_text"] = text[:5000]  # Cap at 5000 chars

        # Classify document
        classification = self._classify_document(path.name, text)
        file_info["classified_as"] = classification["type"]
        file_info["classification_confidence"] = classification["confidence"]

        # Basic validation
        file_info["validation_issues"] = self._validate_file(path, file_info)

        # Extract dates if present
        file_info["metadata"]["detected_dates"] = self._extract_dates(text)

        self.processed_files.append(file_info)
        return file_info

    def process_submission(self, folder_path: str) -> dict:
        """Process all documents in a submission folder."""
        path = Path(folder_path)
        if not path.is_dir():
            return {"error": f"Not a directory: {folder_path}"}

        files = []
        for f in sorted(path.iterdir()):
            if f.is_file() and f.suffix.lower() in [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc", ".tiff"]:
                files.append(self.process_file(str(f)))

        return {
            "submission_folder": str(path),
            "total_files": len(files),
            "processed_at": datetime.now().isoformat(),
            "files": files,
        }

    def _extract_text(self, path: Path) -> str:
        """Extract text content from a file."""
        ext = path.suffix.lower()

        if ext == ".pdf" and PdfReader:
            try:
                reader = PdfReader(str(path))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
                return text.strip()
            except Exception as e:
                return f"[PDF extraction error: {e}]"

        elif ext == ".docx" and DocxDocument:
            try:
                doc = DocxDocument(str(path))
                return "\n".join([p.text for p in doc.paragraphs]).strip()
            except Exception as e:
                return f"[DOCX extraction error: {e}]"

        elif ext in [".txt", ".csv"]:
            try:
                return path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception as e:
                return f"[Text extraction error: {e}]"

        elif ext in [".jpg", ".jpeg", ".png", ".tiff"]:
            # For images, we rely on Claude Vision when available
            return "[Image file — requires OCR/Vision for text extraction]"

        return "[Unsupported file type for text extraction]"

    def _classify_document(self, filename: str, text: str) -> dict:
        """Classify a document based on filename and content."""
        filename_lower = filename.lower().replace("_", " ").replace("-", " ")
        text_lower = text.lower()
        combined = f"{filename_lower} {text_lower}"

        best_match = None
        best_score = 0

        for doc_type, keywords in self.DOCUMENT_SIGNATURES.items():
            score = 0
            for keyword in keywords:
                if keyword in filename_lower:
                    score += 3  # Filename match is strong signal
                if keyword in text_lower:
                    score += 2  # Content match

            if score > best_score:
                best_score = score
                best_match = doc_type

        confidence = min(1.0, best_score / 5.0)  # Normalize to 0-1

        return {
            "type": best_match,
            "confidence": round(confidence, 2),
        }

    def _validate_file(self, path: Path, file_info: dict) -> list:
        """Run basic validation checks on a file."""
        issues = []

        # Check file size
        if file_info["file_size_mb"] > 25:
            issues.append({
                "severity": "error",
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds 25MB limit ({file_info['file_size_mb']}MB)",
            })

        if file_info["file_size_bytes"] < 1000:
            issues.append({
                "severity": "warning",
                "code": "FILE_TOO_SMALL",
                "message": "File is suspiciously small — may be blank or corrupt",
            })

        # Check allowed file types
        allowed = [".pdf", ".jpg", ".jpeg", ".png", ".docx", ".doc", ".tiff"]
        if path.suffix.lower() not in allowed:
            issues.append({
                "severity": "error",
                "code": "UNSUPPORTED_FORMAT",
                "message": f"File type {path.suffix} not accepted. Use: {', '.join(allowed)}",
            })

        # Check for empty content
        if not file_info["extracted_text"] or file_info["extracted_text"].startswith("["):
            if path.suffix.lower() in [".pdf", ".docx"]:
                issues.append({
                    "severity": "warning",
                    "code": "NO_TEXT_EXTRACTED",
                    "message": "Could not extract text — file may be scanned/image-only",
                })

        return issues

    def _extract_dates(self, text: str) -> list:
        """Extract date-like patterns from text."""
        import re
        dates = []

        # Common date patterns
        patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches[:10])  # Cap at 10

        return list(set(dates))

    def _compute_checksum(self, path: Path) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]  # Short hash for display
