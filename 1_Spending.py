"""
Spending page - where the money goes.
Donut chart of spending by category + a separate transfers/payments chart.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from data import get_transactions, MOVEMENT

st.set_page_config(page_title="Spending", layout="wide")
st.title("Spending")

# Load the shared transaction data
df = get_transactions()

if df.empty:
    st.error("Could not load transactions.")
    st.stop()

# ---- Spending by category (donut) ----
st.subheader("Spending by Category")

spending_df = df[(df["Amount"] > 0) & (~df["Category"].isin(MOVEMENT))]

if spending_df.empty:
    st.info("No spending to show.")
else:
    by_category = spending_df.groupby("Category")["Amount"].sum().reset_index()
    by_category.columns = ["Category", "Total Spent"]
    fig = px.pie(
        by_category,
        names="Category",
        values="Total Spent",
        hole=0.5,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---- Transfers & payments (money movement) ----
st.subheader("Transfers & Payments")
st.caption("Money moving between accounts - not counted as spending above.")

movement_df = df[(df["Amount"] > 0) & (df["Category"].isin(MOVEMENT))]

if movement_df.empty:
    st.info("No transfers or payments to show.")
else:
    by_movement = movement_df.groupby("Category")["Amount"].sum().sort_values(ascending=False).reset_index()
    by_movement.columns = ["Category", "Total ($)"]
    st.bar_chart(by_movement, x="Category", y="Total ($)")