from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime, timedelta
import os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Styling ──
hdr_font = Font(name="Arial", bold=True, size=10, color="FFFFFF")
hdr_fill = PatternFill("solid", fgColor="2F5496")
data_font = Font(name="Arial", size=10)
green_fill = PatternFill("solid", fgColor="C6EFCE")
thin_border = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)
num_fmt = '#,##0.00'
date_fmt = 'DD/MM/YYYY'

def style_header(ws, cols):
    for c in range(1, cols + 1):
        cell = ws.cell(1, c)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center", wrap_text=True)
        cell.border = thin_border

def style_row(ws, row, cols, fill=None):
    for c in range(1, cols + 1):
        cell = ws.cell(row, c)
        cell.font = data_font
        cell.border = thin_border
        if fill:
            cell.fill = fill

# ════════════════════════════════════════════════════════════════
# FILE 1: CBC_Master_Sheet.xlsx
# ════════════════════════════════════════════════════════════════
wb = Workbook()

# ── Sheet 1: Escrow Account ──
ws1 = wb.active
ws1.title = "Updated Sheet_Escrow Account"
headers_escrow = ["Date", "Value Date", "Narration", "Reference", "Debit", "Credit",
                  "Running Balance", "Unit No. / Remarks", "Account Name", "Receipt", "Status"]
for c, h in enumerate(headers_escrow, 1):
    ws1.cell(1, c, h)
style_header(ws1, 11)

# Column widths
ws1.column_dimensions['A'].width = 12
ws1.column_dimensions['B'].width = 12
ws1.column_dimensions['C'].width = 50
ws1.column_dimensions['D'].width = 20
ws1.column_dimensions['E'].width = 14
ws1.column_dimensions['F'].width = 14
ws1.column_dimensions['G'].width = 16
ws1.column_dimensions['H'].width = 16
ws1.column_dimensions['I'].width = 30
ws1.column_dimensions['J'].width = 10
ws1.column_dimensions['K'].width = 10

# Pre-existing transactions (already reconciled)
existing = [
    # (date, value_date, narration, reference, debit, credit, unit, name, receipt, status)
    (datetime(2026,1,5), datetime(2026,1,5), "OUTWARD CLEARINGUNIT 101 DEFAULT - ~026ABC123", "TXN-001", 0, 450000, "101", "Ahmed Hassan Al Maktoum", "Done", "NEW"),
    (datetime(2026,1,8), datetime(2026,1,8), "INWARD REMITTANCETT REF: 530P4F86D98E100 AED 380000 FATIMA ABDULRAHMAN SAEED PO BOX 5432 DUBAI", "TXN-002", 0, 380000, "102", "Fatima Abdulrahman Saeed", "Done", "NEW"),
    (datetime(2026,1,12), datetime(2026,1,12), "OUTWARD CLEARINGUNIT 203 DEFAULT - ~026DEF456", "TXN-003", 0, 520000, "203", "Mohamed Khalid Al Rashidi", "Done", "NEW"),
    (datetime(2026,1,15), datetime(2026,1,15), "INWARD REMITTANCETT REF: 044ABLC7890123 AED 490000 SARAH JOHNSON 45 PARK LANE LONDON", "TXN-004", 0, 490000, "204", "Sarah Johnson", "Done", "NEW"),
    (datetime(2026,1,20), datetime(2026,1,20), "OUTWARD CLEARINGUNIT 305 DEFAULT - ~026GHI789", "TXN-005", 0, 410000, "305", "Khalid Omar Al Mansouri", "Done", "NEW"),
    (datetime(2026,1,25), datetime(2026,1,25), "INWARD REMITTANCETT REF: 20260125001234 AED 375000 NADIA HASSAN IBRAHIM", "TXN-006", 0, 375000, "306", "Nadia Hassan Ibrahim", "Done", "NEW"),
    (datetime(2026,2,1), datetime(2026,2,1), "OUTWARD CLEARINGUNIT 407 DEFAULT - ~026JKL012", "TXN-007", 0, 560000, "407", "Rashid Saeed Al Ketbi", "Done", "NEW"),
    (datetime(2026,2,5), datetime(2026,2,5), "INWARD REMITTANCETT REF: 530P5EB4FCD5AA AED 430000 ELENA PETROVA MOSCOW RUSSIA", "TXN-008", 0, 430000, "408", "Elena Petrova", "Done", "NEW"),
    (datetime(2026,2,10), datetime(2026,2,10), "OUTWARD CLEARINGUNIT 509 DEFAULT - ~026MNO345", "TXN-009", 0, 510000, "509", "Ali Mohammed Al Suwaidi", "Done", "NEW"),
    (datetime(2026,2,15), datetime(2026,2,15), "INWARD REMITTANCETT REF: 20260215005678 AED 395000 JAMES ROBERT WILSON FLAT 12 CHICAGO USA", "TXN-010", 0, 395000, "510", "James Robert Wilson", "Done", "NEW"),
    # Q1 installments (already paid for some units)
    (datetime(2026,2,20), datetime(2026,2,20), "INWARD REMITTANCETT REF: 530P4F86D98E201 AED 56250 AHMED HASSAN AL MAKTOUM PO BOX 12345 DUBAI UAE", "TXN-011", 0, 56250, "101", "Ahmed Hassan Al Maktoum", "Done", "NEW"),
    (datetime(2026,2,25), datetime(2026,2,25), "OUTWARD CLEARINGUNIT 102 DEFAULT - ~026PQR678", "TXN-012", 0, 47500, "102", "Fatima Abdulrahman Saeed", "Done", "NEW"),
    (datetime(2026,3,1), datetime(2026,3,1), "IPP Customer CreditIPP 20260301ADC6B981118 AED 61250", "TXN-013", 0, 61250, "204", "Sarah Johnson", "Done", "NEW"),
]

balance = 5000000.00
for i, (dt, vd, narr, ref, deb, cred, unit, name, rcpt, status) in enumerate(existing):
    r = i + 2
    ws1.cell(r, 1, dt).number_format = date_fmt
    ws1.cell(r, 2, vd).number_format = date_fmt
    ws1.cell(r, 3, narr)
    ws1.cell(r, 4, ref)
    ws1.cell(r, 5, deb).number_format = num_fmt
    ws1.cell(r, 6, cred).number_format = num_fmt
    if i == 0:
        ws1.cell(r, 7, 5000000 - deb + cred).number_format = num_fmt
    else:
        ws1.cell(r, 7, f"=G{r-1}-E{r}+F{r}")
    ws1.cell(r, 7).number_format = num_fmt
    ws1.cell(r, 8, unit)
    ws1.cell(r, 9, name)
    ws1.cell(r, 10, rcpt)
    ws1.cell(r, 11, status)
    style_row(ws1, r, 11, green_fill)

# ── Sheet 2: Corporate ──
ws2 = wb.create_sheet("Updated Sheet_Corporate")
headers_corp = ["Date", "Narration", "Reference", "Debit", "Credit", "Running Balance",
                "Unit No. / Remarks", "Account Name"]
for c, h in enumerate(headers_corp, 1):
    ws2.cell(1, c, h)
style_header(ws2, 8)

ws2.column_dimensions['A'].width = 12
ws2.column_dimensions['B'].width = 50
ws2.column_dimensions['C'].width = 20
ws2.column_dimensions['D'].width = 14
ws2.column_dimensions['E'].width = 14
ws2.column_dimensions['F'].width = 16
ws2.column_dimensions['G'].width = 16
ws2.column_dimensions['H'].width = 30

corp_data = [
    (datetime(2026,1,10), "SERVICE CHARGE - CBC COMMON AREAS Q1 2026", "CORP-001", 125000, 0, "CBC Management", ""),
    (datetime(2026,2,1), "DEWA UTILITIES PAYMENT - CBC BUILDING", "CORP-002", 45000, 0, "DEWA", ""),
    (datetime(2026,2,15), "MAINTENANCE FEE - CBC PARKING FACILITIES", "CORP-003", 35000, 0, "CBC Facilities", ""),
]

corp_balance = 2000000.00
for i, (dt, narr, ref, deb, cred, name, unit) in enumerate(corp_data):
    r = i + 2
    ws2.cell(r, 1, dt).number_format = date_fmt
    ws2.cell(r, 2, narr)
    ws2.cell(r, 3, ref)
    ws2.cell(r, 4, deb).number_format = num_fmt
    ws2.cell(r, 5, cred).number_format = num_fmt
    if i == 0:
        ws2.cell(r, 6, corp_balance - deb + cred).number_format = num_fmt
    else:
        ws2.cell(r, 6, f"=F{r-1}-D{r}+E{r}")
    ws2.cell(r, 6).number_format = num_fmt
    ws2.cell(r, 7, unit)
    ws2.cell(r, 8, name)
    style_row(ws2, r, 8)

master_path = os.path.join(OUT_DIR, "CBC_Master_Sheet.xlsx")
wb.save(master_path)
print(f"Created: {master_path}")

# ════════════════════════════════════════════════════════════════
# FILE 2: CBC_Escrow_Statement_Mar2026.xlsx
# ════════════════════════════════════════════════════════════════
wb2 = Workbook()
ws = wb2.active
ws.title = "Statement"

stmt_headers = ["Transaction Date", "Value Date", "Description", "Reference No",
                "Debit", "Credit", "Balance"]
for c, h in enumerate(stmt_headers, 1):
    ws.cell(1, c, h)
style_header(ws, 7)

ws.column_dimensions['A'].width = 14
ws.column_dimensions['B'].width = 14
ws.column_dimensions['C'].width = 70
ws.column_dimensions['D'].width = 25
ws.column_dimensions['E'].width = 14
ws.column_dimensions['F'].width = 14
ws.column_dimensions['G'].width = 16

# 15 NEW transactions — varying difficulty levels
transactions = [
    # 1. Easy: full name + unit amount match → Unit 101 Q2
    (datetime(2026,3,14), datetime(2026,3,14),
     "INWARD REMITTANCETT REF: 530P4F86D98E301 AED 56250 AHMED HASSAN AL MAKTOUM PO BOX 12345 DUBAI UAE",
     "STMT-301", 0, 56250),
    # 2. Easy: unit number in narration → Unit 102
    (datetime(2026,3,15), datetime(2026,3,15),
     "OUTWARD CLEARINGUNIT 102 DEFAULT - ~026STU901",
     "STMT-302", 0, 47500),
    # 3. Medium: surname variant "RASHIDI" vs "AL RASHIDI" → Unit 203
    (datetime(2026,3,16), datetime(2026,3,16),
     "INWARD REMITTANCETT REF: 033DBLC2608235 AED 65000 MOHAMED KHALID RASHIDI CIT YWALK BUILDING DUBAI",
     "STMT-303", 0, 65000),
    # 4. Hard: IPP with no name, only reference → Unit 204
    (datetime(2026,3,17), datetime(2026,3,17),
     "IPP Customer CreditIPP 20260317ADC6B981204",
     "STMT-304", 0, 61250),
    # 5. Medium: abbreviated first name "KH" for KHALID → Unit 305
    (datetime(2026,3,18), datetime(2026,3,18),
     "INWARD REMITTANCETT REF: 20260318004944 AED 51250 KH OMAR AL MANSOURI",
     "STMT-305", 0, 51250),
    # 6. Easy: unit number in narration → Unit 306
    (datetime(2026,3,19), datetime(2026,3,19),
     "OUTWARD CLEARINGUNIT 306 DEFAULT - ~026VWX234",
     "STMT-306", 0, 46875),
    # 7. Medium: "ALKETBI" vs "AL KETBI" (no space) → Unit 407
    (datetime(2026,3,20), datetime(2026,3,20),
     "INWARD REMITTANCETT REF: 530P5EB4FCD5BB AED 70000 RASHID SAEED ALKETBI",
     "STMT-307", 0, 70000),
    # 8. Hard: Russian name variant "PETROVNA" vs "PETROVA" → Unit 408
    (datetime(2026,3,21), datetime(2026,3,21),
     "INWARD REMITTANCETT REF: 044ABLC1234567 AED 53750 ELENA PETROVNA MOSCOW RUSSIA",
     "STMT-308", 0, 53750),
    # 9. Hard: initials "A M" for "ALI MOHAMMED" → Unit 509
    (datetime(2026,3,22), datetime(2026,3,22),
     "INWARD REMITTANCETT REF: 20260322123456 AED 63750 A M AL SUWAIDI",
     "STMT-309", 0, 63750),
    # 10. Easy: unit number in narration → Unit 510
    (datetime(2026,3,22), datetime(2026,3,22),
     "OUTWARD CLEARINGUNIT 510 DEFAULT - ~026YZA567",
     "STMT-310", 0, 49375),
    # 11. Tricky: same person second payment, partial name → Unit 101 Q3
    (datetime(2026,3,23), datetime(2026,3,23),
     "INWARD REMITTANCETT REF: 789ABC123DEF AED 56250 AHMED H MAKTOUM",
     "STMT-311", 0, 56250),
    # 12. Medium: middle name dropped → Unit 102
    (datetime(2026,3,24), datetime(2026,3,24),
     "INWARD REMITTANCETT REF: 456DEF789GHI AED 47500 FATIMA SAEED",
     "STMT-312", 0, 47500),
    # 13. Hard: MOHAMMED vs MOHAMED + initial K for KHALID → Unit 203
    (datetime(2026,3,24), datetime(2026,3,24),
     "BANKNET AE420350000000123456789 12345678 MOHAMMED K AL RASHIDI",
     "STMT-313", 0, 65000),
    # 14. Medium: middle name "HASSAN" dropped → Unit 306
    (datetime(2026,3,25), datetime(2026,3,25),
     "INWARD REMITTANCETT REF: 111222333444 AED 46875 NADIA IBRAHIM",
     "STMT-314", 0, 46875),
    # 15. Hardest: blank narration, amount only → Unit 305 (needs AI)
    (datetime(2026,3,26), datetime(2026,3,26),
     "-",
     "STMT-315", 0, 51250),
]

balance = 8500000.00
for i, (dt, vd, desc, ref, deb, cred) in enumerate(transactions):
    r = i + 2
    ws.cell(r, 1, dt).number_format = date_fmt
    ws.cell(r, 2, vd).number_format = date_fmt
    ws.cell(r, 3, desc)
    ws.cell(r, 4, ref)
    ws.cell(r, 5, deb).number_format = num_fmt
    ws.cell(r, 6, cred).number_format = num_fmt
    balance = balance - deb + cred
    ws.cell(r, 7, balance).number_format = num_fmt
    style_row(ws, r, 7)

stmt_path = os.path.join(OUT_DIR, "CBC_Escrow_Statement_Mar2026.xlsx")
wb2.save(stmt_path)
print(f"Created: {stmt_path}")

print("\n=== Test Data Summary ===")
print(f"Master Sheet: 10 units, 13 pre-existing transactions")
print(f"Bank Statement: 15 new transactions to match")
print(f"\nDifficulty breakdown:")
print(f"  Easy (unit in narration):     4 transactions (#2, #6, #10, + full name #1)")
print(f"  Medium (name variants):       5 transactions (#3, #5, #7, #12, #14)")
print(f"  Hard (initials/variants):     4 transactions (#8, #9, #11, #13)")
print(f"  Very Hard (no name/IPP):      1 transaction (#4)")
print(f"  Impossible (blank narration): 1 transaction (#15)")
