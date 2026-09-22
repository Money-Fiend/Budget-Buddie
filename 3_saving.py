"""
Savings page - budgets and the savings projection.
Budget vs. actual (in the sidebar) + a forward savings projection.
"""

import pandas as pd
import streamlit as st

from data import get_transactions, MOVEMENT, init_budget_db, get_budget, save_budget

st.set_page_config(page_title="Savings", layout="wide")
st.title("Savings")

init_budget_db()

df = get_transactions()

if df.empty:
    st.error("Could not load transactions.")
    st.stop()

# Real spending for the budget comparison
spending_df = df[(df["Amount"] > 0) & (~df["Category"].isin(MOVEMENT))]

# ---- Budget vs. actual (in the sidebar) ----
with st.sidebar:
    st.subheader("Budget vs. Actual")
    st.write("Set your monthly budget for each category:")

    actual = spending_df.groupby("Category")["Amount"].sum()

    for category in actual.index:
        spent = actual[category]
        saved = get_budget(category)
        budget = st.number_input(
            f"{category} budget",
            min_value=0,
            value=int(saved),
            step=50,
            key=category,
        )
        save_budget(category, budget)

        if budget > 0:
            pct = spent / budget
        else:
            pct = 0
        st.progress(min(pct, 1.0))

        if spent > budget:
            st.error(f"{category}: ${spent:,.0f} / ${budget:,.0f} - OVER by ${spent - budget:,.0f}")
        else:
            st.success(f"{category}: ${spent:,.0f} / ${budget:,.0f} - ${budget - spent:,.0f} left")

# ---- Savings projection (main area) ----
st.subheader("Savings Projection")

monthly_savings = st.number_input(
    "How much can you save per month?",
    min_value=0,
    value=200,
    step=50,
)
months = st.slider("Project how many months ahead?", 1, 24, 12)

projection = []
running_total = 0
for month in range(1, months + 1):
    running_total += monthly_savings
    projection.append({"Month": month, "Projected Savings ($)": running_total})

projection_df = pd.DataFrame(projection)

st.metric(f"Projected savings in {months} months", f"${running_total:,.0f}")
st.line_chart(projection_df, x="Month", y="Projected Savings ($)")