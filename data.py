"""
data.py - shared data layer for Budget-Buddie.
Holds the Plaid connection, transaction fetching, and budget storage.
Every page imports what it needs from here, so the logic lives in ONE place.
"""

import os
import time
import sqlite3
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

import plaid
from plaid.api import plaid_api
from plaid.model.sandbox_public_token_create_request import SandboxPublicTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.exceptions import ApiException

import streamlit as st

# Categories that are money-movement, not real spending
MOVEMENT = ["Transfer", "Payment", "Uncategorized"]

# Load secret keys
load_dotenv()
CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
SECRET = os.getenv("PLAID_SECRET")


# ---------------------------------------------------------------
# Get transactions from Plaid (cached)
# ---------------------------------------------------------------
@st.cache_data(ttl=600)
def get_transactions():
    configuration = plaid.Configuration(
        host=plaid.Environment.Sandbox,
        api_key={"clientId": CLIENT_ID, "secret": SECRET},
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    pt_request = SandboxPublicTokenCreateRequest(
        institution_id="ins_109508",
        initial_products=[Products("transactions")],
    )
    public_token = client.sandbox_public_token_create(pt_request).public_token

    exchange = client.item_public_token_exchange(
        ItemPublicTokenExchangeRequest(public_token=public_token)
    )
    access_token = exchange.access_token

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
        return pd.DataFrame()

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
# Budget storage (SQLite)
# ---------------------------------------------------------------
DB_FILE = "budgets.db"

def init_budget_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS budgets (category TEXT PRIMARY KEY, amount REAL)"
    )
    conn.commit()
    conn.close()

def get_budget(category, default=500):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        "SELECT amount FROM budgets WHERE category = ?", (category,)
    ).fetchone()
    conn.close()
    return row[0] if row else default

def save_budget(category, amount):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO budgets (category, amount) VALUES (?, ?) "
        "ON CONFLICT(category) DO UPDATE SET amount = ?",
        (category, amount, amount),
    )
    conn.commit()
    conn.close()
    # ---------------------------------------------------------------
# Deposit check-off storage (SQLite)
# ---------------------------------------------------------------
def init_deposits_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS deposits (deposit_date TEXT PRIMARY KEY, done INTEGER)"
    )
    conn.commit()
    conn.close()

def is_deposit_done(deposit_date):
    conn = sqlite3.connect(DB_FILE)
    row = conn.execute(
        "SELECT done FROM deposits WHERE deposit_date = ?", (str(deposit_date),)
    ).fetchone()
    conn.close()
    return bool(row[0]) if row else False

def toggle_deposit(deposit_date):
    # Flip the done status: if done, make it not-done, and vice versa
    current = is_deposit_done(deposit_date)
    new_status = 0 if current else 1
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO deposits (deposit_date, done) VALUES (?, ?) "
        "ON CONFLICT(deposit_date) DO UPDATE SET done = ?",
        (str(deposit_date), new_status, new_status),
    )
    conn.commit()
    conn.close()