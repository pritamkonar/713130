import streamlit as st
import pandas as pd
from fpdf import FPDF
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="PF Interest Calculation", layout="wide")

# --- CSS for Tables to match Excel look ---
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
</style>
""", unsafe_allow_html=True)

st.title("📄 PF Interest Calculation Sheet")

# --- Inputs: Header Info (Matching Excel Header) ---
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
        "Dep_Before_15": [0.0] * 12,    # Excel: Deposit up to 15th -> Deposit
        "PFLR_Before_15": [0.0] * 12,   # Excel: Deposit up to 15th -> P.F.L.R
        "Dep_After_15": [0.0] * 12,     # Excel: Deposit 16th & last -> Deposit
        "PFLR_After_15": [0.0] * 12,    # Excel: Deposit 16th & last -> P.F.L.R
        "Withdrawal": [0.0] * 12,
        "Remarks": [""] * 12
    }
    st.session_state.input_data = pd.DataFrame(data)
else:
    # Update Month labels if Year changes
    st.session_state.input_data["Month"] = months_list

st.subheader("Monthly Data Entry")
st.info("Enter amounts below. Logic: Interest is calculated on Lowest Balance (Opening + Deposits before 15th - Withdrawals).")

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

# --- Calculation Engine (LOGIC UNCHANGED) ---
def calculate_ledger(opening_bal, input_df, rate):
    results = []
    current_bal = opening_bal
    total_interest = 0.0

    # For column sums
    sum_dep_b = 0
    sum_pflr_b = 0
    sum_dep_a = 0
    sum_pflr_a = 0
    sum_with = 0

    for index, row in input_df.iterrows():
        month = row['Month']
        dep_before = row['Dep_Before_15']
        pflr_before = row['PFLR_Before_15']
        dep_after = row['Dep_After_15']
        pflr_after = row['PFLR_After_15']
        withdrawal = row['Withdrawal']
        remarks = row['Remarks']

        # Update Sums
        sum_dep_b += dep_before
        sum_pflr_b += pflr_before
        sum_dep_a += dep_after
        sum_pflr_a += pflr_after
        sum_with += withdrawal

        # Lowest Balance Calculation
        effective_deposit_for_interest = dep_before + pflr_before
        lowest_bal_calc = current_bal + effective_deposit_for_interest - withdrawal
        lowest_bal = max(0, lowest_bal_calc)

        # --- LOGIC: Interest Truncation ---
        raw_interest = (lowest_bal * rate) / 1200
        # Truncate to 2 decimal places (No Rounding Up)
        interest = int(raw_interest * 100) / 100.0

        # Closing Balance
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
    
    # Create DataFrame
    df_res = pd.DataFrame(results)
    
    # Store totals for footer
    totals = {
        "Dep (<15th)": sum_dep_b,
        "PFLR (<15th)": sum_pflr_b,
        "Dep (>15th)": sum_dep_a,
        "PFLR (>15th)": sum_pflr_a,
        "Withdrawal": sum_with,
        "Interest": total_interest
    }

    return df_res, totals, current_bal

# Perform Calculation
result_df, totals, final_principal = calculate_ledger(opening_balance_input, edited_df, rate_input)

# --- Display Results (Formatted to Match Excel) ---
st.divider()
st.subheader(f"Interest Calculation for the Year {start_year}-{start_year+1}")

# Prepare Display Dataframe with Total Row
display_df = result_df.copy()

# Rename columns to match Excel Visuals closely
display_df.columns = [
    "Month", "Opening Bal", 
    "Deposit (Up to 15)", "PFLR (Up to 15)", 
    "Deposit (16-End)", "PFLR (16-End)", 
    "Withdrawal", "Lowest Bal", "Interest", "Closing Bal", "Remarks"
]

# Add Total Row
total_row = pd.DataFrame([{
    "Month": "TOTAL",
    "Opening Bal": None,
    "Deposit (Up to 15)": totals["Dep (<15th)"],
    "PFLR (Up to 15)": totals["PFLR (<15th)"],
    "Deposit (16-End)": totals["Dep (>15th)"],
    "PFLR (16-End)": totals["PFLR (>15th)"],
    "Withdrawal": totals["Withdrawal"],
    "Lowest Bal": None,
    "Interest": totals["Interest"],
    "Closing Bal": None,
    "Remarks": ""
}])

display_df = pd.concat([display_df, total_row], ignore_index=True)

st.dataframe(
    display_df,
    column_config={
        "Opening Bal": st.column_config.NumberColumn(format="%.2f"),
        "Deposit (Up to 15)": st.column_config.NumberColumn(format="%.2f"),
        "PFLR (Up to 15)": st.column_config.NumberColumn(format="%.2f"),
        "Deposit (16-End)": st.column_config.NumberColumn(format="%.2f"),
        "PFLR (16-End)": st.column_config.NumberColumn(format="%.2f"),
        "Withdrawal": st.column_config.NumberColumn(format="%.2f"),
        "Lowest Bal": st.column_config.NumberColumn(format="%.2f"),
        "Interest": st.column_config.NumberColumn(format="%.2f"),
        "Closing Bal": st.column_config.NumberColumn(format="%.2f"),
    },
    use_container_width=True,
    hide_index=True
)

# --- Footer Summary (Matches Excel Bottom Left) ---
st.write("### Summary")
col1, col2 = st.columns([1, 2])

final_total_balance = final_principal + totals['Interest']

with col1:
    summary_data = {
        "Description": ["Principal", "Interest", "TOTAL"],
        "Amount": [final_principal, totals['Interest'], final_total_balance]
    }
    st.table(pd.DataFrame(summary_data).style.format({"Amount": "₹ {:.2f}"}))

# --- PDF Export (Visual Match to Template) ---
class PDF(FPDF):
    def header(self):
        pass # We will do a custom header in the generation function

def create_pdf(df, school, name, year, rate, totals, final_bal):
    pdf = PDF(orientation='L', unit='mm', format='A4') 
    pdf.add_page()
    
    # --- Excel Header Simulation ---
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, f"SCHOOL NAME :- {school}", 0, 1, 'C')
    pdf.cell(0, 8, f"INTEREST CALCULATION OF PROVIDENT FUND ACCOUNT FOR THE YEAR - {year}-{year+1}", 0, 1, 'C')
    
    pdf.set_font('Arial', 'B', 10)
    # Name and Rate on same line
    pdf.cell(150, 8, f"NAME :- {name}", 0, 0, 'L')
    pdf.cell(0, 8, f"RATE OF INTEREST:- {rate} %", 0, 1, 'R')
    pdf.ln(2)

    # --- Table Header ---
    pdf.set_font('Arial', 'B', 7)
    
    # Widths
    w_mo = 18
    w_op = 22
    w_dep = 22
    w_rem = 20
    w_int = 15
    
    # Top Header Row (Merged cells simulation)
    x = pdf.get_x()
    y = pdf.get_y()
    
    # Standard single height headers
    pdf.rect(x, y, w_mo, 10)
    pdf.text(x+2, y+6, "Month")
    
    pdf.rect(x+w_mo, y, w_op, 10)
    pdf.text(x+w_mo+2, y+6, "Opening Bal")
    
    # Merged Header: Deposit up to 15th
    pdf.rect(x+w_mo+w_op, y, w_dep*2, 5)
    pdf.text(x+w_mo+w_op+8, y+3.5, "Deposit up to 15th day")
    pdf.rect(x+w_mo+w_op, y+5, w_dep, 5) # Sub col 1
    pdf.text(x+w_mo+w_op+5, y+8.5, "Deposit")
    pdf.rect(x+w_mo+w_op+w_dep, y+5, w_dep, 5) # Sub col 2
    pdf.text(x+w_mo+w_op+w_dep+5, y+8.5, "P.F.L.R")

    # Merged Header: Deposit 16th to last
    start_16 = x+w_mo+w_op+(w_dep*2)
    pdf.rect(start_16, y, w_dep*2, 5)
    pdf.text(start_16+5, y+3.5, "Deposit 16th & last day")
    pdf.rect(start_16, y+5, w_dep, 5)
    pdf.text(start_16+5, y+8.5, "Deposit")
    pdf.rect(start_16+w_dep, y+5, w_dep, 5)
    pdf.text(start_16+w_dep+5, y+8.5, "P.F.L.R")

    # Other columns
    cur_x = start_16 + (w_dep*2)
    pdf.rect(cur_x, y, w_dep, 10)
    pdf.text(cur_x+2, y+6, "Withdrawal")
    
    cur_x += w_dep
    pdf.rect(cur_x, y, w_op, 10)
    pdf.text(cur_x+2, y+6, "Lowest Bal")
    
    cur_x += w_op
    pdf.rect(cur_x, y, w_int, 10)
    pdf.text(cur_x+1, y+6, "Interest")
    
    cur_x += w_int
    pdf.rect(cur_x, y, w_op, 10)
    pdf.text(cur_x+2, y+6, "Closing Bal")

    cur_x += w_op
    pdf.rect(cur_x, y, w_rem, 10)
    pdf.text(cur_x+2, y+6, "Remarks")
    
    pdf.ln(10)

    # --- Table Rows ---
    pdf.set_font('Arial', '', 8)
    
    def draw_row(row_data, is_bold=False):
        if is_bold: pdf.set_font('Arial', 'B', 8)
        else: pdf.set_font('Arial', '', 8)
        
        pdf.cell(w_mo, 8, str(row_data[0]), 1)
        pdf.cell(w_op, 8, str(row_data[1]), 1)
        pdf.cell(w_dep, 8, str(row_data[2]), 1) # Dep <15
        pdf.cell(w_dep, 8, str(row_data[3]), 1) # PFLR <15
        pdf.cell(w_dep, 8, str(row_data[4]), 1) # Dep >15
        pdf.cell(w_dep, 8, str(row_data[5]), 1) # PFLR >15
        pdf.cell(w_dep, 8, str(row_data[6]), 1) # With
        pdf.cell(w_op, 8, str(row_data[7]), 1) # Low
        pdf.cell(w_int, 8, str(row_data[8]), 1) # Int
        pdf.cell(w_op, 8, str(row_data[9]), 1) # Close
        pdf.cell(w_rem, 8, str(row_data[10]), 1) # Rem
        pdf.ln()

    # Data Rows
    for index, row in df.iterrows():
        r_d = [
            row['Month'],
            f"{row['Opening Balance']:.2f}",
            f"{row['Dep (<15th)']:.2f}",
            f"{row['PFLR (<15th)']:.2f}",
            f"{row['Dep (>15th)']:.2f}",
            f"{row['PFLR (>15th)']:.2f}",
            f"{row['Withdrawal']:.2f}",
            f"{row['Lowest Balance']:.2f}",
            f"{row['Interest']:.2f}",
            f"{row['Closing Balance']:.2f}",
            row['Remarks']
        ]
        draw_row(r_d)

    # Total Row
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(w_mo, 8, "Total", 1)
    pdf.cell(w_op, 8, "", 1)
    pdf.cell(w_dep, 8, f"{totals['Dep (<15th)']:.2f}", 1)
    pdf.cell(w_dep, 8, f"{totals['PFLR (<15th)']:.2f}", 1)
    pdf.cell(w_dep, 8, f"{totals['Dep (>15th)']:.2f}", 1)
    pdf.cell(w_dep, 8, f"{totals['PFLR (>15th)']:.2f}", 1)
    pdf.cell(w_dep, 8, f"{totals['Withdrawal']:.2f}", 1)
    pdf.cell(w_op, 8, "", 1)
    pdf.cell(w_int, 8, f"{totals['Interest']:.2f}", 1)
    pdf.cell(w_op, 8, "", 1)
    pdf.cell(w_rem, 8, "", 1)
    pdf.ln(12)

    # --- Footer Summary ---
    pdf.set_font('Arial', '', 10)
    pdf.cell(40, 6, "Principal", 0, 0)
    pdf.cell(40, 6, f": {final_bal:.2f}", 0, 1)
    
    pdf.cell(40, 6, "Interest", 0, 0)
    pdf.cell(40, 6, f": {totals['Interest']:.2f}", 0, 1)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, 6, "TOTAL", 0, 0)
    pdf.cell(40, 6, f": {(final_bal + totals['Interest']):.2f}", 0, 1)
    
    pdf.ln(10)
    pdf.cell(0, 10, "Signature of HM", 0, 1, 'L')

    return pdf.output(dest='S').encode('latin-1')

pdf_bytes = create_pdf(result_df, school_name, employee_name, start_year, rate_input, totals, final_principal)
st.download_button("📄 Download PDF Report", pdf_bytes, 'PF_Statement_Official.pdf', 'application/pdf')
