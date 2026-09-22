"""
Goals page - savings goal tracker (steps 1-2: inputs + date generation).
User picks a cadence and amount; we generate the deposit dates.
The clickable calendar grid comes next session.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from data import init_deposits_db, is_deposit_done, toggle_deposit

st.set_page_config(page_title="Goals", layout="wide")
st.title("Savings Goal Tracker")
init_deposits_db()
# ---- Step 1: the setup inputs ----
st.subheader("Set up your savings plan")

cadence = st.selectbox(
    "How often will you deposit?",
    ["Daily", "Weekly", "Bi-weekly", "Monthly"],
)

amount = st.number_input(
    f"How much per {cadence.lower()[:-2] if cadence == 'Daily' else cadence.lower().rstrip('ly')}?",
    min_value=0,
    value=200,
    step=25,
)

start = st.date_input("Start date", value=date.today())

num_deposits = st.slider("How many deposits to plan?", 1, 52, 10)

# ---- Step 2: generate the deposit dates ----
# Pick the gap between deposits based on cadence
if cadence == "Daily":
    step_days = 1
elif cadence == "Weekly":
    step_days = 7
elif cadence == "Bi-weekly":
    step_days = 14
else:  # Monthly (approximate as 30 days for now)
    step_days = 30

# Build the list of deposit dates
deposits = []
running_total = 0
for i in range(num_deposits):
    deposit_date = start + timedelta(days=step_days * i)
    running_total += amount
    deposits.append({
        "Deposit #": i + 1,
        "Date": deposit_date,
        "Amount": amount,
        "Running Total": running_total,
    })

deposits_df = pd.DataFrame(deposits)

# ---- Show the plan ----
st.divider()
st.subheader("Your deposit schedule")
st.metric("Goal total", f"${running_total:,.0f}")

st.dataframe(
    deposits_df,
    use_container_width=True,
    column_config={
        "Amount": st.column_config.NumberColumn("Amount", format="$ %,.0f"),
        "Running Total": st.column_config.NumberColumn("Running Total", format="$ %,.0f"),
    },
) 
import calendar

st.divider()
st.subheader("Calendar View")

# Get the month structure for the start date's month
cal_weeks = calendar.monthcalendar(start.year, start.month)

# Show which month we're looking at
st.write(f"**{calendar.month_name[start.month]} {start.year}**")

# Draw the weekday headers (Mon-Sun) across the top
day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
header_cols = st.columns(7)
for i, day_name in enumerate(day_names):
    header_cols[i].write(f"**{day_name}**")

# Pull out the day-numbers that are deposit days (only for this month/year)
deposit_days = set()
for d in deposits_df["Date"]:
    if d.month == start.month and d.year == start.year:
        deposit_days.add(d.day)

# Draw each week as a row of 7 cells
 # We need the actual full dates (not just day numbers) for deposit days
deposit_dates_this_month = {}
for d in deposits_df["Date"]:
    if d.month == start.month and d.year == start.year:
        deposit_dates_this_month[d.day] = d

# Draw each week as a row of 7 cells
for week in cal_weeks:
    cols = st.columns(7)
    for i, day in enumerate(week):
        if day == 0:
            cols[i].write(" ")                        # blank padding
        elif day in deposit_dates_this_month:
            full_date = deposit_dates_this_month[day]
            done = is_deposit_done(full_date)
            label = f"{day} {'✅' if done else '⬜'}"
            # A button for this deposit day; clicking toggles it
            if cols[i].button(label, key=f"dep_{full_date}"):
                toggle_deposit(full_date)
                st.rerun()
        else:
            cols[i].write(str(day))                   # normal day
st.divider()
st.subheader("Your Progress")

# Count how many deposits are checked off
completed = 0
for d in deposits_df["Date"]:
    if is_deposit_done(d):
        completed += 1

total_deposits = len(deposits_df)
saved_so_far = completed * amount
goal_total = total_deposits * amount

# Show the numbers as tiles
col1, col2, col3 = st.columns(3)
col1.metric("Deposits Done", f"{completed} / {total_deposits}")
col2.metric("Saved So Far", f"${saved_so_far:,.0f}")
col3.metric("Goal", f"${goal_total:,.0f}")

# Progress bar toward the goal
if goal_total > 0:
    st.progress(saved_so_far / goal_total)
    st.write(f"You're **{saved_so_far / goal_total:.0%}** of the way to your goal!")