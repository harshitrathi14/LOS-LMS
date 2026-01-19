"""
Generate PowerPoint presentation for the Unified LOS/LMS System.

Version 2.0 - Includes FLDG, ECL, Servicer Income features

Usage:
    pip install python-pptx
    python generate_presentation.py

Output: LOS_LMS_System_Presentation.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


def add_title_slide(prs, title, subtitle):
    """Add a title slide."""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.5), Inches(9), Inches(1.5))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(44)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(0, 51, 102)
    title_para.alignment = PP_ALIGN.CENTER

    # Subtitle
    sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(4), Inches(9), Inches(1.5))
    sub_frame = sub_box.text_frame
    sub_para = sub_frame.paragraphs[0]
    sub_para.text = subtitle
    sub_para.font.size = Pt(22)
    sub_para.font.color.rgb = RGBColor(100, 100, 100)
    sub_para.alignment = PP_ALIGN.CENTER

    return slide


def add_content_slide(prs, title, bullet_points, subtitle=None):
    """Add a content slide with title and bullet points."""
    slide_layout = prs.slide_layouts[6]  # Blank layout
    slide = prs.slides.add_slide(slide_layout)

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(32)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(0, 51, 102)

    # Subtitle if provided
    y_offset = 1.1
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.1), Inches(9), Inches(0.5))
        sub_frame = sub_box.text_frame
        sub_para = sub_frame.paragraphs[0]
        sub_para.text = subtitle
        sub_para.font.size = Pt(18)
        sub_para.font.italic = True
        sub_para.font.color.rgb = RGBColor(100, 100, 100)
        y_offset = 1.6

    # Bullet points
    content_box = slide.shapes.add_textbox(Inches(0.5), Inches(y_offset), Inches(9), Inches(5))
    content_frame = content_box.text_frame
    content_frame.word_wrap = True

    for i, point in enumerate(bullet_points):
        if i == 0:
            para = content_frame.paragraphs[0]
        else:
            para = content_frame.add_paragraph()

        para.text = f"• {point}"
        para.font.size = Pt(18)
        para.space_after = Pt(10)
        para.font.color.rgb = RGBColor(50, 50, 50)

    return slide


def add_table_slide(prs, title, headers, rows, subtitle=None):
    """Add a slide with a table."""
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(32)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(0, 51, 102)

    y_offset = 1.2
    if subtitle:
        sub_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.1), Inches(9), Inches(0.5))
        sub_frame = sub_box.text_frame
        sub_para = sub_frame.paragraphs[0]
        sub_para.text = subtitle
        sub_para.font.size = Pt(18)
        sub_para.font.italic = True
        y_offset = 1.7

    # Table
    num_cols = len(headers)
    num_rows = len(rows) + 1
    col_width = 8.5 / num_cols

    table = slide.shapes.add_table(
        num_rows, num_cols,
        Inches(0.5), Inches(y_offset),
        Inches(8.5), Inches(min(num_rows * 0.45, 4.5))
    ).table

    # Header row
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.size = Pt(12)
        cell.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(0, 51, 102)

    # Data rows
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_data in enumerate(row_data):
            cell = table.cell(row_idx + 1, col_idx)
            cell.text = str(cell_data)
            cell.text_frame.paragraphs[0].font.size = Pt(11)
            if row_idx % 2 == 1:
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(240, 240, 240)

    return slide


def add_two_column_slide(prs, title, left_title, left_points, right_title, right_points):
    """Add a two-column slide."""
    slide_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(slide_layout)

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.8))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.size = Pt(32)
    title_para.font.bold = True
    title_para.font.color.rgb = RGBColor(0, 51, 102)

    # Left column title
    left_title_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(4), Inches(0.5))
    left_title_frame = left_title_box.text_frame
    left_title_para = left_title_frame.paragraphs[0]
    left_title_para.text = left_title
    left_title_para.font.size = Pt(20)
    left_title_para.font.bold = True
    left_title_para.font.color.rgb = RGBColor(0, 102, 153)

    # Left column content
    left_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.7), Inches(4), Inches(4.5))
    left_frame = left_box.text_frame
    left_frame.word_wrap = True
    for i, point in enumerate(left_points):
        if i == 0:
            para = left_frame.paragraphs[0]
        else:
            para = left_frame.add_paragraph()
        para.text = f"• {point}"
        para.font.size = Pt(14)
        para.space_after = Pt(6)

    # Right column title
    right_title_box = slide.shapes.add_textbox(Inches(5), Inches(1.2), Inches(4), Inches(0.5))
    right_title_frame = right_title_box.text_frame
    right_title_para = right_title_frame.paragraphs[0]
    right_title_para.text = right_title
    right_title_para.font.size = Pt(20)
    right_title_para.font.bold = True
    right_title_para.font.color.rgb = RGBColor(0, 102, 153)

    # Right column content
    right_box = slide.shapes.add_textbox(Inches(5), Inches(1.7), Inches(4), Inches(4.5))
    right_frame = right_box.text_frame
    right_frame.word_wrap = True
    for i, point in enumerate(right_points):
        if i == 0:
            para = right_frame.paragraphs[0]
        else:
            para = right_frame.add_paragraph()
        para.text = f"• {point}"
        para.font.size = Pt(14)
        para.space_after = Pt(6)

    return slide


def create_presentation():
    """Create the full presentation."""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Slide 1: Title
    add_title_slide(
        prs,
        "Unified Loan Origination &\nLoan Management System",
        "A Complete Enterprise Lending Platform\n\nRetail • Commercial • Co-Lending • Supply Chain • Securitization\nFLDG • ECL Staging • Servicer Income\n\nVersion 2.0 | January 2026"
    )

    # Slide 2: Executive Summary
    add_table_slide(
        prs,
        "Executive Summary",
        ["Capability", "Status"],
        [
            ["Loan Origination & Management", "✓ Complete"],
            ["Co-Lending (80:20, 90:10, 100:0)", "✓ Complete"],
            ["FLDG (First/Second Loss)", "✓ Complete"],
            ["ECL Staging (IFRS 9)", "✓ Complete"],
            ["Servicer Fees & Income", "✓ Complete"],
            ["Supply Chain Finance", "✓ Complete"],
            ["Securitization (PTC/DA)", "✓ Complete"],
        ],
        subtitle="386 Tests | 65+ Models | 25+ Services | 120 Files | 22,000+ Lines"
    )

    # Slide 3: Technology Stack
    add_content_slide(
        prs,
        "Technology Stack",
        [
            "FastAPI (Python) - High-performance REST API framework",
            "SQLAlchemy 2.0 ORM - Enterprise-grade database abstraction",
            "Pydantic v2 - Type safety and request/response validation",
            "PostgreSQL / SQLite - ACID-compliant database layer",
            "pytest - Comprehensive test framework (386 tests)",
        ],
        subtitle="Modern, Scalable Architecture"
    )

    # Slide 4: System Architecture
    add_content_slide(
        prs,
        "System Architecture",
        [
            "Clients (Mobile / Web / API) → API Layer (FastAPI Routers)",
            "API Layer → Services Layer (Business Logic)",
            "Services Layer → Models Layer (SQLAlchemy ORM)",
            "Models Layer → Database (PostgreSQL)",
            "",
            "Key Modules:",
            "   Core: Borrowers, Products, Applications, Accounts",
            "   Co-Lending: Partners, Participations, Settlements",
            "   Risk: FLDG, ECL Staging, Provisions",
            "   Income: Servicer Fees, Excess Spread, Withholding",
        ],
        subtitle="Layered Design Pattern"
    )

    # Slide 5: Co-Lending Ratios
    add_table_slide(
        prs,
        "Co-Lending Partnership Types",
        ["Type", "Ratio", "Description"],
        [
            ["Co-Lending", "80:20", "Both parties fund (Standard NBFC-Bank)"],
            ["Co-Lending", "90:10", "Low capital NBFC arrangements"],
            ["Direct Assignment", "100:0", "Lender funds 100%, originator services"],
            ["Participation", "Variable", "Sale of existing loan participation"],
        ],
        subtitle="Flexible Partnership Structures"
    )

    # Slide 6: Collection Split
    add_content_slide(
        prs,
        "Collection Split (80:20 Example)",
        [
            "EMI Received: ₹22,000",
            "",
            "Waterfall:",
            "   1. Servicer Fee Withheld: ₹85 (fee + GST)",
            "   2. Excess Spread Withheld: ₹1,143",
            "   3. Lender Principal (80%): ₹13,600",
            "   4. Lender Interest (after excess): ₹2,857",
            "",
            "Net to Lender: ₹16,372",
            "Net to Originator: ₹5,628 (share + fee + spread)",
        ],
        subtitle="Payment Waterfall with Withholding"
    )

    # Slide 7: FLDG Overview
    add_two_column_slide(
        prs,
        "FLDG (First Loss Default Guarantee)",
        "First Loss FLDG",
        [
            "Originator's guarantee absorbs first",
            "Protects lender up to X%",
            "Example: 5% FLDG on ₹100 Cr",
            "   → ₹5 Cr protection",
            "Trigger: 90+ DPD or Write-off",
        ],
        "Second Loss FLDG",
        [
            "Kicks in after threshold breached",
            "Lender bears first loss up to Y%",
            "Example: 3% first loss, then FLDG",
            "   → Loss of ₹7 Cr:",
            "   → Lender: ₹3 Cr, FLDG: ₹4 Cr",
        ]
    )

    # Slide 8: FLDG Flow
    add_content_slide(
        prs,
        "FLDG Utilization & Recovery",
        [
            "Utilization Flow:",
            "   Loan Defaults → Check FLDG Coverage → Calculate Claim",
            "   → Principal × Partner Share % + Interest (if covered)",
            "   → Approve → Update FLDG Balance → Record Utilization",
            "",
            "Recovery Flow:",
            "   Recovery from Written-off Loan",
            "   → Return to FLDG Pool (up to utilized amount)",
            "   → Excess to Lender",
            "",
            "Top-up: Required when balance < 50% of limit",
        ],
        subtitle="Complete Lifecycle Management"
    )

    # Slide 9: ECL Staging
    add_table_slide(
        prs,
        "ECL Staging (IFRS 9 / Ind AS 109)",
        ["Stage", "Description", "ECL Measurement", "Typical DPD"],
        [
            ["Stage 1", "Performing", "12-month ECL", "0-30 days"],
            ["Stage 2", "Underperforming (SICR)", "Lifetime ECL", "31-90 days"],
            ["Stage 3", "Non-performing", "Lifetime ECL", "90+ days"],
        ],
        subtitle="Forward-Looking Provisioning"
    )

    # Slide 10: ECL Calculation
    add_content_slide(
        prs,
        "ECL Calculation",
        [
            "Formula: ECL = EAD × PD × LGD",
            "",
            "Stage 1 Example:",
            "   EAD = ₹1,00,000 | PD (12m) = 0.5% | LGD = 65%",
            "   ECL = ₹1,00,000 × 0.5% × 65% = ₹325",
            "",
            "Stage 3 Example:",
            "   EAD = ₹1,00,000 | PD = 100% | LGD = 65%",
            "   ECL = ₹1,00,000 × 100% × 65% = ₹65,000",
            "",
            "Stage Assignment: Write-off → NPA → DPD>90 → Restructure → DPD>30 → SICR",
        ],
        subtitle="Expected Credit Loss Calculation"
    )

    # Slide 11: ECL Portfolio Summary
    add_table_slide(
        prs,
        "ECL Portfolio Summary (Month-End)",
        ["Stage", "Loans", "Exposure", "Provision", "Coverage"],
        [
            ["Stage 1", "9,500", "₹950 Cr", "₹3.09 Cr", "0.33%"],
            ["Stage 2", "400", "₹40 Cr", "₹2.60 Cr", "6.50%"],
            ["Stage 3", "100", "₹10 Cr", "₹6.50 Cr", "65.00%"],
            ["Total", "10,000", "₹1,000 Cr", "₹12.19 Cr", "1.22%"],
        ],
        subtitle="Example Portfolio as on 31-Jan-2024"
    )

    # Slide 12: Servicer Income Components
    add_table_slide(
        prs,
        "Servicer Income Components",
        ["Component", "Calculation", "Example"],
        [
            ["Servicer Fee", "Outstanding × Rate × Days/365", "₹100Cr × 0.5% × 30/365 = ₹41K"],
            ["Excess Spread", "Borrower Rate - Lender Yield", "14% - 10% = 4% p.a."],
            ["Performance Fee", "Collections × Rate (if >95%)", "₹98K (0.1% bonus)"],
            ["GST", "18% on Servicer Fee", "₹7,400"],
            ["TDS", "10% on Lender Interest", "₹8,22K deducted"],
        ],
        subtitle="Fee & Income Breakdown"
    )

    # Slide 13: Income Distribution
    add_two_column_slide(
        prs,
        "Monthly Income Distribution",
        "Servicer Income",
        [
            "Servicer Fee: ₹4,10,000",
            "Excess Spread: ₹3,29,000",
            "Performance Fee: ₹98,000",
            "Gross Income: ₹8,37,000",
            "GST Collected: ₹73,800",
            "Total Invoice: ₹9,10,800",
        ],
        "Lender Income",
        [
            "Interest Income: ₹82,19,000",
            "Less: TDS (10%): (₹8,21,900)",
            "Net Interest: ₹73,97,100",
            "",
            "Principal Collections: As per share",
            "Net Settlement: After withholding",
        ]
    )

    # Slide 14: Write-off & ECL Flags
    add_content_slide(
        prs,
        "Write-off & ECL Flags (LoanAccount)",
        [
            "Write-off Flags:",
            "   is_written_off, write_off_date, write_off_amount, write_off_reason",
            "",
            "NPA Flags:",
            "   is_npa, npa_date, npa_category (substandard/doubtful/loss)",
            "",
            "ECL Fields:",
            "   ecl_stage (1/2/3), ecl_stage_date, ecl_provision, ecl_provision_date",
            "",
            "Other Flags:",
            "   is_restructured, sicr_flag, is_fraud, is_co_lent, has_fldg_coverage",
        ],
        subtitle="Comprehensive Flag Tracking Across All Models"
    )

    # Slide 15: Financial Engine
    add_two_column_slide(
        prs,
        "Financial Engine",
        "Day-Count Conventions",
        [
            "30/360 - US corporate standard",
            "ACT/365 - Indian lending standard",
            "ACT/ACT - Government bonds",
            "ACT/360 - Money market",
        ],
        "Schedule Types",
        [
            "EMI - Equal monthly installments",
            "Bullet - Principal at maturity",
            "Interest-Only - Interest payments only",
            "Step-Up/Down - Graduated payments",
            "Balloon - Large final payment",
            "Moratorium - Deferred start",
        ]
    )

    # Slide 16: Lifecycle Management
    add_two_column_slide(
        prs,
        "Loan Lifecycle Management",
        "Restructuring Options",
        [
            "Rate Reduction - Lower EMI",
            "Tenure Extension - Lower EMI",
            "Principal Haircut - Debt relief",
            "Impact on ECL Stage (→ Stage 2)",
        ],
        "Closure Types",
        [
            "Normal - Fully paid as scheduled",
            "Foreclosure - Prepaid before maturity",
            "Settlement (OTS) - Reduced amount",
            "Write-off - Bad debt with recovery",
        ]
    )

    # Slide 17: Collections
    add_table_slide(
        prs,
        "Delinquency & Collections",
        ["Bucket", "DPD", "Status", "Action"],
        [
            ["Current", "0", "Performing", "None"],
            ["1-30", "1-30", "Early", "Reminder"],
            ["31-60", "31-60", "Moderate", "Call"],
            ["61-90", "61-90", "Serious", "Visit"],
            ["90+", "91+", "NPA/Stage 3", "Legal/FLDG"],
        ],
        subtitle="DPD Bucket Classification"
    )

    # Slide 18: Data Models
    add_table_slide(
        prs,
        "Data Model Categories (65+ Models)",
        ["Category", "Models"],
        [
            ["Core", "Borrower, LoanApplication, LoanAccount, LoanProduct"],
            ["Co-Lending", "LoanPartner, LoanParticipation, PartnerLedger, Settlement"],
            ["FLDG", "FLDGArrangement, FLDGUtilization, FLDGRecovery"],
            ["ECL", "ECLConfiguration, ECLStaging, ECLProvision, ECLMovement"],
            ["Servicer", "ServicerArrangement, IncomeAccrual, WithholdingTracker"],
            ["Lifecycle", "LoanRestructure, Prepayment, WriteOff, WriteOffRecovery"],
            ["SCF/Secur", "Counterparty, Invoice, SecuritizationPool, Investor"],
        ],
        subtitle="Comprehensive Data Model"
    )

    # Slide 19: Test Coverage
    add_table_slide(
        prs,
        "Test Coverage (386 Tests)",
        ["Category", "Tests", "Coverage"],
        [
            ["Day-Count & Frequencies", "85", "All conventions"],
            ["Floating Rates & Schedules", "35", "Benchmarks, step-up/down"],
            ["Lifecycle Operations", "26", "Restructure, prepay, close"],
            ["Rules & Workflow", "42", "Engine, state machine"],
            ["SCF & Securitization", "43", "Invoice, pools"],
            ["FLDG", "21", "Utilization, recovery"],
            ["ECL", "29", "Staging, provisions"],
            ["Servicer Income", "25", "Fees, excess spread"],
        ],
        subtitle="Comprehensive Test Suite"
    )

    # Slide 20: API Endpoints
    add_table_slide(
        prs,
        "API Endpoints (60+)",
        ["Module", "Endpoints", "Operations"],
        [
            ["Core", "/borrowers, /loan-accounts", "CRUD + Schedule + Payments"],
            ["Co-Lending", "/loan-participations, /settlements", "CRUD + Settlement"],
            ["FLDG", "/fldg-arrangements, /utilizations", "CRUD + Approve + Recover"],
            ["ECL", "/ecl-staging, /provisions, /uploads", "Stage + Provision + Upload"],
            ["Lifecycle", "/loan-lifecycle/*", "Restructure, Prepay, Close"],
            ["Collections", "/collection-cases, /ptp", "Case management"],
        ],
        subtitle="RESTful API with Swagger Documentation"
    )

    # Slide 21: Security & Compliance
    add_content_slide(
        prs,
        "Security & Regulatory Compliance",
        [
            "Access Control:",
            "   Role-based permissions (RBAC), API key management",
            "",
            "Data Protection:",
            "   Pydantic validation, SQL injection prevention (ORM)",
            "",
            "Audit Trail:",
            "   Complete history for all operations, ECL provisions, FLDG",
            "",
            "Regulatory Compliance:",
            "   IFRS 9 / Ind AS 109 ECL staging",
            "   RBI NPA classification",
            "   Co-lending guidelines compliance",
            "   FLDG disclosure requirements",
        ],
        subtitle="Enterprise-Grade Security"
    )

    # Slide 22: Deployment
    add_two_column_slide(
        prs,
        "Deployment Options",
        "Development",
        [
            "Quick start with SQLite",
            "pip install -r requirements.txt",
            "python -m app.db.init_db",
            "uvicorn app.main:app --reload",
        ],
        "Production",
        [
            "Docker + PostgreSQL",
            "docker compose up -d",
            "alembic upgrade head",
            "Horizontal scaling support",
            "Environment-based config",
        ]
    )

    # Slide 23: Documentation
    add_table_slide(
        prs,
        "Documentation Suite",
        ["Document", "Description"],
        [
            ["SYSTEM_DOCUMENTATION.md", "Complete technical documentation"],
            ["CO_LENDING_PARTNERSHIP.md", "80:20, 90:10, 100:0 arrangements"],
            ["FLDG_GUARANTEE.md", "First/Second Loss Default Guarantee"],
            ["ECL_STAGING_PROVISIONS.md", "IFRS 9 Stage 1, 2, 3 provisioning"],
            ["SERVICER_FEES_INCOME.md", "Fees, excess spread, withholding"],
        ],
        subtitle="Comprehensive Documentation"
    )

    # Slide 24: Key Differentiators
    add_table_slide(
        prs,
        "Key Differentiators",
        ["Feature", "Benefit"],
        [
            ["Multi-Product", "Single platform for all loan types"],
            ["Flexible Co-Lending", "80:20, 90:10, 100:0 with FLDG"],
            ["FLDG Management", "First/Second loss with recovery"],
            ["IFRS 9 ECL", "Stage 1, 2, 3 with month-end batch"],
            ["Servicer Income", "Fee, excess spread, withholding"],
            ["386 Tests", "Production-ready quality"],
        ],
        subtitle="What Sets Us Apart"
    )

    # Slide 25: Future Roadmap
    add_content_slide(
        prs,
        "Future Roadmap",
        [
            "Near-Term:",
            "   User authentication (JWT/OAuth2)",
            "   API rate limiting",
            "   Notification service (email/SMS)",
            "",
            "Medium-Term:",
            "   Mobile SDK, Webhook integrations",
            "   Bureau API, E-signature integration",
            "",
            "Long-Term:",
            "   ML-based credit scoring, Fraud detection",
            "   Multi-tenant SaaS",
        ],
        subtitle="Planned Enhancements"
    )

    # Slide 26: Thank You
    add_title_slide(
        prs,
        "Thank You",
        "Questions?\n\nDocumentation: docs/SYSTEM_DOCUMENTATION.md\nAPI Reference: http://localhost:8000/docs\n\nUnified LOS/LMS v2.0 - Enterprise Lending Made Simple"
    )

    # Save the presentation
    output_path = "LOS_LMS_System_Presentation.pptx"
    prs.save(output_path)
    print(f"Presentation saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    create_presentation()
