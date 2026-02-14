import streamlit as st
import pandas as pd
from fpdf import FPDF

# --- Page Configuration ---
st.set_page_config(page_title="PF Interest Calculation", layout="wide")

# --- CSS for Tables to match Excel look ---
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
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

# Display logic (simplified for UI)
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

# --- PDF GENERATION (EXACT MATCH) ---
def create_exact_pdf(df, school, name, year, rate, totals, final_bal):
    # A4 Landscape: 297mm width. 
    # Margins 10mm L/R -> 277mm usable width.
    pdf = FPDF('L', 'mm', 'A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_page()
    
    # --- 1. Headers ---
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, f"SCHOOL NAME :- {school}", 0, 1, 'C')
    
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"INTEREST CALCULATION OF PROVIDENT FUND ACCOUNT FOR THE YEAR - {year}-{year+1}", 0, 1, 'C')
    
    pdf.set_font('Arial', 'B', 10)
    # Name (Left) and Rate (Right)
    # Using a borderless cell trick to align them on the same line
    pdf.cell(140, 8, f"NAME :- {name}", 0, 0, 'L')
    pdf.cell(0, 8, f"RATE OF INTEREST:- {rate} %", 0, 1, 'R')
    pdf.ln(2)

    # --- 2. Table Column Widths (Total must be <= 277) ---
    # Width Calculation:
    # Month(26) + Op(26) + D1(22)+P1(22) + D2(22)+P2(22) + W(22) + Low(26) + Int(20) + Close(26) + Rem(30)
    # Total = 264mm (Fits comfortably within 277mm)
    w = {
        "mo": 26, "op": 26, 
        "d1": 22, "p1": 22, 
        "d2": 22, "p2": 22, 
        "wi": 22, "lo": 26, 
        "in": 20, "cl": 26, 
        "re": 30
    }

    pdf.set_font('Arial', 'B', 8)
    # Store starting X and Y
    x = pdf.get_x()
    y = pdf.get_y()
    
    # --- 3. Table Header (Merged Cells Logic) ---
    # Row Height = 12mm total. 
    # Single headers take full 12mm. Split headers take 6mm + 6mm.
    
    # 1. Month
    pdf.rect(x, y, w['mo'], 12)
    pdf.text(x+2, y+7, "Month")
    
    # 2. Opening Balance
    pdf.rect(x+w['mo'], y, w['op'], 12)
    pdf.text(x+w['mo']+2, y+7, "Opening Balance")
    
    # 3. Group: Deposit up to 15th (Dep + PFLR)
    grp1_x = x + w['mo'] + w['op']
    pdf.rect(grp1_x, y, w['d1']+w['p1'], 6) # Top box
    pdf.text(grp1_x+5, y+4, "Deposit up to 15th day")
    # Sub-columns
    pdf.rect(grp1_x, y+6, w['d1'], 6)
    pdf.text(grp1_x+2, y+10, "Deposit")
    pdf.rect(grp1_x+w['d1'], y+6, w['p1'], 6)
    pdf.text(grp1_x+w['d1']+2, y+10, "P.F.L.R")

    # 4. Group: Deposit 16th to Last (Dep + PFLR)
    grp2_x = grp1_x + w['d1'] + w['p1']
    pdf.rect(grp2_x, y, w['d2']+w['p2'], 6) # Top box
    pdf.text(grp2_x+2, y+4, "Deposit between 16th & last day")
    # Sub-columns
    pdf.rect(grp2_x, y+6, w['d2'], 6)
    pdf.text(grp2_x+2, y+10, "Deposit")
    pdf.rect(grp2_x+w['d2'], y+6, w['p2'], 6)
    pdf.text(grp2_x+w['d2']+2, y+10, "P.F.L.R")

    # 5. Withdrawal
    curr_x = grp2_x + w['d2'] + w['p2']
    pdf.rect(curr_x, y, w['wi'], 12)
    pdf.text(curr_x+2, y+7, "Withdrawal")

    # 6. Lowest Balance
    curr_x += w['wi']
    pdf.rect(curr_x, y, w['lo'], 12)
    pdf.text(curr_x+2, y+7, "Lowest Balance")

    # 7. Interest
    curr_x += w['lo']
    pdf.rect(curr_x, y, w['in'], 12)
    pdf.set_xy(curr_x, y) 
    # Multicell for Interest title to wrap if needed, or manual placement
    pdf.text(curr_x+1, y+5, "Interest for")
    pdf.text(curr_x+1, y+8, "the month")

    # 8. Closing Balance
    curr_x += w['in']
    pdf.rect(curr_x, y, w['cl'], 12)
    pdf.text(curr_x+2, y+7, "Closing Balance")

    # 9. Remarks
    curr_x += w['cl']
    pdf.rect(curr_x, y, w['re'], 12)
    pdf.text(curr_x+2, y+7, "Remarks")

    # Move cursor down after header
    pdf.set_xy(x, y + 12)

    # --- 4. Table Body ---
    pdf.set_font('Arial', '', 9) # Increased font size slightly for readability
    row_h = 8

    for index, row in df.iterrows():
        pdf.cell(w['mo'], row_h, str(row['Month']), 1, 0, 'L')
        pdf.cell(w['op'], row_h, f"{row['Opening Balance']:.2f}", 1, 0, 'R')
        pdf.cell(w['d1'], row_h, f"{row['Dep (<15th)']:.2f}", 1, 0, 'R')
        pdf.cell(w['p1'], row_h, f"{row['PFLR (<15th)']:.2f}", 1, 0, 'R')
        pdf.cell(w['d2'], row_h, f"{row['Dep (>15th)']:.2f}", 1, 0, 'R')
        pdf.cell(w['p2'], row_h, f"{row['PFLR (>15th)']:.2f}", 1, 0, 'R')
        pdf.cell(w['wi'], row_h, f"{row['Withdrawal']:.2f}", 1, 0, 'R')
        pdf.cell(w['lo'], row_h, f"{row['Lowest Balance']:.2f}", 1, 0, 'R')
        pdf.cell(w['in'], row_h, f"{row['Interest']:.2f}", 1, 0, 'R')
        pdf.cell(w['cl'], row_h, f"{row['Closing Balance']:.2f}", 1, 0, 'R')
        pdf.cell(w['re'], row_h, str(row['Remarks']), 1, 1, 'L')

    # --- 5. Total Row ---
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(w['mo'], row_h, "Total", 1, 0, 'C')
    pdf.cell(w['op'], row_h, "", 1, 0, 'C')
    pdf.cell(w['d1'], row_h, f"{totals['Dep (<15th)']:.2f}", 1, 0, 'R')
    pdf.cell(w['p1'], row_h, f"{totals['PFLR (<15th)']:.2f}", 1, 0, 'R')
    pdf.cell(w['d2'], row_h, f"{totals['Dep (>15th)']:.2f}", 1, 0, 'R')
    pdf.cell(w['p2'], row_h, f"{totals['PFLR (>15th)']:.2f}", 1, 0, 'R')
    pdf.cell(w['wi'], row_h, f"{totals['Withdrawal']:.2f}", 1, 0, 'R')
    pdf.cell(w['lo'], row_h, "", 1, 0, 'C')
    pdf.cell(w['in'], row_h, f"{totals['Interest']:.2f}", 1, 0, 'R')
    pdf.cell(w['cl'], row_h, "", 1, 0, 'C')
    pdf.cell(w['re'], row_h, "", 1, 1, 'C')

    # --- 6. Footer Summary (Bottom Left & Right) ---
    pdf.ln(5)
    
    # Calculate Final Total
    total_balance = final_bal + totals['Interest']

    # We use cells to align the Summary block
    pdf.set_font('Arial', '', 10)
    
    # Row 1: Principal
    pdf.cell(30, 6, "Principal", 0, 0)
    pdf.cell(30, 6, f"{final_bal:.2f}", 0, 1)
    
    # Row 2: Interest
    pdf.cell(30, 6, "Interest", 0, 0)
    pdf.cell(30, 6, f"{totals['Interest']:.2f}", 0, 1)
    
    # Row 3: Total (Bold)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(30, 6, "TOTAL", 0, 0)
    pdf.cell(30, 6, f"{total_balance:.2f}", 0, 0) # No line break here yet
    
    # Signature (Right aligned relative to page)
    # Move cursor to right side for signature
    pdf.set_x(230) 
    pdf.cell(40, 6, "Signature of HM", 0, 1, 'C')

    return pdf.output(dest='S').encode('latin-1')

# Button to Generate
if st.button("Generate PDF Report"):
    pdf_bytes = create_exact_pdf(result_df, school_name, employee_name, start_year, rate_input, totals, final_principal)
    st.download_button("📄 Download PDF", pdf_bytes, 'PF_Ledger_Final.pdf', 'application/pdf')
