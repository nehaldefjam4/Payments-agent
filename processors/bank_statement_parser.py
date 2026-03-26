"""
Bank Statement Parser -- Extracts credit and debit transactions from
Emirates NBD bank statements (Century escrow account).

Supports:
  - PDF statements (tabular, multi-line descriptions)
  - Excel (.xlsx / .xls) statements
  - CSV statements
"""

import re
import csv
import io
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    import xlrd
    HAS_XLRD = True
except ImportError:
    HAS_XLRD = False


@dataclass
class Transaction:
    """A single bank statement transaction."""
    date: str = ""                  # DD/MM/YYYY or similar
    value_date: str = ""            # Value date if separate
    description: str = ""           # Full description (may be multi-line)
    reference: str = ""             # Transfer/cheque reference number
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    tx_type: str = ""               # "credit" or "debit"
    # Matching fields (populated later by matching engine)
    matched_unit: str = ""
    matched_client: str = ""
    match_confidence: float = 0.0
    match_method: str = ""          # "unit_in_desc", "amount_match", "email_proof", "manual"
    match_status: str = "unmatched" # "matched", "review", "unmatched"

    def to_dict(self) -> dict:
        return asdict(self)


class BankStatementParser:
    """Parse Emirates NBD bank statement PDFs into structured transactions."""

    # Common date patterns in ENBD statements
    DATE_PATTERN = re.compile(
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
    )

    # Amount pattern: handles commas and decimals (e.g., "1,234,567.89")
    AMOUNT_PATTERN = re.compile(
        r'([\d,]+\.\d{2})'
    )

    # Unit number patterns in descriptions
    UNIT_PATTERNS = [
        re.compile(r'(?:unit|apt|apartment|flat)\s*#?\s*(\d{3,4}[A-Za-z]?)', re.IGNORECASE),
        re.compile(r'(?:UNIT|U)\s*[-:]?\s*(\d{3,4}[A-Za-z]?)', re.IGNORECASE),
        re.compile(r'\b(\d{3,4})\s*[-/]?\s*(?:century|BB|business\s*bay)', re.IGNORECASE),
        # Standalone 3-4 digit number that could be a unit (lower confidence)
        re.compile(r'\b([2-9]\d{2}|1[0-8]\d{2})\b'),
    ]

    def __init__(self):
        self.transactions: list[Transaction] = []
        self.statement_period = ""
        self.account_name = ""
        self.opening_balance = 0.0
        self.closing_balance = 0.0
        self.raw_text = ""

    def parse(self, file_path: str) -> dict:
        """Auto-detect file format and parse accordingly."""
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".pdf":
            return self.parse_pdf(file_path)
        elif ext == ".xls":
            return self.parse_xls(file_path)
        elif ext == ".xlsx":
            return self.parse_excel(file_path)
        elif ext == ".csv":
            return self.parse_csv(file_path)
        else:
            return {"error": f"Unsupported file type: {ext}. Use PDF, XLSX, XLS, or CSV."}

    def parse_xls(self, file_path: str) -> dict:
        """Parse old .xls format using xlrd (Emirates NBD escrow statements)."""
        if not HAS_XLRD:
            return {"error": "xlrd not installed -- cannot read .xls files"}

        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            wb = xlrd.open_workbook(str(path))
            ws = wb.sheet_by_index(0)

            # Extract header info from top rows
            for r in range(min(10, ws.nrows)):
                row_text = " ".join(str(ws.cell_value(r, c)) for c in range(ws.ncols))
                if "Account Name" in row_text:
                    m = re.search(r'Account Name\s*:\s*(.+?)(?:\s{2,}|$)', row_text)
                    if m:
                        self.account_name = m.group(1).strip()
                if "From:" in row_text:
                    m = re.search(r'From:\s*(\S+)\s+to\s+(\S+)', row_text)
                    if m:
                        self.statement_period = f"{m.group(1)} to {m.group(2)}"

            # Find the header row with column names
            header_row = -1
            col_map = {}
            for r in range(min(20, ws.nrows)):
                cells = [str(ws.cell_value(r, c)).strip().lower() for c in range(ws.ncols)]
                # Look for the ENBD header pattern
                if any("transaction date" in c or c == "narration" for c in cells):
                    header_row = r
                    for ci, cell in enumerate(cells):
                        if "s no" in cell or cell == "s no":
                            col_map["sno"] = ci
                        elif "transaction date" in cell:
                            col_map["date"] = ci
                        elif "value date" in cell:
                            col_map["value_date"] = ci
                        elif "narration" in cell or "description" in cell:
                            col_map["narration"] = ci
                        elif "transaction reference" in cell or "reference" in cell:
                            col_map["reference"] = ci
                        elif cell == "debit":
                            col_map["debit"] = ci
                        elif cell == "credit":
                            col_map["credit"] = ci
                        elif "running balance" in cell or "balance" in cell:
                            col_map["balance"] = ci
                    break

            if header_row < 0:
                return {"error": "Could not find header row in .xls file"}

            # Parse data rows
            self.transactions = []
            for r in range(header_row + 1, ws.nrows):
                # Skip empty rows
                narr_val = ws.cell_value(r, col_map.get("narration", 3))
                if not narr_val:
                    continue

                tx = Transaction()

                # Date
                date_val = ws.cell_value(r, col_map.get("date", 1))
                if isinstance(date_val, float):
                    # xlrd date serial
                    try:
                        dt = xlrd.xldate_as_datetime(date_val, wb.datemode)
                        tx.date = dt.strftime("%d-%m-%Y")
                    except Exception:
                        tx.date = str(date_val)
                else:
                    tx.date = str(date_val).strip()

                if not tx.date or tx.date in ("", "0.0"):
                    continue

                # Value date
                vd = ws.cell_value(r, col_map.get("value_date", 2))
                if isinstance(vd, float):
                    try:
                        tx.value_date = xlrd.xldate_as_datetime(vd, wb.datemode).strftime("%d-%m-%Y")
                    except Exception:
                        tx.value_date = str(vd)
                else:
                    tx.value_date = str(vd).strip()

                # Narration / description
                tx.description = str(narr_val).strip()

                # Reference
                ref_val = ws.cell_value(r, col_map.get("reference", 4))
                tx.reference = str(ref_val).strip() if ref_val else ""

                # Amounts -- handle ENBD's "   -   " for empty cells
                def safe_float(val):
                    if not val:
                        return 0.0
                    if isinstance(val, (int, float)):
                        return float(val)
                    s = str(val).strip().replace(",", "")
                    if not s or s == "-" or s.strip("-").strip() == "":
                        return 0.0
                    try:
                        return float(s)
                    except ValueError:
                        return 0.0

                debit_val = ws.cell_value(r, col_map.get("debit", 5))
                credit_val = ws.cell_value(r, col_map.get("credit", 6))
                balance_val = ws.cell_value(r, col_map.get("balance", 7))

                tx.debit = safe_float(debit_val)
                tx.credit = safe_float(credit_val)
                tx.balance = safe_float(balance_val)

                if tx.credit > 0:
                    tx.tx_type = "credit"
                elif tx.debit > 0:
                    tx.tx_type = "debit"
                else:
                    continue

                # Extract unit and name from narration
                unit, unit_conf = self.extract_unit_from_description(tx.description)
                if unit:
                    tx.matched_unit = unit
                    tx.match_confidence = unit_conf

                self.transactions.append(tx)

            return self._build_result(path.name, 1)

        except Exception as e:
            return {"error": f"XLS parsing failed: {str(e)}"}

    def parse_excel(self, file_path: str) -> dict:
        """Parse a bank statement from an Excel file."""
        if not HAS_OPENPYXL:
            return {"error": "openpyxl not installed -- cannot read Excel files"}

        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            wb = openpyxl.load_workbook(str(path), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))

            if not rows:
                return {"error": "Excel file is empty"}

            # Find header row (look for columns like date, description, credit, debit, amount, balance)
            header_idx, col_map = self._detect_excel_columns(rows)

            if col_map is None:
                return {"error": "Could not detect column layout. Expected columns like Date, Description, Credit, Debit, Amount, Balance."}

            self.transactions = []
            for row in rows[header_idx + 1:]:
                if not row or all(c is None for c in row):
                    continue

                tx = self._parse_excel_row(row, col_map)
                if tx and (tx.credit > 0 or tx.debit > 0):
                    tx.tx_type = "credit" if tx.credit > 0 else "debit"
                    self.transactions.append(tx)

            return self._build_result(path.name, 1)

        except Exception as e:
            return {"error": f"Excel parsing failed: {str(e)}"}

    def parse_csv(self, file_path: str) -> dict:
        """Parse a bank statement from a CSV file."""
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            reader = csv.reader(io.StringIO(text))
            rows = [tuple(r) for r in reader]

            if not rows:
                return {"error": "CSV file is empty"}

            header_idx, col_map = self._detect_excel_columns(rows)

            if col_map is None:
                return {"error": "Could not detect column layout in CSV."}

            self.transactions = []
            for row in rows[header_idx + 1:]:
                if not row or all(not c for c in row):
                    continue
                tx = self._parse_excel_row(row, col_map)
                if tx and (tx.credit > 0 or tx.debit > 0):
                    tx.tx_type = "credit" if tx.credit > 0 else "debit"
                    self.transactions.append(tx)

            return self._build_result(path.name, 1)

        except Exception as e:
            return {"error": f"CSV parsing failed: {str(e)}"}

    def _detect_excel_columns(self, rows: list) -> tuple[int, dict | None]:
        """Scan rows to find the header and map column indices."""
        keywords = {
            "date": ["date", "txn date", "transaction date", "value date", "posting date"],
            "description": ["description", "details", "narration", "particulars", "remarks", "reference"],
            "credit": ["credit", "deposit", "credit amount", "credits"],
            "debit": ["debit", "withdrawal", "debit amount", "debits"],
            "amount": ["amount", "sum", "value"],
            "balance": ["balance", "running balance", "closing balance", "available balance"],
            "reference": ["ref", "reference", "ref no", "reference no", "reference no.", "cheque no", "chq no", "transaction reference"],
        }

        for row_idx, row in enumerate(rows[:20]):  # Scan first 20 rows
            if not row:
                continue
            cells = [str(c).strip().lower() if c else "" for c in row]
            col_map = {}

            for col_idx, cell in enumerate(cells):
                if not cell:
                    continue
                for field, aliases in keywords.items():
                    matched = False
                    for alias in aliases:
                        if alias == cell:
                            matched = True
                            break
                    # Contains fallback — but only if cell starts with the alias
                    # (prevents "value date" matching the "date" field)
                    if not matched:
                        for alias in aliases:
                            if len(alias) > 2 and cell.startswith(alias):
                                matched = True
                                break
                    if matched and field not in col_map:
                        col_map[field] = col_idx

            # Need at least date + (credit or amount) to be a valid header
            if "date" in col_map and ("credit" in col_map or "amount" in col_map):
                return (row_idx, col_map)

        return (-1, None)

    def _parse_excel_row(self, row: tuple, col_map: dict) -> Transaction | None:
        """Convert an Excel/CSV row to a Transaction using the column map."""
        tx = Transaction()

        def cell(key):
            idx = col_map.get(key)
            if idx is not None and idx < len(row):
                val = row[idx]
                return str(val).strip() if val is not None else ""
            return ""

        def amount(key):
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return 0.0
            raw = row[idx]
            if raw is None or str(raw).strip() == "":
                return 0.0
            try:
                return abs(float(str(raw).replace(",", "").replace("(", "-").replace(")", "")))
            except (ValueError, TypeError):
                return 0.0

        # Date
        date_val = cell("date")
        if not date_val or date_val.lower() in ("", "nan", "none", "total", "totals"):
            return None
        # Handle datetime objects from Excel
        idx = col_map.get("date")
        if idx is not None and idx < len(row):
            raw = row[idx]
            if isinstance(raw, datetime):
                date_val = raw.strftime("%d/%m/%Y")
        tx.date = date_val

        # Description
        tx.description = cell("description")
        tx.reference = cell("reference")

        # Amounts
        if "credit" in col_map and "debit" in col_map:
            tx.credit = amount("credit")
            tx.debit = amount("debit")
        elif "amount" in col_map:
            # Single amount column -- need to figure out direction from description or sign
            amt_str = cell("amount")
            amt_val = amount("amount")
            if amt_str.startswith("-") or amt_str.startswith("("):
                tx.debit = amt_val
            else:
                tx.credit = amt_val

        tx.balance = amount("balance")

        return tx

    def _build_result(self, filename: str, pages: int) -> dict:
        """Build the standard result dict from self.transactions."""
        credits = [t for t in self.transactions if t.tx_type == "credit"]
        debits = [t for t in self.transactions if t.tx_type == "debit"]

        return {
            "file": filename,
            "pages": pages,
            "statement_period": self.statement_period,
            "account_name": self.account_name,
            "opening_balance": self.opening_balance,
            "closing_balance": self.closing_balance,
            "total_transactions": len(self.transactions),
            "total_credits": len(credits),
            "total_debits": len(debits),
            "total_credit_amount": round(sum(t.credit for t in credits), 2),
            "total_debit_amount": round(sum(t.debit for t in debits), 2),
            "transactions": [t.to_dict() for t in self.transactions],
            "credits": [t.to_dict() for t in credits],
        }

    def parse_pdf(self, pdf_path: str) -> dict:
        """Parse a bank statement PDF and extract all transactions."""
        if not PdfReader:
            return {"error": "PyPDF2 not installed"}

        path = Path(pdf_path)
        if not path.exists():
            return {"error": f"File not found: {pdf_path}"}

        try:
            reader = PdfReader(str(path))
            all_text = ""
            page_texts = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                page_texts.append(text)
                all_text += text + "\n\n"

            self.raw_text = all_text

            # Extract header info
            self._parse_header(all_text)

            # Extract transactions
            self._parse_transactions(all_text)

            # Classify each transaction
            for tx in self.transactions:
                if tx.credit > 0:
                    tx.tx_type = "credit"
                elif tx.debit > 0:
                    tx.tx_type = "debit"

            return self._build_result(path.name, len(reader.pages))

        except Exception as e:
            return {"error": f"PDF parsing failed: {str(e)}"}

    def _parse_header(self, text: str):
        """Extract statement metadata from header."""
        # Statement period
        period_match = re.search(
            r'(?:statement\s+period|period|from)\s*:?\s*'
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s*(?:to|-)\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            text, re.IGNORECASE
        )
        if period_match:
            self.statement_period = f"{period_match.group(1)} to {period_match.group(2)}"

        # Account name
        name_match = re.search(
            r'(?:account\s+name|account\s+holder|name)\s*:?\s*(.+?)(?:\n|account)',
            text, re.IGNORECASE
        )
        if name_match:
            self.account_name = name_match.group(1).strip()

        # Opening/closing balance
        opening_match = re.search(
            r'(?:opening|brought\s+forward)\s*(?:balance)?\s*:?\s*([\d,]+\.\d{2})',
            text, re.IGNORECASE
        )
        if opening_match:
            self.opening_balance = self._parse_amount(opening_match.group(1))

        closing_match = re.search(
            r'(?:closing|carried\s+forward)\s*(?:balance)?\s*:?\s*([\d,]+\.\d{2})',
            text, re.IGNORECASE
        )
        if closing_match:
            self.closing_balance = self._parse_amount(closing_match.group(1))

    def _parse_transactions(self, text: str):
        """Extract individual transactions from the statement text."""
        lines = text.split('\n')
        self.transactions = []
        current_tx = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip header/footer lines
            if any(skip in line.lower() for skip in [
                'page', 'statement', 'account number', 'branch',
                'iban', 'currency', 'opening balance', 'closing balance',
                'total', 'emirates nbd', 'date', 'description',
                'brought forward', 'carried forward',
            ]):
                # But check if this line also has a transaction pattern
                dates = self.DATE_PATTERN.findall(line)
                amounts = self.AMOUNT_PATTERN.findall(line)
                if not (dates and amounts):
                    continue

            # Try to detect a new transaction line (starts with a date)
            dates = self.DATE_PATTERN.findall(line)
            amounts = self.AMOUNT_PATTERN.findall(line)

            if dates and amounts:
                # Save previous transaction
                if current_tx and (current_tx.credit > 0 or current_tx.debit > 0):
                    self.transactions.append(current_tx)

                current_tx = Transaction()
                current_tx.date = dates[0]
                if len(dates) > 1:
                    current_tx.value_date = dates[1]

                # Parse amounts -- typically: debit, credit, balance (or some subset)
                parsed_amounts = [self._parse_amount(a) for a in amounts]

                # Remove any amounts that look like dates parsed as amounts
                parsed_amounts = [a for a in parsed_amounts if a > 0.009]

                if len(parsed_amounts) >= 3:
                    # Likely: debit, credit, balance OR credit, balance
                    # Heuristic: the last amount is usually the balance (largest)
                    current_tx.balance = parsed_amounts[-1]
                    # Check which of the remaining are debit/credit
                    remaining = parsed_amounts[:-1]
                    for amt in remaining:
                        # We'll refine this with description context
                        if amt > 0:
                            # Temporarily store; we'll classify later
                            if not current_tx.credit:
                                current_tx.credit = amt
                            else:
                                current_tx.debit = current_tx.credit
                                current_tx.credit = amt
                elif len(parsed_amounts) == 2:
                    # Could be: amount + balance
                    current_tx.credit = parsed_amounts[0]  # Default to credit
                    current_tx.balance = parsed_amounts[1]
                elif len(parsed_amounts) == 1:
                    current_tx.credit = parsed_amounts[0]

                # Extract description (text between date and first amount)
                desc_text = line
                for d in dates:
                    desc_text = desc_text.replace(d, '', 1)
                for a in amounts:
                    desc_text = desc_text.replace(a, '', 1)
                current_tx.description = desc_text.strip().strip('-').strip()

                # Extract reference number
                ref_match = re.search(r'(?:ref|reference|txn)\s*:?\s*(\w+)', line, re.IGNORECASE)
                if ref_match:
                    current_tx.reference = ref_match.group(1)

            elif current_tx:
                # Continuation line -- append to description
                if line and not self.AMOUNT_PATTERN.search(line):
                    current_tx.description += " " + line

        # Don't forget the last transaction
        if current_tx and (current_tx.credit > 0 or current_tx.debit > 0):
            self.transactions.append(current_tx)

    def _parse_amount(self, amount_str: str) -> float:
        """Parse an amount string like '1,234,567.89' to float."""
        try:
            return float(amount_str.replace(',', ''))
        except (ValueError, AttributeError):
            return 0.0

    # ===================================================================
    # UNIT EXTRACTION PATTERNS (ordered by confidence)
    # ===================================================================
    ENBD_UNIT_PATTERNS = [
        # Explicit: "UNIT 1505", "UNIT NO 1506", "UNIT NO. 802", "UNIT-304"
        (re.compile(r'UNIT[- ]*(?:NO\.?\s*)?(\d{3,4})\b', re.IGNORECASE), 0.98),
        # "AMBS-1702" (corporate account clearing pattern)
        (re.compile(r'AMBS[- ](\d{3,4})\b', re.IGNORECASE), 0.90),
        # "APT 305", "APARTMENT 1202"
        (re.compile(r'(?:APT|APARTMENT)\s*(\d{3,4})\b', re.IGNORECASE), 0.95),
        # "CENTURYUNIT NO 802" (no space)
        (re.compile(r'CENTURY\s*UNIT\s*(?:NO\.?\s*)?(\d{3,4})\b', re.IGNORECASE), 0.98),
        # "UNI/T 708" (ENBD line-break artifacts)
        (re.compile(r'UNI/?T\s*(\d{3,4})\b', re.IGNORECASE), 0.95),
        # "CLEARING CHEQUESUNIT 1505"
        (re.compile(r'CHEQUES?\s*UNIT\s*(\d{3,4})\b', re.IGNORECASE), 0.98),
        # "/REF/UNIT NO 1506"
        (re.compile(r'/REF/.*?UNIT\s*(?:NO\.?\s*)?(\d{3,4})\b', re.IGNORECASE), 0.97),
        # "BOOKING AMOUNT CENTURY UNIT 1705"
        (re.compile(r'(?:BOOKING|PAYMENT).*?CENTURY\s*UNIT\s*(\d{3,4})\b', re.IGNORECASE), 0.97),
        # ENBD typo: "CENTURY NIT 1507", "CENTRURY U 507"
        (re.compile(r'CENTUR\w*\s*(?:NIT|U)\s*(\d{3,4})\b', re.IGNORECASE), 0.90),
        # "CENTURY 802" or "CENTURY 606D" (unit after project name, optional letter suffix)
        (re.compile(r'CENTURY\s*(\d{3,4})[A-Z]?\b', re.IGNORECASE), 0.85),
        # "GDS CENTURY" patterns: "GDS BO O UNIT 802", "GDS CENT URY 1003"
        (re.compile(r'GDS\s+.*?(?:CENTURY|CENT\s*URY).*?(\d{3,4})\b', re.IGNORECASE), 0.80),
        # "DLD.*CENTURY.*<number>" or "DLD APT 1102 CENTURY"
        (re.compile(r'DLD\s+.*?(?:APT|UNIT)?\s*(\d{3,4}).*?CENTURY', re.IGNORECASE), 0.85),
        (re.compile(r'DLD\s+.*?CENTURY\s*(\d{3,4})\b', re.IGNORECASE), 0.85),
        # "CENTURY<no space><number>" e.g. "CENTURY1010"
        (re.compile(r'CENTURY(\d{3,4})\b', re.IGNORECASE), 0.85),
        # "CENTURY-1207" (with dash, seen in cheque clearing narrations)
        (re.compile(r'CENTURY[- ](\d{3,4})\b', re.IGNORECASE), 0.90),
        # "DEFAULT" clearing pattern: "CENTURY-1207 DEFAULT"
        (re.compile(r'CENTURY[- ]?(\d{3,4})\s+DEFAULT', re.IGNORECASE), 0.95),
    ]

    # IBAN extraction
    IBAN_PATTERN = re.compile(r'(AE\d{21,23})', re.IGNORECASE)
    # Alternative: "FROM AE..." in BANKNET
    BANKNET_ACCT_PATTERN = re.compile(r'FROM\s+(AE\d+)', re.IGNORECASE)

    def extract_unit_from_description(self, description: str) -> tuple[str, float]:
        """Extract unit number from an ENBD bank statement narration."""
        if not description:
            return ("", 0.0)

        cleaned = re.sub(r'\s+', ' ', description)

        for pattern, base_confidence in self.ENBD_UNIT_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                unit = match.group(1)
                try:
                    unit_num = int(unit)
                    # Valid unit range: 100-1999 (covers all projects)
                    if 100 <= unit_num <= 1999:
                        return (unit, base_confidence)
                except ValueError:
                    pass

        return ("", 0.0)

    # Words that are NOT names (noise in ENBD narrations)
    NOISE_WORDS = {
        "TRANSFER", "PAYMENT", "CREDIT", "DEBIT", "BANK", "ACCOUNT", "AMOUNT",
        "CHEQUE", "CLEARING", "INWARD", "OUTWARD", "REMITTANCE", "SALARY",
        "BOOKING", "ADVANCE", "REFUND", "RETURN", "CHARGE", "FEE", "FEES",
        "COMMISSION", "SERVICE", "TAX", "VAT", "DLD", "RERA", "OQOOD",
        "ESCROW", "CENTURY", "BUSINESS", "BAY", "DUBAI", "ABU", "DHABI",
        "BRANCH", "EMIRATES", "NBD", "ENBD", "INTERNATIONAL", "LOCAL",
        "BANKNET", "SWIFT", "RTGS", "NEFT", "IMPS", "FROM", "TOWARDS",
        "AGAINST", "FAVOUR", "BEHALF", "PURPOSE", "REFERENCE", "DEPOSIT",
        "FUND", "RECEIPT", "INSTALLMENT", "DOWN", "UNIT", "FLAT", "APT",
        "PVT", "LTD", "LLC", "INC", "CORP", "FZE", "FZC", "FZCO",
        "THE", "AND", "FOR", "WITH", "PER", "VIA",
        # Address/location noise (appears after names in INWARD REMITTANCE)
        "CIT", "CITY", "BUILDING", "BLDG", "TOWER", "ROAD", "STREET", "ST",
        "FLOOR", "SUITE", "OFFICE", "BLOCK", "PLOT", "SECTOR", "AREA",
        "WALK", "YWALK", "MALL", "CENTER", "CENTRE", "GATE", "GARDENS",
        "RESIDENCE", "RESIDENCES", "VILLAGE", "SQUARE", "PLAZA", "HEIGHTS",
        # Transaction noise
        "GOODS", "SERVICES", "BOUGH", "BOUGHT", "PURCHASED", "SOLD",
        "REF", "REFNO", "REMITTANCETT", "SDM", "CDC", "MOBILE", "BANKING",
        "ENCASHMENT", "CHEQUES", "DEFAULT", "SID",
    }

    def extract_name_from_description(self, description: str) -> str:
        """Extract payer/client name from ENBD narration. Enhanced with multiple fallbacks."""
        if not description:
            return ""
        cleaned = re.sub(r'\s+', ' ', description.upper())

        # Pattern 1: "AED <amount> <NAME> <terminator>"
        m = re.search(
            r'AED\s+[\d,.]+\s+(?:MR\.?\s+|MRS\.?\s+|MS\.?\s+|MISS\s+)?'
            r'([A-Z][A-Z\s]{3,60}?)'
            r'(?:\s+PO\s+BOX|\s+BR\s|\s+\d{2,}|\s*/|\s+REFNO|\s+BOOKING|\s+DOWN|\s+ADVANCE)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3:
            return self._clean_name(m.group(1).strip())

        # Pattern 2: "MR/MRS/MS <NAME>"
        m = re.search(
            r'(?:MR\.?\s+|MRS\.?\s+|MS\.?\s+|MISS\s+)([A-Z][A-Z\s]{3,50}?)(?:\s+PO|\s+BR|\s+\d|\s*/|$)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3:
            return self._clean_name(m.group(1).strip())

        # Pattern 3: BANKNET -- name after "FROM AE... <digits> <NAME>"
        m = re.search(
            r'FROM\s+AE\d+\s+\d+\s+(.+?)(?:\s+REFNO|\s+REF|\s*$)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3 and not m.group(1).strip().startswith("BOOKING"):
            return self._clean_name(m.group(1).strip())

        # Pattern 4: After "USD <amount>@<rate> <NAME>"
        m = re.search(
            r'USD\s+[\d,.]+@[\d.]+\s+([A-Z][A-Z\s]{3,50}?)(?:\s+/|\s+BNY|\s+BOOKING)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3:
            return self._clean_name(m.group(1).strip())

        # Pattern 5: "TRANSFER FROM <NAME>" or "CREDIT FROM <NAME>"
        m = re.search(
            r'(?:TRANSFER|CREDIT|TRF|XFER|REMIT)\s+(?:FROM|FR|BY)\s+([A-Z][A-Z\s]{3,50}?)(?:\s+TO|\s+ACC|\s+A/C|\s+REF|\s+\d{5,}|\s*/|$)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3:
            return self._clean_name(m.group(1).strip())

        # Pattern 6: "BY ORDER OF <NAME>" or "ORDERED BY <NAME>"
        m = re.search(
            r'(?:BY\s+ORDER\s+OF|ORDERED\s+BY|ORIG\s+|ORIGINATOR\s*:?\s*)([A-Z][A-Z\s]{3,50}?)(?:\s+REF|\s+ACC|\s+\d{5,}|\s*/|$)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3:
            return self._clean_name(m.group(1).strip())

        # Pattern 7: "FAVOUR OF <NAME>" or "FAV <NAME>" or "BENEF <NAME>"
        m = re.search(
            r'(?:FAVOUR\s+OF|FAV\s+|BENEF(?:ICIARY)?\s*:?\s*)([A-Z][A-Z\s]{3,50}?)(?:\s+ACC|\s+REF|\s+\d{5,}|\s*/|$)',
            cleaned
        )
        if m and len(m.group(1).strip()) > 3:
            return self._clean_name(m.group(1).strip())

        # Pattern 8: Fallback — find longest sequence of 2+ capitalized name-like words
        # that aren't noise words
        best = self._extract_name_fallback(cleaned)
        if best and len(best) > 5:
            return best

        return ""

    def _clean_name(self, name: str) -> str:
        """Remove noise words from an extracted name. Truncate at first noise/address word."""
        parts = name.upper().split()
        clean = []
        for p in parts:
            # Stop at first noise word (address, reference, etc.)
            if p in self.NOISE_WORDS:
                break
            # Stop at numbers (account numbers, refs)
            if any(c.isdigit() for c in p) and len(p) > 3:
                break
            # Stop at slash-prefixed tokens (/REF/, /GOODS/)
            if p.startswith("/"):
                break
            if len(p) > 1:
                clean.append(p)
        result = " ".join(clean).strip()
        # Must have at least 2 name parts to be valid
        if len(clean) < 2:
            # Try without truncation — just remove noise words
            clean2 = [p for p in parts if p not in self.NOISE_WORDS and len(p) > 1 and not any(c.isdigit() for c in p)]
            if len(clean2) >= 2:
                result = " ".join(clean2[:4]).strip()  # Take first 4 clean words max
        return result

    def _extract_name_fallback(self, text: str) -> str:
        """Fallback: find the longest consecutive name-like word sequence."""
        words = text.split()
        best_name = ""
        current = []

        for w in words:
            # Name-like: alphabetic, not a noise word, not all digits, at least 2 chars
            w_clean = re.sub(r'[^A-Z]', '', w)
            if (
                len(w_clean) >= 2
                and w_clean.isalpha()
                and w_clean not in self.NOISE_WORDS
                and not any(c.isdigit() for c in w)
            ):
                current.append(w_clean)
            else:
                if len(current) >= 2:
                    candidate = " ".join(current)
                    if len(candidate) > len(best_name):
                        best_name = candidate
                current = []

        # Check last sequence
        if len(current) >= 2:
            candidate = " ".join(current)
            if len(candidate) > len(best_name):
                best_name = candidate

        return best_name

    def extract_iban_from_description(self, description: str) -> str:
        """Extract IBAN/account number from narration."""
        if not description:
            return ""
        cleaned = re.sub(r'\s+', ' ', description)
        m = self.BANKNET_ACCT_PATTERN.search(cleaned)
        if m:
            return m.group(1)
        m = self.IBAN_PATTERN.search(cleaned)
        if m:
            return m.group(1)
        return ""

    def run_multi_pass_matching(self):
        """
        Multi-pass intelligent matching:
        Pass 1: Unit number from narration (already done during parsing)
        Pass 2: Build knowledge base from matched transactions
        Pass 3: Match remaining by IBAN/account (same account = same unit)
        Pass 4: Match remaining by name (same payer = same unit)
        Pass 5: Fuzzy name matching
        """
        credits = self.get_credits_only()

        # --- Pass 1 already done during parsing ---

        # --- Build knowledge base from Pass 1 results ---
        kb_name_to_unit: dict[str, str] = {}   # normalized_name -> unit
        kb_iban_to_unit: dict[str, str] = {}    # iban -> unit
        kb_name_to_iban: dict[str, str] = {}    # for chaining

        for tx in credits:
            if not tx.matched_unit:
                continue
            # Learn name -> unit
            name = self.extract_name_from_description(tx.description)
            if name and len(name) > 3:
                key = self._normalize_name(name)
                kb_name_to_unit[key] = tx.matched_unit
            # Learn IBAN -> unit
            iban = self.extract_iban_from_description(tx.description)
            if iban:
                kb_iban_to_unit[iban] = tx.matched_unit
                if name:
                    kb_name_to_iban[self._normalize_name(name)] = iban

        # --- Pass 2: Match by IBAN ---
        for tx in credits:
            if tx.matched_unit:
                continue
            iban = self.extract_iban_from_description(tx.description)
            if iban and iban in kb_iban_to_unit:
                tx.matched_unit = kb_iban_to_unit[iban]
                tx.match_confidence = 0.90
                tx.match_method = "iban_match"
                tx.match_status = "matched"
                # Also learn this name
                name = self.extract_name_from_description(tx.description)
                if name:
                    kb_name_to_unit[self._normalize_name(name)] = tx.matched_unit

        # --- Pass 3: Match by exact name ---
        for tx in credits:
            if tx.matched_unit:
                continue
            name = self.extract_name_from_description(tx.description)
            if not name:
                continue
            key = self._normalize_name(name)
            if key in kb_name_to_unit:
                tx.matched_unit = kb_name_to_unit[key]
                tx.match_confidence = 0.85
                tx.match_method = "name_exact"
                tx.match_status = "matched"

        # --- Pass 4: Fuzzy name matching ---
        for tx in credits:
            if tx.matched_unit:
                continue
            name = self.extract_name_from_description(tx.description)
            if not name or len(name) < 5:
                continue
            parts = self._normalize_name(name).split()
            if len(parts) < 2:
                continue

            best_unit = None
            best_score = 0
            for kb_name, kb_unit in kb_name_to_unit.items():
                kb_parts = kb_name.split()
                # Count how many name parts match
                matches = sum(1 for p in parts if any(p in kp or kp in p for kp in kb_parts if len(kp) > 2) and len(p) > 2)
                score = matches / max(len(parts), len(kb_parts))
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_unit = kb_unit

            if best_unit:
                tx.matched_unit = best_unit
                tx.match_confidence = round(min(0.80, best_score * 0.85), 2)
                tx.match_method = "name_fuzzy"
                tx.match_status = "review" if best_score < 0.7 else "matched"

        # --- Pass 5: Populate matched_client for all ---
        for tx in credits:
            name = self.extract_name_from_description(tx.description)
            if name:
                tx.matched_client = name

        return self.get_credits_only()

    def load_cross_reference(self, other_parser: 'BankStatementParser'):
        """
        Cross-reference another bank statement (e.g., Escrow) to improve matching.
        Names matched to units in the other statement expand our knowledge base.
        """
        for tx in other_parser.get_credits_only():
            if not tx.matched_unit:
                continue
            name = other_parser.extract_name_from_description(tx.description)
            if name and len(name) > 3:
                # Find unmatched credits in THIS statement with the same name
                key = self._normalize_name(name)
                for my_tx in self.get_credits_only():
                    if my_tx.matched_unit:
                        continue
                    my_name = self.extract_name_from_description(my_tx.description)
                    if my_name and self._normalize_name(my_name) == key:
                        my_tx.matched_unit = tx.matched_unit
                        my_tx.match_confidence = 0.82
                        my_tx.match_method = "cross_reference"
                        my_tx.match_status = "matched"

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a name for matching: uppercase, remove artifacts, collapse spaces."""
        n = name.upper().strip()
        # Remove ENBD line-break artifacts (single-char fragments)
        n = re.sub(r'\b([A-Z])\s+(?=[A-Z]{2,})', r'\1', n)
        n = re.sub(r'\s+', ' ', n)
        return n

    def get_credits_only(self) -> list[Transaction]:
        """Return only credit (incoming payment) transactions."""
        return [t for t in self.transactions if t.tx_type == "credit"]
