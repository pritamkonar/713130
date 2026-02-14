import streamlit as st
import pandas as pd
from fpdf import FPDF

# --- Page Configuration ---
st.set_page_config(page_title="PF Interest Calculation", layout="wide")

# --- CSS for Tables to match Excel look ---
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    .summary-box {
        font-size: 18px; 
        font-weight: bold; 
        margin-top: 20px; 
        padding: 15px; 
        border: 2px solid #f0f2f6; 
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📄 PF Interest Calculation Sheet")

# --- Inputs: Header Info ---
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    school_name = st.text_input("School Name", placeholder="Enter School Name")
    employee_name = st.text_input("Employee Name", placeholder="Enter Employee Name")
with col_h2:
    start_year = st.number_input("Financial Year Start (e.g., 2024)", value=2024, step=1)
    rate_input = st.number_input("Rate of Interest (%)", min_value=0.0, value=7.1, step=0.1, format="%.2f")

# --- Sidebar: Opening Data ---
st.sidebar.header("Account Setup")
opening_balance_input = st.sidebar.number_input("Opening Balance (April 1st)", min_value=0.0, value=0.0, step=100.0, format="%.2f")

# --- Helper: Generate Financial Year Months ---
def get_fy_months(start_year):
    m_names = ["APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER", "JANUARY", "FEBRUARY", "MARCH"]
    fy_months = []
    for i, m in enumerate(m_names):
        y = start_year if i < 9 else start_year + 1
        fy_months.append(f"{m} {str(y)[-2:]}")
    return fy_months

months_list = get_fy_months(start_year)

# --- Main Data Entry ---
if 'input_data' not in st.session_state:
    data = {
        "Month": months_list,
        "Dep_Before_15": [0.0] * 12,
        "PFLR_Before_15": [0.0] * 12,
        "Dep_After_15": [0.0] * 12,
        "PFLR_After_15": [0.0] * 12,
        "Withdrawal": [0.0] * 12,
        "Remarks": [""] * 12
    }
    st.session_state.input_data = pd.DataFrame(data)
else:
    st.session_state.input_data["Month"] = months_list

st.subheader("Monthly Data Entry")
edited_df = st.data_editor(
    st.session_state.input_data,
    column_config={
        "Month": st.column_config.TextColumn("Month", disabled=True),
        "Dep_Before_15": st.column_config.NumberColumn("Deposit (Up to 15th)", format="₹ %.2f"),
        "PFLR_Before_15": st.column_config.NumberColumn("P.F.L.R (Up to 15th)", format="₹ %.2f"),
        "Dep_After_15": st.column_config.NumberColumn("Deposit (16th-End)", format="₹ %.2f"),
        "PFLR_After_15": st.column_config.NumberColumn("P.F.L.R (16th-End)", format="₹ %.2f"),
        "Withdrawal": st.column_config.NumberColumn("Withdrawal", format="₹ %.2f"),
        "Remarks": st.column_config.TextColumn("Remarks")
    },
    hide_index=True,
    use_container_width=True,
    num_rows="fixed"
)

# --- Calculation Engine ---
def calculate_ledger(opening_bal, input_df, rate):
    results = []
    current_bal = opening_bal
    total_interest = 0.0

    # For column sums
    sum_dep_b = 0; sum_pflr_b = 0; sum_dep_a = 0; sum_pflr_a = 0; sum_with = 0

    for index, row in input_df.iterrows():
        month = row['Month']
        dep_before = row['Dep_Before_15']
        pflr_before = row['PFLR_Before_15']
        dep_after = row['Dep_After_15']
        pflr_after = row['PFLR_After_15']
        withdrawal = row['Withdrawal']
        remarks = row['Remarks']

        sum_dep_b += dep_before
        sum_pflr_b += pflr_before
        sum_dep_a += dep_after
        sum_pflr_a += pflr_after
        sum_with += withdrawal

        # Interest Logic: Lowest Balance
        effective_deposit_for_interest = dep_before + pflr_before
        lowest_bal_calc = current_bal + effective_deposit_for_interest - withdrawal
        lowest_bal = max(0, lowest_bal_calc)

        # Truncation Logic
        raw_interest = (lowest_bal * rate) / 1200
        interest = int(raw_interest * 100) / 100.0

        closing_bal = current_bal + dep_before + dep_after + pflr_before + pflr_after - withdrawal

        results.append({
            "Month": month,
            "Opening Balance": current_bal,
            "Dep (<15th)": dep_before,
            "PFLR (<15th)": pflr_before,
            "Dep (>15th)": dep_after,
            "PFLR (>15th)": pflr_after,
            "Withdrawal": withdrawal,
            "Lowest Balance": lowest_bal,
            "Interest": interest,
            "Closing Balance": closing_bal,
            "Remarks": remarks
        })

        current_bal = closing_bal
        total_interest += interest
    
    df_res = pd.DataFrame(results)
    totals = {
        "Dep (<15th)": sum_dep_b, "PFLR (<15th)": sum_pflr_b,
        "Dep (>15th)": sum_dep_a, "PFLR (>15th)": sum_pflr_a,
        "Withdrawal": sum_with, "Interest": total_interest
    }
    return df_res, totals, current_bal

result_df, totals, final_principal = calculate_ledger(opening_balance_input, edited_df, rate_input)

# --- Display Results ---
st.divider()
st.subheader("Calculation Result")

display_df = result_df.copy()
total_row = pd.DataFrame([{
    "Month": "TOTAL",
    "Opening Balance": None,
    "Dep (<15th)": totals["Dep (<15th)"],
    "PFLR (<15th)": totals["PFLR (<15th)"],
    "Dep (>15th)": totals["Dep (>15th)"],
    "PFLR (>15th)": totals["PFLR (>15th)"],
    "Withdrawal": totals["Withdrawal"],
    "Lowest Balance": None,
    "Interest": totals["Interest"],
    "Closing Balance": None,
    "Remarks": ""
}])
display_df = pd.concat([display_df, total_row], ignore_index=True)
st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- WEB PAGE SUMMARY SECTION (Added) ---
final_total_balance = final_principal + totals['Interest']

st.markdown("### Final Summary")
col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    st.markdown(f"""
    <div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>
        <p style='margin:0; font-weight:bold;'>Principal :</p>
        <p style='margin:0; font-size:20px;'>₹ {final_principal:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

with col_s2:
    st.markdown(f"""
    <div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>
        <p style='margin:0; font-weight:bold;'>Interest :</p>
        <p style='margin:0; font-size:20px;'>₹ {totals['Interest']:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

with col_s3:
    st.markdown(f"""
    <div style='background-color:#e6ffe6; padding:10px; border-radius:5px;'>
        <p style='margin:0; font-weight:bold;'>TOTAL :</p>
        <p style='margin:0; font-size:20px;'>₹ {final_total_balance:,.2f}</p>
    </div>
    """, unsafe_allow_html=True)

# --- PDF GENERATION (Centered & Fixed Box) ---
def create_exact_pdf(df, school, name, year, rate, totals, final_bal):
    pdf = FPDF('L', 'mm', 'A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # --- 1. Top Headers ---
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, f"SCHOOL NAME :- {school}", 0, 1, 'C')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"INTEREST CALCULATION OF PROVIDENT FUND ACCOUNT FOR THE YEAR - {year}-{year+1}", 0, 1, 'C')
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(140, 8, f"NAME :- {name}", 0, 0, 'L')
    pdf.cell(0, 8, f"RATE OF INTEREST:- {rate} %", 0, 1, 'R')
    pdf.ln(2)

    # --- 2. Table Column Widths ---
    w = {
        "mo": 26, "op": 26, 
        "d1": 24, "p1": 24, 
        "d2": 24, "p2": 24, 
        "wi": 22, "lo": 26, 
        "in": 20, "cl": 26, 
        "re": 30
    }

    pdf.set_font('Arial', 'B', 8)
    x = pdf.get_x()
    y = pdf.get_y()
    
    # --- 3. Complex Header Construction ---
    # Month
    pdf.rect(x, y, w['mo'], 12)
    pdf.set_xy(x, y+4) 
    pdf.cell(w['mo'], 4, "Month", 0, 0, 'C')
    
    # Opening Balance
    pdf.rect(x+w['mo'], y, w['op'], 12)
    pdf.set_xy(x+w['mo'], y+4)
    pdf.cell(w['op'], 4, "Opening Balance", 0, 0, 'C')
    
    # Group: Deposit up to 15th
    grp1_x = x + w['mo'] + w['op']
    pdf.rect(grp1_x, y, w['d1']+w['p1'], 6)
    pdf.set_xy(grp1_x, y+1)
    pdf.cell(w['d1']+w['p1'], 4, "Deposit up to 15th day", 0, 0, 'C')
    
    pdf.rect(grp1_x, y+6, w['d1'], 6)
    pdf.set_xy(grp1_x, y+7)
    pdf.cell(w['d1'], 4, "Deposit", 0, 0, 'C')
    
    pdf.rect(grp1_x+w['d1'], y+6, w['p1'], 6)
    pdf.set_xy(grp1_x+w['d1'], y+7)
    pdf.cell(w['p1'], 4, "P.F.L.R", 0, 0, 'C')

    # Group: Deposit 16th to Last
    grp2_x = grp1_x + w['d1'] + w['p1']
    grp2_w = w['d2'] + w['p2']
    pdf.rect(grp2_x, y, grp2_w, 6)
    pdf.set_xy(grp2_x, y) 
    pdf.multi_cell(grp2_w, 3, "Deposit between\n16th & last day", 0, 'C')
    
    pdf.rect(grp2_x, y+6, w['d2'], 6)
    pdf.set_xy(grp2_x, y+7)
    pdf.cell(w['d2'], 4, "Deposit", 0, 0, 'C')
    
    pdf.rect(grp2_x+w['d2'], y+6, w['p2'], 6)
    pdf.set_xy(grp2_x+w['d2'], y+7)
    pdf.cell(w['p2'], 4, "P.F.L.R", 0, 0, 'C')

    # Withdrawal
    curr_x = grp2_x + w['d2'] + w['p2']
    pdf.rect(curr_x, y, w['wi'], 12)
    pdf.set_xy(curr_x, y+4)
    pdf.cell(w['wi'], 4, "Withdrawal", 0, 0, 'C')

    # Lowest Balance
    curr_x += w['wi']
    pdf.rect(curr_x, y, w['lo'], 12)
    pdf.set_xy(curr_x, y+4)
    pdf.cell(w['lo'], 4, "Lowest Balance", 0, 0, 'C')

    # Interest
    curr_x += w['lo']
    pdf.rect(curr_x, y, w['in'], 12)
    pdf.set_xy(curr_x, y+2)
    pdf.multi_cell(w['in'], 4, "Interest\nfor month", 0, 'C')

    # Closing Balance
    curr_x += w['in']
    pdf.rect(curr_x, y, w['cl'], 12)
    pdf.set_xy(curr_x, y+4)
    pdf.cell(w['cl'], 4, "Closing Balance", 0, 0, 'C')

    # Remarks
    curr_x += w['cl']
    pdf.rect(curr_x, y, w['re'], 12)
    pdf.set_xy(curr_x, y+4)
    pdf.cell(w['re'], 4, "Remarks", 0, 0, 'C')

    pdf.set_xy(x, y + 12)

    # --- 4. Table Body (ALL CENTER ALIGNED) ---
    pdf.set_font('Arial', '', 9) 
    row_h = 8

    def cell_c(w, txt, border=1):
        pdf.cell(w, row_h, str(txt), border, 0, 'C')

    for index, row in df.iterrows():
        cell_c(w['mo'], row['Month'])
        cell_c(w['op'], f"{row['Opening Balance']:.2f}")
        cell_c(w['d1'], f"{row['Dep (<15th)']:.2f}")
        cell_c(w['p1'], f"{row['PFLR (<15th)']:.2f}")
        cell_c(w['d2'], f"{row['Dep (>15th)']:.2f}")
        cell_c(w['p2'], f"{row['PFLR (>15th)']:.2f}")
        cell_c(w['wi'], f"{row['Withdrawal']:.2f}")
        cell_c(w['lo'], f"{row['Lowest Balance']:.2f}")
        cell_c(w['in'], f"{row['Interest']:.2f}")
        cell_c(w['cl'], f"{row['Closing Balance']:.2f}")
        cell_c(w['re'], row['Remarks'])
        pdf.ln()

    # --- 5. Total Row ---
    pdf.set_font('Arial', 'B', 9)
    cell_c(w['mo'], "Total")
    cell_c(w['op'], "")
    cell_c(w['d1'], f"{totals['Dep (<15th)']:.2f}")
    cell_c(w['p1'], f"{totals['PFLR (<15th)']:.2f}")
    cell_c(w['d2'], f"{totals['Dep (>15th)']:.2f}")
    cell_c(w['p2'], f"{totals['PFLR (>15th)']:.2f}")
    cell_c(w['wi'], f"{totals['Withdrawal']:.2f}")
    cell_c(w['lo'], "")
    cell_c(w['in'], f"{totals['Interest']:.2f}")
    cell_c(w['cl'], "")
    cell_c(w['re'], "")
    pdf.ln(12)

    # --- 6. Footer ---
    pdf.ln(5)
    total_balance = final_bal + totals['Interest']

    pdf.set_font('Arial', '', 10)
    pdf.cell(30, 6, "Principal", 0, 0)
    pdf.cell(30, 6, f": {final_bal:.2f}", 0, 1)
    
    pdf.cell(30, 6, "Interest", 0, 0)
    pdf.cell(30, 6, f": {totals['Interest']:.2f}", 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, "TOTAL", 0, 0)
    pdf.cell(30, 6, f": {total_balance:.2f}", 0, 0)
    
    pdf.set_x(230) 
    pdf.cell(40, 6, "Signature of HM", 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# Button to Generate
if st.button("Generate PDF Report"):
    pdf_bytes = create_exact_pdf(result_df, school_name, employee_name, start_year, rate_input, totals, final_principal)
    st.download_button("📄 Download PDF", pdf_bytes, 'PF_Ledger_Final.pdf', 'application/pdf')
