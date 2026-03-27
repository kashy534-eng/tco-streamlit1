import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import io

# -----------------------------
# Constants (simplified policy)
# -----------------------------
DAYS_PER_MONTH = 30
NON_JIT_INVENTORY_MONTHS = 2   # 2 months inventory for Non-JIT
NON_JIT_FINANCING_DAYS = 60    # Pay 2 months before delivery

# -----------------------------
# Core calculation
# -----------------------------
def calculate_supplier(
    supplier_name,
    spud_date,
    cadence_months,
    planning_years,
    wells_per_year,
    wacc,
    holding_rate,
    prod_lt,
    delivery_lt,
    price_per_ft,
    feet_per_well,
    mode,  # "JIT" or "Non-JIT"
):
    total_wells = wells_per_year * planning_years

    # Mode logic
    if mode == "JIT":
        inventory_months = 0
        financing_days = 0
    else:
        inventory_months = NON_JIT_INVENTORY_MONTHS
        financing_days = NON_JIT_FINANCING_DAYS

    inventory_days = inventory_months * DAYS_PER_MONTH

    # Ordering logic (program-level)
    required_delivery_date = spud_date - timedelta(days=inventory_days)
    total_lt_days = (prod_lt + delivery_lt) * DAYS_PER_MONTH
    latest_order_date = required_delivery_date - timedelta(days=total_lt_days)

    cadence_days = cadence_months * DAYS_PER_MONTH
    cadence_anchor = spud_date.replace(month=1, day=1)
    steps = math.floor((latest_order_date - cadence_anchor).days / cadence_days)
    order_date = cadence_anchor + timedelta(days=steps * cadence_days)

    delivery_date = order_date + timedelta(days=(prod_lt + delivery_lt) * DAYS_PER_MONTH)

    # Purchase cost
    purchase_cost = price_per_ft * feet_per_well * total_wells

    # Inventory holding cost
    if mode == "JIT":
        avg_inventory_value_program = 0
        holding_cost = 0
    else:
        avg_inventory_value_per_well = 0.5 * price_per_ft * feet_per_well
        avg_inventory_value_program = avg_inventory_value_per_well * wells_per_year
        holding_cost = avg_inventory_value_program * holding_rate * planning_years

    # Working capital cost
    if mode == "JIT":
        wc_cost = 0
    else:
        wc_cost = (
            avg_inventory_value_program
            * wacc
            * planning_years
            * (financing_days / 365)
        )

    total_cost = purchase_cost + holding_cost + wc_cost

    return {
        "Supplier": supplier_name,
        "Mode": mode,
        "Total Wells": total_wells,
        "Order Date": order_date,
        "Delivery Date": delivery_date,
        "Inventory Months": inventory_months,
        "Financing Days": financing_days,
        "Purchase Cost ($)": round(purchase_cost, 0),
        "Inventory Holding Cost ($)": round(holding_cost, 0),
        "WC Cost ($)": round(wc_cost, 0),
        "Total Cost of Ownership ($)": round(total_cost, 0),
    }

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("OCTG Supplier TCO Model")
st.caption("Simplified JIT vs Non‑JIT | Program‑Level Cost Comparison")

st.markdown("### Global Inputs")
col1, col2, col3 = st.columns(3)

with col1:
    wacc = st.number_input("WACC", value=0.20, step=0.01)
    holding_rate = st.number_input("Inventory Holding Cost Rate", value=0.02, step=0.005)

with col2:
    spud_date = st.date_input("Well Spud Date", value=datetime(2026, 6, 1))
    cadence = st.number_input("Order Cadence (months)", value=6)

with col3:
    years = st.number_input("Planning Years", value=5)
    wells_per_year = st.number_input("Wells per Year", value=9)

st.divider()

st.markdown("### Supplier A")
A_prod = st.number_input("A: Production Lead Time (months)", value=5)
A_del = st.number_input("A: Delivery Lead Time (months)", value=1)
A_price = st.number_input("A: Unit Price ($/ft)", value=85)
A_ft = st.number_input("A: Feet per Well", value=1500)
A_mode = st.selectbox("A: Supply Mode", ["JIT", "Non-JIT"], index=1)

st.divider()

st.markdown("### Supplier B")
B_prod = st.number_input("B: Production Lead Time (months)", value=7)
B_del = st.number_input("B: Delivery Lead Time (months)", value=1)
B_price = st.number_input("B: Unit Price ($/ft)", value=82)
B_ft = st.number_input("B: Feet per Well", value=1500)
B_mode = st.selectbox("B: Supply Mode", ["JIT", "Non-JIT"], index=0)

# -----------------------------
# Run model
# -----------------------------
A = calculate_supplier(
    "Supplier A",
    spud_date, cadence, years, wells_per_year,
    wacc, holding_rate,
    A_prod, A_del, A_price, A_ft, A_mode
)

B = calculate_supplier(
    "Supplier B",
    spud_date, cadence, years, wells_per_year,
    wacc, holding_rate,
    B_prod, B_del, B_price, B_ft, B_mode
)

df = pd.DataFrame([A, B])

st.markdown("## Results")
st.dataframe(df, use_container_width=True)

# -----------------------------
# Excel Download (FIXED)
# -----------------------------
buffer = io.BytesIO()
df.to_excel(buffer, index=False)
buffer.seek(0)

st.download_button(
    label="Download Excel",
    data=buffer,
    file_name="OCTG_TCO_Streamlit.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
