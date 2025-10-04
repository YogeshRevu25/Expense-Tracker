# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

import db

# Initialize DB
db.init_db()

st.set_page_config(page_title="Expense Tracker", layout="wide", initial_sidebar_state="expanded")
st.title("💸 Expense Tracker")

# --- Sidebar navigation ---
PAGES = ["Dashboard", "Add Expense", "View & Export", "Settings"]
page = st.sidebar.selectbox("Navigation", PAGES)

# Common helper
def money(x):
    return f"${x:,.2f}"

# Load data
df = db.fetch_expenses()

# ---------- ADD EXPENSE ----------
if page == "Add Expense":
    st.header("Add an expense")
    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns([2,1])
        with col1:
            amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            date_input = st.date_input("Date", value=date.today())
        categories = ["Housing", "Food", "Transportation", "Utilities", "Entertainment", "Healthcare", "Other"]
        category = st.selectbox("Category", categories)
        notes = st.text_area("Notes (optional)", height=70)
        submitted = st.form_submit_button("Add expense")
    if submitted:
        if amount <= 0:
            st.error("Enter an amount > 0")
        else:
            db.add_expense(amount=amount, category=category, date_str=date_input, notes=notes)
            st.success(f"Added expense: {money(amount)} — {category} on {date_input.isoformat()}")
            # reload df
            df = db.fetch_expenses()

# ---------- VIEW & EXPORT ----------
elif page == "View & Export":
    st.header("View and export expenses")
    if df.empty:
        st.info("No expenses recorded yet. Add one on the 'Add Expense' page.")
    else:
        # Filters
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        date_range = st.date_input("Date range", value=(min_date, max_date))
        start_dt, end_dt = date_range if isinstance(date_range, (list, tuple)) else (min_date, max_date)
        cats = sorted(df['category'].unique().tolist())
        selected_cats = st.multiselect("Categories", options=cats, default=cats)
        text_search = st.text_input("Search notes/description (contains)")

        filtered = df.copy()
        # convert start_dt/end_dt to timestamps
        filtered = filtered[(filtered['date'] >= pd.to_datetime(start_dt)) & (filtered['date'] <= pd.to_datetime(end_dt))]
        if selected_cats:
            filtered = filtered[filtered['category'].isin(selected_cats)]
        if text_search:
            filtered = filtered[filtered['notes'].astype(str).str.contains(text_search, case=False, na=False)]

        st.subheader(f"{len(filtered)} records found")
        st.dataframe(filtered.sort_values(by=['date','created_at'], ascending=[False, False]).reset_index(drop=True))

        # Export
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv, file_name="expenses_export.csv", mime="text/csv")

# ---------- DASHBOARD ----------
elif page == "Dashboard":
    st.header("Analytics Dashboard")
    if df.empty:
        st.info("No data — add some expenses to see analytics.")
    else:
        # Timeframe selection
        timeframe = st.selectbox("Timeframe", ["Last 30 days", "Last 90 days", "Year to date", "All time", "Custom range"])
        if timeframe == "Custom range":
            dr = st.date_input("Select range", value=(df['date'].min().date(), df['date'].max().date()))
            start = pd.to_datetime(dr[0])
            end = pd.to_datetime(dr[1])
        else:
            end = pd.to_datetime(df['date'].max())
            if timeframe == "Last 30 days":
                start = end - pd.Timedelta(days=30)
            elif timeframe == "Last 90 days":
                start = end - pd.Timedelta(days=90)
            elif timeframe == "Year to date":
                start = pd.Timestamp(year=end.year, month=1, day=1)
            else:
                start = pd.to_datetime(df['date'].min())

        df_filtered = df[(df['date'] >= start) & (df['date'] <= end)].copy()
        total = df_filtered['amount'].sum()
        last_30_days = df[(df['date'] >= (pd.to_datetime(end) - pd.Timedelta(days=30))) & (df['date'] <= end)]['amount'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total", money(total))
        col2.metric("Last 30 days", money(last_30_days))
        col3.metric("Records", f"{len(df_filtered)}")

        st.markdown("---")
        # Time series: Monthly and Weekly
        ts_col1, ts_col2 = st.columns([2,1])
        # Prepare monthly series
        monthly = df_filtered.set_index('date').resample('M')['amount'].sum().reset_index()
        if monthly.empty:
            st.info("Not enough data range to create monthly chart.")
        else:
            monthly['label'] = monthly['date'].dt.strftime('%Y-%m')
            fig_month = px.bar(monthly, x='label', y='amount', title="Monthly spending", labels={'label':'Month','amount':'Amount'})
            fig_month.update_layout(xaxis_tickangle=-45)
            ts_col1.plotly_chart(fig_month, use_container_width=True)

        # Weekly (last 12 weeks)
        weekly = df_filtered.set_index('date').resample('W-MON')['amount'].sum().reset_index()
        if not weekly.empty:
            weekly['label'] = weekly['date'].dt.strftime('%Y-%W')
            fig_week = px.bar(weekly.tail(12), x='label', y='amount', title="Weekly spending (last 12 weeks)", labels={'label':'Week','amount':'Amount'})
            ts_col2.plotly_chart(fig_week, use_container_width=True)

        st.markdown("---")
        # Category breakdown
        cat_df = df_filtered.groupby('category', as_index=False)['amount'].sum().sort_values('amount', ascending=False)
        c1, c2 = st.columns(2)
        if not cat_df.empty:
            fig_pie = px.pie(cat_df, names='category', values='amount', title="Spending by Category (pie)", hole=0.4)
            c1.plotly_chart(fig_pie, use_container_width=True)

            fig_bar = px.bar(cat_df, x='category', y='amount', title="Spending by Category (bar)")
            c2.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No category data available in the selected timeframe.")

# ---------- SETTINGS ----------
elif page == "Settings":
    st.header("Settings & Maintenance")
    st.write("This area is for optional tools and production tips.")
    if st.button("Add demo data (60 random rows)"):
        db.add_demo_data()
        st.success("Demo data added. Refresh the app to see it.")
    st.markdown("""
    **Production notes**
    - For a real deployment use a networked DB (Postgres/Supabase) — SQLite is file-based and ephemeral on some hosts.
    - Add authentication (Streamlit-Auth or OAuth) to restrict access.
    - Back up the `data/expenses.db` file regularly.
    """)
