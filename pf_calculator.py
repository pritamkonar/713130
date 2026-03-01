import streamlit as st
import pandas as pd
from fpdf import FPDF
import io
import xlsxwriter

# --- Page Configuration ---
st.set_page_config(page_title="PF Interest Calculation", layout="wide")

# --- CSS for Tables & Layout ---
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    .summary-box { background-color: #f9f9f9; padding: 15px; border-radius: 10px; border: 1px solid #ddd; text-align: center; margin-bottom: 10px; }
    .total-box { background-color: #e6ffe6; padding: 15px; border-radius: 10px; border: 1px solid #b3ffb3; text-align: center; margin-bottom: 10px; }
    .stButton button { width: 100%; font-weight: bold; height: 50px; }
</style>
""", unsafe_allow_html=True)

st.title("📄 PF Interest Calculation Sheet By Pritam Konar")

# --- Inputs ---
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    school_name = st.text_input("School Name", placeholder="Enter School Name")
    employee_name = st.text_input("Employee Name", placeholder="Enter Employee Name")
with col_h2:
    start_year = st.number_input("Financial Year Start (e.g., 2024)", value=2024, step=1)
    
    # Store the default rate in session state to detect changes
    if 'prev_default_rate' not in st.session_state:
        st.session_state.prev_default_rate = 7.1
        
    rate_input = st.number_input("Default Rate of Interest (%)", min_value=0.0, value=7.1, step=0.1, format="%.2f")

# --- Sidebar ---
st.sidebar.header("Account Setup")
opening_balance_input = st.sidebar.number_input("Opening Balance (April 1st)", min_value=0.0, value=0.0, step=100.0, format="%.2f")

# --- Helper: Months ---
def get_fy_months(start_year):
    m_names = ["APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER", "JANUARY", "FEBRUARY", "MARCH"]
    return [f"{m} {str(start_year if i < 9 else start_year + 1)[-2:]}" for i, m in enumerate(m_names)]

months_list = get_fy_months(start_year)

# --- Data Entry ---
# Initialize or update the Rate column if the global Default Rate changes
if 'input_data' not in st.session_state:
    st.session_state.input_data = pd.DataFrame({
        "Month": months_list, 
        "Dep_Before_15": [0.0]*12, "PFLR_Before_15": [0.0]*12, 
        "Dep_After_15": [0.0]*12, "PFLR_After_15": [0.0]*12, 
        "Withdrawal": [0.0]*12, 
        "Monthly_Rate": [rate_input]*12, # NEW COLUMN
        "Remarks": [""]*12
    })
else:
    st.session_state.input_data["Month"] = months_list
    # Auto-update all monthly rates if the user changes the Top Default Rate box
    if rate_input != st.session_state.prev_default_rate:
        st.session_state.input_data["Monthly_Rate"] = rate_input
        st.session_state.prev_default_rate = rate_input

st.subheader("Monthly Data Entry")
edited_df = st.data_editor(
    st.session_state.input_data,
    column_config={
        "Month": st.column_config.TextColumn("Month", disabled=True),
        "Dep_Before_15": st.column_config.NumberColumn("Deposit (< 15th)", format="₹ %.2f"),
        "PFLR_Before_15": st.column_config.NumberColumn("P.F.L.R (< 15th)", format="₹ %.2f"),
        "Dep_After_15": st.column_config.NumberColumn("Deposit (> 15th)", format="₹ %.2f"),
        "PFLR_After_15": st.column_config.NumberColumn("P.F.L.R (> 15th)", format="₹ %.2f"),
        "Withdrawal": st.column_config.NumberColumn("Withdrawal", format="₹ %.2f"),
        "Monthly_Rate": st.column_config.NumberColumn("Rate %", format="%.2f %%"), # EXPOSED IN UI
        "Remarks": st.column_config.TextColumn("Remarks")
    },
    hide_index=True, use_container_width=True, num_rows="fixed"
)

# --- Calculation Logic ---
def calculate_ledger(opening_bal, input_df):
    results = []
    current_bal = opening_bal
    total_interest = 0.0
    sum_dep_b = 0; sum_pflr_b = 0; sum_dep_a = 0; sum_pflr_a = 0; sum_with = 0

    for index, row in input_df.iterrows():
        month = row['Month']
        dep_before = row['Dep_Before_15']; pflr_before = row['PFLR_Before_15']
        dep_after = row['Dep_After_15']; pflr_after = row['PFLR_After_15']
        withdrawal = row['Withdrawal']; remarks = row['Remarks']
        
        # Pull the specific rate for this month
        month_rate = row['Monthly_Rate']

        sum_dep_b += dep_before; sum_pflr_b += pflr_before
        sum_dep_a += dep_after; sum_pflr_a += pflr_after; sum_with += withdrawal

        effective_deposit_for_interest = dep_before + pflr_before
        lowest_bal = max(0, current_bal + effective_deposit_for_interest - withdrawal)

        # Interest calculation using the CUSTOM MONTHLY RATE
        raw_interest = (lowest_bal * month_rate) / 1200
        interest = int(raw_interest * 100) / 100.0

        closing_bal = current_bal + dep_before + dep_after + pflr_before + pflr_after - withdrawal

        results.append({
            "Month": month, "Opening Balance": current_bal, "Dep (<15th)": dep_before, 
            "PFLR (<15th)": pflr_before, "Dep (>15th)": dep_after, "PFLR (>15th)": pflr_after, 
            "Withdrawal": withdrawal, "Lowest Balance": lowest_bal, 
            "Rate (%)": month_rate, # Store for display
            "Interest": interest, "Closing Balance": closing_bal, "Remarks": remarks
        })

        current_bal = closing_bal
        total_interest += interest
    
    df_res = pd.DataFrame(results)
    totals = {
        "Dep (<15th)": sum_dep_b, "PFLR (<15th)": sum_pflr_b, "Dep (>15th)": sum_dep_a, 
        "PFLR (>15th)": sum_pflr_a, "Withdrawal": sum_with, "Interest": total_interest
    }
    return df_res, totals, current_bal

result_df, totals, final_principal = calculate_ledger(opening_balance_input, edited_df)

# --- Display Results ---
st.divider()
st.subheader("Calculation Result")

display_df = result_df.copy()
# We don't necessarily need to show the Rate column in the final output grid to keep it matching your template,
# but it's calculated correctly in the background. Dropping it from the display dataframe.
display_df_view = display_df.drop(columns=['Rate (%)'])

total_row = pd.DataFrame([{
    "Month": "TOTAL", "Opening Balance": None, "Dep (<15th)": totals["Dep (<15th)"], 
    "PFLR (<15th)": totals["PFLR (<15th)"], "Dep (>15th)": totals["Dep (>15th)"], 
    "PFLR (>15th)": totals["PFLR (>15th)"], "Withdrawal": totals["Withdrawal"], 
    "Lowest Balance": None, "Interest": totals["Interest"], "Closing Balance": None, "Remarks": ""
}])
display_df_view = pd.concat([display_df_view, total_row], ignore_index=True)
st.dataframe(display_df_view, use_container_width=True, hide_index=True)

# --- SUMMARY SECTION ---
final_total_balance = final_principal + totals['Interest']

st.markdown("### Final Summary")
col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    st.markdown(f'<div class="summary-box"><div style="font-weight:bold; color:#555;">Principal</div><div style="font-size:22px;">₹ {final_principal:,.2f}</div></div>', unsafe_allow_html=True)
with col_s2:
    st.markdown(f'<div class="summary-box"><div style="font-weight:bold; color:#555;">Interest</div><div style="font-size:22px;">₹ {totals["Interest"]:,.2f}</div></div>', unsafe_allow_html=True)
with col_s3:
    st.markdown(f'<div class="total-box"><div style="font-weight:bold; color:#005500;">TOTAL</div><div style="font-size:22px; color:#005500;">₹ {final_total_balance:,.2f}</div></div>', unsafe_allow_html=True)

# --- PDF GENERATION (Unchanged to match your template) ---
def create_pdf(df, school, name, year, rate, totals, final_bal):
    pdf = FPDF('L', 'mm', 'A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    pdf.set_font('Arial', '', 14)
    pdf.multi_cell(0, 8, f"SCHOOL NAME :- {school}", 0, 'C')
    pdf.set_font('Arial', '', 9)
    pdf.cell(0, 8, f"INTEREST CALCULATION OF PROVIDENT FUND ACCOUNT FOR THE YEAR - {year}-{year+1}", 0, 1, 'C')
    pdf.ln(2) 
    pdf.set_font('Arial', '', 10)
    pdf.cell(140, 8, f"NAME :- {name}", 0, 0, 'L')
    pdf.cell(0, 8, f"RATE OF INTEREST:- {rate} %", 0, 1, 'R')
    pdf.ln(5) 

    w = {"mo": 26, "op": 26, "d1": 24, "p1": 24, "d2": 24, "p2": 24, "wi": 22, "lo": 26, "in": 20, "cl": 26, "re": 30}
    pdf.set_font('Arial', '', 8) 
    x, y = pdf.get_x(), pdf.get_y()
    
    pdf.rect(x, y, w['mo'], 12); pdf.set_xy(x, y+4); pdf.cell(w['mo'], 4, "Month", 0, 0, 'C')
    pdf.rect(x+w['mo'], y, w['op'], 12); pdf.set_xy(x+w['mo'], y+4); pdf.cell(w['op'], 4, "Opening Balance", 0, 0, 'C')
    
    grp1_x = x + w['mo'] + w['op']
    pdf.rect(grp1_x, y, w['d1']+w['p1'], 6); pdf.set_xy(grp1_x, y+1); pdf.cell(w['d1']+w['p1'], 4, "Deposit up to 15th day", 0, 0, 'C')
    pdf.rect(grp1_x, y+6, w['d1'], 6); pdf.set_xy(grp1_x, y+7); pdf.cell(w['d1'], 4, "Deposit", 0, 0, 'C')
    pdf.rect(grp1_x+w['d1'], y+6, w['p1'], 6); pdf.set_xy(grp1_x+w['d1'], y+7); pdf.cell(w['p1'], 4, "P.F.L.R", 0, 0, 'C')

    grp2_x = grp1_x + w['d1'] + w['p1']; grp2_w = w['d2'] + w['p2']
    pdf.rect(grp2_x, y, grp2_w, 6); pdf.set_xy(grp2_x, y); pdf.multi_cell(grp2_w, 3, "Deposit between\n16th & last day", 0, 'C')
    pdf.rect(grp2_x, y+6, w['d2'], 6); pdf.set_xy(grp2_x, y+7); pdf.cell(w['d2'], 4, "Deposit", 0, 0, 'C')
    pdf.rect(grp2_x+w['d2'], y+6, w['p2'], 6); pdf.set_xy(grp2_x+w['d2'], y+7); pdf.cell(w['p2'], 4, "P.F.L.R", 0, 0, 'C')

    curr_x = grp2_x + w['d2'] + w['p2']
    pdf.rect(curr_x, y, w['wi'], 12); pdf.set_xy(curr_x, y+4); pdf.cell(w['wi'], 4, "Withdrawal", 0, 0, 'C')
    curr_x += w['wi']
    pdf.rect(curr_x, y, w['lo'], 12); pdf.set_xy(curr_x, y+4); pdf.cell(w['lo'], 4, "Lowest Balance", 0, 0, 'C')
    curr_x += w['lo']
    pdf.rect(curr_x, y, w['in'], 12); pdf.set_xy(curr_x, y+2); pdf.multi_cell(w['in'], 4, "Interest\nfor month", 0, 'C')
    curr_x += w['in']
    pdf.rect(curr_x, y, w['cl'], 12); pdf.set_xy(curr_x, y+4); pdf.cell(w['cl'], 4, "Closing Balance", 0, 0, 'C')
    curr_x += w['cl']
    pdf.rect(curr_x, y, w['re'], 12); pdf.set_xy(curr_x, y+4); pdf.cell(w['re'], 4, "Remarks", 0, 0, 'C')

    pdf.set_xy(x, y + 12)
    pdf.set_font('Arial', '', 9) 
    row_h = 8
    def cell_c(w, txt, border=1): pdf.cell(w, row_h, str(txt), border, 0, 'C')

    for _, row in df.iterrows():
        cell_c(w['mo'], row['Month']); cell_c(w['op'], f"{row['Opening Balance']:.2f}"); cell_c(w['d1'], f"{row['Dep (<15th)']:.2f}"); cell_c(w['p1'], f"{row['PFLR (<15th)']:.2f}"); cell_c(w['d2'], f"{row['Dep (>15th)']:.2f}"); cell_c(w['p2'], f"{row['PFLR (>15th)']:.2f}"); cell_c(w['wi'], f"{row['Withdrawal']:.2f}"); cell_c(w['lo'], f"{row['Lowest Balance']:.2f}"); cell_c(w['in'], f"{row['Interest']:.2f}"); cell_c(w['cl'], f"{row['Closing Balance']:.2f}"); cell_c(w['re'], row['Remarks'])
        pdf.ln()

    pdf.set_font('Arial', '', 9)
    cell_c(w['mo'], "Total"); cell_c(w['op'], ""); cell_c(w['d1'], f"{totals['Dep (<15th)']:.2f}"); cell_c(w['p1'], f"{totals['PFLR (<15th)']:.2f}"); cell_c(w['d2'], f"{totals['Dep (>15th)']:.2f}"); cell_c(w['p2'], f"{totals['PFLR (>15th)']:.2f}"); cell_c(w['wi'], f"{totals['Withdrawal']:.2f}"); cell_c(w['lo'], ""); cell_c(w['in'], f"{totals['Interest']:.2f}"); cell_c(w['cl'], ""); cell_c(w['re'], "")
    pdf.ln(12)

    pdf.ln(5)
    pdf.set_font('Arial', '', 10)
    pdf.cell(30, 6, "Principal", 0, 0); pdf.cell(30, 6, f": {final_bal:.2f}", 0, 1)
    pdf.cell(30, 6, "Interest", 0, 0); pdf.cell(30, 6, f": {totals['Interest']:.2f}", 0, 1)
    pdf.cell(30, 6, "TOTAL", 0, 0); pdf.cell(30, 6, f": {(final_bal + totals['Interest']):.2f}", 0, 0)
    pdf.set_x(230); pdf.cell(40, 6, "Signature of HM", 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# --- EXCEL GENERATION (Unchanged to match your template) ---
def create_excel(df, school, name, year, rate, totals, final_bal):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    worksheet.set_landscape(); worksheet.set_paper(9); worksheet.fit_to_pages(1, 1); worksheet.set_margins(0.25, 0.25, 0.25, 0.25)
    base_font = 'Calibri'
    
    title_fmt = workbook.add_format({'font_name': base_font, 'align': 'center', 'valign': 'vcenter', 'font_size': 14})
    subtitle_fmt = workbook.add_format({'font_name': base_font, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})
    header_fmt = workbook.add_format({'font_name': base_font, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 10})
    text_fmt = workbook.add_format({'font_name': base_font, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
    money_fmt = workbook.add_format({'font_name': base_font, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'num_format': '#,##0.00', 'font_size': 10})
    left_fmt = workbook.add_format({'font_name': base_font, 'align': 'left', 'font_size': 10})
    right_fmt = workbook.add_format({'font_name': base_font, 'align': 'right', 'font_size': 10})

    worksheet.set_column('A:A', 12); worksheet.set_column('B:B', 14); worksheet.set_column('C:F', 11); worksheet.set_column('G:G', 11); worksheet.set_column('H:H', 14); worksheet.set_column('I:I', 11); worksheet.set_column('J:J', 14); worksheet.set_column('K:K', 15) 

    worksheet.merge_range('A1:K1', f"SCHOOL NAME :- {school}", title_fmt)
    worksheet.merge_range('A2:K2', f"INTEREST CALCULATION OF PROVIDENT FUND ACCOUNT FOR THE YEAR - {year}-{year+1}", subtitle_fmt)
    worksheet.merge_range('A3:F3', f"NAME :- {name}", left_fmt); worksheet.merge_range('G3:K3', f"RATE OF INTEREST:- {rate} %", right_fmt)

    worksheet.merge_range('A4:A5', "Month", header_fmt); worksheet.merge_range('B4:B5', "Opening Balance", header_fmt)
    worksheet.merge_range('C4:D4', "Deposit up to 15th day", header_fmt); worksheet.write('C5', "Deposit", header_fmt); worksheet.write('D5', "P.F.L.R", header_fmt)
    worksheet.merge_range('E4:F4', "Deposit between 16th & last day", header_fmt); worksheet.write('E5', "Deposit", header_fmt); worksheet.write('F5', "P.F.L.R", header_fmt)
    worksheet.merge_range('G4:G5', "Withdrawal", header_fmt); worksheet.merge_range('H4:H5', "Lowest Balance", header_fmt); worksheet.merge_range('I4:I5', "Interest for the month", header_fmt); worksheet.merge_range('J4:J5', "Closing Balance", header_fmt); worksheet.merge_range('K4:K5', "Remarks", header_fmt)

    row = 5
    for _, r in df.iterrows():
        worksheet.write(row, 0, r['Month'], text_fmt); worksheet.write(row, 1, r['Opening Balance'], money_fmt); worksheet.write(row, 2, r['Dep (<15th)'], money_fmt); worksheet.write(row, 3, r['PFLR (<15th)'], money_fmt); worksheet.write(row, 4, r['Dep (>15th)'], money_fmt); worksheet.write(row, 5, r['PFLR (>15th)'], money_fmt); worksheet.write(row, 6, r['Withdrawal'], money_fmt); worksheet.write(row, 7, r['Lowest Balance'], money_fmt); worksheet.write(row, 8, r['Interest'], money_fmt); worksheet.write(row, 9, r['Closing Balance'], money_fmt); worksheet.write(row, 10, r['Remarks'], text_fmt)
        row += 1

    worksheet.write(row, 0, "Total", text_fmt); worksheet.write(row, 1, "", text_fmt); worksheet.write(row, 2, totals['Dep (<15th)'], money_fmt); worksheet.write(row, 3, totals['PFLR (<15th)'], money_fmt); worksheet.write(row, 4, totals['Dep (>15th)'], money_fmt); worksheet.write(row, 5, totals['PFLR (>15th)'], money_fmt); worksheet.write(row, 6, totals['Withdrawal'], money_fmt); worksheet.write(row, 7, "", text_fmt); worksheet.write(row, 8, totals['Interest'], money_fmt); worksheet.write(row, 9, "", text_fmt); worksheet.write(row, 10, "", text_fmt)

    row += 2
    summary_val_fmt = workbook.add_format({'font_name': base_font, 'font_size': 10, 'align': 'left'})
    
    worksheet.write(row, 0, "Principal", left_fmt); worksheet.write(row, 2, f": {final_bal:.2f}", summary_val_fmt)
    row += 1; worksheet.write(row, 0, "Interest", left_fmt); worksheet.write(row, 2, f": {totals['Interest']:.2f}", summary_val_fmt)
    row += 1; worksheet.write(row, 0, "TOTAL", left_fmt); worksheet.write(row, 2, f": {(final_bal + totals['Interest']):.2f}", summary_val_fmt)
    worksheet.merge_range(row, 8, row, 10, "Signature of HM", workbook.add_format({'font_name': base_font, 'align': 'center', 'valign': 'bottom'}))

    workbook.close()
    return output.getvalue()

# --- DOWNLOAD BUTTONS ---
st.write("") 
col_d1, col_d2 = st.columns(2)

pdf_bytes = create_pdf(result_df, school_name, employee_name, start_year, rate_input, totals, final_principal)
with col_d1:
    st.download_button("📄 Download PDF", pdf_bytes, f"PF_{start_year}.pdf", 'application/pdf', use_container_width=True)

excel_bytes = create_excel(result_df, school_name, employee_name, start_year, rate_input, totals, final_principal)
with col_d2:
    st.download_button("📊 Download Excel", excel_bytes, f"PF_{start_year}.xlsx", 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
