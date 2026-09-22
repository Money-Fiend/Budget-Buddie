"""
Budget-Buddie - Streamlit Dashboard
Connects to Plaid (Sandbox), pulls transactions, and displays them.
Reuses the exact connection flow proven in test_plaid.py.
"""

import os
import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.exceptions import ApiException

# ---------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------
st.set_page_config(page_title="Budget-Buddie", layout="wide")
st.title("Budget-Buddie")
st.caption("Your spending, pulled straight from your bank.")

# ---------------------------------------------------------------
# Load secret keys from .env
# ---------------------------------------------------------------
load_dotenv()
CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
SECRET = os.getenv("PLAID_SECRET")


# ---------------------------------------------------------------
# Connect to Plaid and pull transactions
# (cached so it doesn't re-run on every click)
# ---------------------------------------------------------------
@st.cache_data(ttl=600)
def get_transactions():
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={"clientId": CLIENT_ID, "secret": SECRET},
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    # Sandbox shortcut: create a fake connection and exchange for an access token
    pt_request = SandboxPublicTokenCreateRequest(
        institution_id="ins_109508",
        initial_products=[Products("transactions")],
    )
    public_token = client.sandbox_public_token_create(pt_request).public_token

    exchange = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    access_token = exchange.access_token

    # Pull the last 30 days, retrying while sandbox data generates
    tx_request = TransactionsGetRequest(
        access_token=access_token,
        start_date=(datetime.now() - timedelta(days=30)).date(),
        end_date=datetime.now().date(),
    )

    for attempt in range(10):
        try:
            transactions = client.transactions_get(tx_request).transactions
            break
        except ApiException as e:
            if "PRODUCT_NOT_READY" in str(e):
                time.sleep(3)
            else:
                raise
    else:
        return pd.DataFrame()  # gave up - return empty

    # Turn the transactions into a clean pandas DataFrame
    rows = []
    for t in transactions:
        rows.append({
            "Date": t.date,
            "Name": t.name,
            "Amount": t.amount,
            "Category": t.category[0] if t.category else "Uncategorized",
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------
# Run it
# ---------------------------------------------------------------
with st.spinner("Connecting to your bank..."):
    df = get_transactions()

if df.empty:
    st.error("Could not load transactions. Try refreshing.")
    st.stop()

# ---- Summary tiles ----
# In Plaid, positive amounts = money OUT (spending), negative = money IN.
spending = df[df["Amount"] > 0]["Amount"].sum()
income = -df[df["Amount"] < 0]["Amount"].sum()
net = income - spending

col1, col2, col3 = st.columns(3)
col1.metric("Total Spending", f"${spending:,.2f}")
col2.metric("Total Income", f"${income:,.2f}")
col3.metric("Net", f"${net:,.2f}")

st.divider()

# ---- Transaction table ----
st.subheader("Transactions (last 30 days)")
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Amount": st.column_config.NumberColumn("Amount", format="$ %,.2f", width="medium"),
    },
)