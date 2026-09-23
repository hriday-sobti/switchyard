"""
Generates an interactive Excel Scenario Model workbook for SWITCHYARD.
Models operational labor efficiency, SLA breach penalties, sensitivity matrices,
and executive financial impact tables.
"""
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def create_excel_scenario_model(output_path: Path = Path("reports/switchyard_scenario_model.xlsx")):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()

    # Sheet 1: Executive Summary & Assumptions
    ws1 = wb.active
    ws1.title = "Executive Summary"
    ws1.views.sheetView[0].showGridLines = True

    # Styling Palette
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    sub_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    highlight_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")

    font_title = Font(name="Calibri", size=16, bold=True, color="1E293B")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True, color="000000")
    font_regular = Font(name="Calibri", size=11, color="000000")
    font_kpi_num = Font(name="Calibri", size=14, bold=True, color="047857")

    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    # Title Block
    ws1["A1"] = "SWITCHYARD: Operational Reliability & Financial Impact Model"
    ws1["A1"].font = font_title
    ws1["A2"] = "Scenario analysis modeling triage efficiency gains and SLA penalty avoidance."
    ws1["A2"].font = Font(name="Calibri", size=10, italic=True, color="64748B")

    # Table 1: Model Assumptions
    ws1["A4"] = "Model Assumptions & Parameters"
    ws1["A4"].font = Font(name="Calibri", size=12, bold=True, color="1E293B")

    assumptions = [
        ("Parameter", "Baseline Value", "Unit / Metric"),
        ("Monthly Operational Incident Volume", 15000, "incidents / month"),
        ("Baseline SLA Breach Rate", 0.118, "percentage (11.8%)"),
        ("Target Modeled SLA Breach Rate", 0.072, "percentage (7.2%)"),
        ("Manual Triage Time per Case", 14.0, "minutes"),
        ("SWITCHYARD Automated Triage Time", 3.5, "minutes"),
        ("Average Penalty per SLA Breach", 1250.0, "USD ($)"),
        ("Blended Engineer Hourly Cost", 65.0, "USD ($/hr)"),
    ]

    for r_idx, row in enumerate(assumptions, start=5):
        for c_idx, val in enumerate(row, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.border = thin_border
            if r_idx == 5:
                cell.fill = header_fill
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center" if c_idx > 1 else "left")
            else:
                cell.font = font_regular
                if c_idx == 2 and isinstance(val, (int, float)):
                    if "percentage" in row[2]:
                        cell.number_format = "0.0%"
                    elif "USD" in row[2]:
                        cell.number_format = "$#,##0.00"
                    else:
                        cell.number_format = "#,##0"

    # Table 2: Modeled Outcomes
    ws1["A15"] = "Projected Annual Operational Impact (Excel Formulas)"
    ws1["A15"].font = Font(name="Calibri", size=12, bold=True, color="1E293B")

    headers_out = ["Impact Metric", "Formula / Derivation", "Annual Projected Outcome"]
    for c_idx, h in enumerate(headers_out, start=1):
        cell = ws1.cell(row=16, column=c_idx, value=h)
        cell.fill = header_fill
        cell.font = font_header
        cell.border = thin_border

    outcomes = [
        ("Monthly Triage Hours Saved", "=(B6*(B9-B10))/60", "hours / month"),
        ("Annual Triage Hours Reclaimed", "=C17*12", "hours / year"),
        ("Annual Engineering Productivity Value", "=C18*B12", "$ / year"),
        ("Annual SLA Breaches Prevented", "=B6*(B7-B8)*12", "cases / year"),
        ("Annual Penalty Avoidance Savings", "=C20*B11", "$ / year"),
        ("Total Annual Net Economic Benefit", "=C19+C21", "$ / year"),
    ]

    for r_idx, (m_title, formula, unit_label) in enumerate(outcomes, start=17):
        c1 = ws1.cell(row=r_idx, column=1, value=m_title)
        c2 = ws1.cell(row=r_idx, column=2, value=unit_label)
        c3 = ws1.cell(row=r_idx, column=3, value=formula)

        c1.font = font_bold if r_idx == 22 else font_regular
        c2.font = font_regular
        c3.font = font_kpi_num if r_idx == 22 else font_bold

        c1.border = thin_border
        c2.border = thin_border
        c3.border = thin_border

        if r_idx == 22:
            c1.fill = highlight_fill
            c2.fill = highlight_fill
            c3.fill = highlight_fill

        if "$" in unit_label:
            c3.number_format = "$#,##0.00"
        else:
            c3.number_format = "#,##0.0"

    # Sheet 2: Volume Sensitivity Matrix
    ws2 = wb.create_sheet(title="Sensitivity Matrix")
    ws2.views.sheetView[0].showGridLines = True

    ws2["A1"] = "Incident Volume vs. SLA Breach Reduction Sensitivity ($ Net Benefit)"
    ws2["A1"].font = font_title

    volumes = [5000, 10000, 15000, 20000, 25000, 50000]
    breach_deltas = [0.02, 0.03, 0.046, 0.06, 0.08]

    # Header Row
    ws2.cell(row=3, column=1, value="Monthly Incident Volume").font = font_header
    ws2.cell(row=3, column=1).fill = header_fill
    ws2.cell(row=3, column=1).border = thin_border

    for c_idx, delta in enumerate(breach_deltas, start=2):
        cell = ws2.cell(row=3, column=c_idx, value=f"{delta*100:.1f}% Breach Reduction")
        cell.font = font_header
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center")

    for r_idx, vol in enumerate(volumes, start=4):
        v_cell = ws2.cell(row=r_idx, column=1, value=vol)
        v_cell.font = font_bold
        v_cell.border = thin_border
        v_cell.number_format = "#,##0"

        for c_idx, delta in enumerate(breach_deltas, start=2):
            # Formula: (Vol * 10.5 / 60 * 12 * $65) + (Vol * Delta * 12 * $1250)
            formula_cell = ws2.cell(
                row=r_idx,
                column=c_idx,
                value=f"=($A{r_idx}*(10.5/60)*12*65) + ($A{r_idx}*{delta}*12*1250)"
            )
            formula_cell.font = font_regular
            formula_cell.border = thin_border
            formula_cell.number_format = "$#,##0"

    # Adjust Column Widths
    for ws in [ws1, ws2]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    wb.save(output_path)
    print(f"Generated Excel Scenario Model at {output_path}")


if __name__ == "__main__":
    create_excel_scenario_model()
