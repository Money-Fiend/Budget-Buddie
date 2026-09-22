"""
Trends page - spending over time.
Monthly spending trend line chart.
"""

import pandas as pd
import streamlit as st

from data import get_transactions, MOVEMENT

st.set_page_config(page_title="Trends", layout="wide")
st.title("Trends")

df = get_transactions()

if df.empty:
    st.error("Could not load transactions.")
    st.stop()

# ---- Monthly spending trend ----
st.subheader("Monthly Spending Trend")

trend_df = df[(df["Amount"] > 0) & (~df["Category"].isin(MOVEMENT))].copy()

if trend_df.empty:
    st.info("No spending data to chart.")
else:
    trend_df["Date"] = pd.to_datetime(trend_df["Date"])
    trend_df["Month"] = trend_df["Date"].dt.to_period("M").astype(str)
    monthly = trend_df.groupby("Month")["Amount"].sum().reset_index()
    monthly.columns = ["Month", "Total Spent ($)"]
    st.line_chart(monthly, x="Month", y="Total Spent ($)")
