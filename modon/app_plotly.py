from __future__ import annotations

import logging
import sys

import plotly.express as px
import polars as pl
import streamlit as st

from src.aggregation import (
    enrich_rents,
    enrich_transactions,
    make_project_dimension,
)
from src.cleaning import prepare_lands, prepare_projects, prepare_rents, prepare_transactions
from src.escape_csv_newlines import preprocess_raw_csvs
from src.loading import get_df_by_prefix, load_csvs_to_polars

logging.basicConfig(level=logging.WARNING)


def fmt_m(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value / 1_000_000:,.1f} M"


st.set_page_config(page_title="Modon – Market Analysis (Plotly)", layout="wide")

PREPROCESS_RAW = "--preprocess-raw" in sys.argv[1:]
if PREPROCESS_RAW:
    processed_files = preprocess_raw_csvs()
    st.toast(f"Pre-processed {len(processed_files)} raw CSV files.")


@st.cache_data
def load_data():
    dfs = load_csvs_to_polars("data")
    projects = prepare_projects(get_df_by_prefix(dfs, "projects-"))
    lands = prepare_lands(get_df_by_prefix(dfs, "lands-"))
    transactions = prepare_transactions(get_df_by_prefix(dfs, "transactions-"))
    rents = prepare_rents(get_df_by_prefix(dfs, "rents-"))
    dim = make_project_dimension(projects, lands)
    tx = enrich_transactions(transactions, dim)
    rn = enrich_rents(rents, dim)
    return projects, lands, tx, rn


projects, lands, transactions, rents = load_data()

# ── Pre-compute aggregates ────────────────────────────────────────────────────

developer_sales = (
    transactions.filter(pl.col("DEVELOPER_EN").is_not_null())
    .group_by("DEVELOPER_EN")
    .agg(
        pl.len().alias("sales_count"),
        pl.col("TRANS_VALUE").sum().alias("sales_value"),
        pl.col("PRICE_PER_SQM").median().alias("median_price_sqm"),
    )
)

developer_rents = (
    rents.filter(pl.col("DEVELOPER_EN").is_not_null())
    .group_by("DEVELOPER_EN")
    .agg(
        pl.len().alias("rent_count"),
        pl.col("ANNUAL_AMOUNT").sum().alias("rent_value"),
        pl.col("RENT_PER_SQM").median().alias("median_rent_sqm"),
    )
)

developer_projects = (
    projects.group_by("DEVELOPER_EN")
    .agg(
        pl.len().alias("total_projects"),
        (pl.col("PROJECT_STATUS") == "ACTIVE").sum().alias("active"),
        (pl.col("PROJECT_STATUS") == "PENDING").sum().alias("pending"),
        pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).sum().alias("portfolio_value"),
        (pl.col("CNT_UNIT").cast(pl.Float64, strict=False)).sum().alias("total_units"),
    )
)

leaderboard = (
    developer_projects.join(developer_sales, on="DEVELOPER_EN", how="left")
    .join(developer_rents, on="DEVELOPER_EN", how="left")
    .with_columns(
        [
            pl.col("sales_count").fill_null(0),
            pl.col("rent_count").fill_null(0),
            (pl.col("median_rent_sqm") / pl.col("median_price_sqm")).alias("gross_yield"),
        ]
    )
    .sort("total_projects", descending=True)
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

developer_names = sorted(leaderboard["DEVELOPER_EN"].drop_nulls().to_list())
selected_developer = st.sidebar.selectbox("Filter by developer", ["— All —"] + developer_names)

if selected_developer == "— All —":
    f_projects = projects
    f_transactions = transactions
    f_rents = rents
else:
    f_projects = projects.filter(pl.col("DEVELOPER_EN") == selected_developer)
    f_transactions = transactions.filter(pl.col("DEVELOPER_EN") == selected_developer)
    f_rents = rents.filter(pl.col("DEVELOPER_EN") == selected_developer)

# ── Page ──────────────────────────────────────────────────────────────────────

st.title("Modon – Market Analysis")

tab_overview, tab_dev, tab_tx, tab_prop, tab_rent, tab_supply = st.tabs(
    ["Market Overview", "Developers", "Transactions", "Property Types", "Rent Market", "Land & Supply"]
)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 – Market Overview  (always unfiltered)
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    st.subheader("Market Pulse")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Projects", f"{projects.height:,}")
    k2.metric("Active Projects", f"{(projects['PROJECT_STATUS'] == 'ACTIVE').sum():,}")
    k3.metric("Units in Pipeline", f"{int(projects['CNT_UNIT'].cast(pl.Float64, strict=False).sum()):,}")
    k4.metric("Total Sales Value (M AED)", fmt_m(transactions['TRANS_VALUE'].sum()))
    k5.metric("Median Price/sqm (AED)", f"{transactions['PRICE_PER_SQM'].median():,.0f}")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        monthly_sales = (
            transactions.group_by("MONTH")
            .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("Sales Value (M AED)"))
            .sort("MONTH")
            .to_pandas()
        )
        fig = px.line(monthly_sales, x="MONTH", y="Sales Value (M AED)",
                      title="Monthly Sales Volume (M AED) – All Market",
                      labels={"MONTH": "Month"})
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        monthly_count = (
            transactions.group_by("MONTH")
            .agg(pl.len().alias("Transactions"))
            .sort("MONTH")
            .to_pandas()
        )
        fig = px.line(monthly_count, x="MONTH", y="Transactions",
                      title="Monthly Transaction Count – All Market",
                      labels={"MONTH": "Month"})
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    if "AREA_EN" in transactions.columns:
        by_area = (
            transactions.filter(pl.col("AREA_EN").is_not_null())
            .group_by("AREA_EN")
            .agg(
                pl.col("PRICE_PER_SQM").median().alias("Median Price/sqm"),
                pl.len().alias("Transactions"),
            )
            .filter(pl.col("Transactions") >= 10)
            .sort("Median Price/sqm", descending=True)
            .head(20)
            .to_pandas()
        )
        fig = px.bar(by_area, x="AREA_EN", y="Median Price/sqm",
                     title="Median Price/sqm by Area (top 20, min 10 transactions)",
                     labels={"AREA_EN": "Area"})
        fig.update_layout(xaxis_tickangle=-40)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        status_counts = (
            projects.group_by("PROJECT_STATUS")
            .agg(pl.len().alias("Count"))
            .to_pandas()
        )
        fig = px.bar(status_counts, x="PROJECT_STATUS", y="Count",
                     title="Active vs Pending Projects",
                     labels={"PROJECT_STATUS": "Status"}, color="PROJECT_STATUS")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        if "AREA_EN" in transactions.columns:
            top_areas = (
                transactions.filter(pl.col("AREA_EN").is_not_null())
                .group_by("AREA_EN")
                .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("Sales Value (M AED)"))
                .sort("Sales Value (M AED)", descending=True)
                .head(10)
                .to_pandas()
            )
            fig = px.bar(top_areas, x="AREA_EN", y="Sales Value (M AED)",
                         title="Top 10 Areas by Transaction Volume",
                         labels={"AREA_EN": "Area"})
            fig.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 – Developers
# ══════════════════════════════════════════════════════════════════════════════
with tab_dev:
    if selected_developer == "— All —":
        st.subheader("Developer Leaderboard")
        display = leaderboard.select([
            "DEVELOPER_EN",
            "total_projects", "active", "pending",
            "portfolio_value", "total_units",
            "sales_count", "sales_value",
            "rent_count", "rent_value",
            "median_price_sqm", "median_rent_sqm", "gross_yield",
        ]).rename({
            "DEVELOPER_EN": "Developer",
            "total_projects": "Projects",
            "active": "Active",
            "pending": "Pending",
            "portfolio_value": "Portfolio Value (M AED)",
            "total_units": "Units",
            "sales_count": "Sales Txns",
            "sales_value": "Sales Value (M AED)",
            "rent_count": "Rent Contracts",
            "rent_value": "Annual Rent (M AED)",
            "median_price_sqm": "Median Price/sqm",
            "median_rent_sqm": "Median Rent/sqm",
            "gross_yield": "Gross Yield",
        })
        st.dataframe(display.to_pandas(), use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            top15 = leaderboard.head(15).select(["DEVELOPER_EN", "total_projects"]).to_pandas()
            fig = px.bar(top15, x="DEVELOPER_EN", y="total_projects",
                         title="Top 15 by Total Projects",
                         labels={"DEVELOPER_EN": "Developer", "total_projects": "Projects"})
            fig.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            top15_sales = (
                leaderboard.sort("sales_value", descending=True)
                .head(15)
                .with_columns((pl.col("sales_value") / 1_000_000).alias("Sales Value (M AED)"))
                .select(["DEVELOPER_EN", "Sales Value (M AED)"])
                .to_pandas()
            )
            fig = px.bar(top15_sales, x="DEVELOPER_EN", y="Sales Value (M AED)",
                         title="Top 15 by Sales Value",
                         labels={"DEVELOPER_EN": "Developer"})
            fig.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

    else:
        dev_row = leaderboard.filter(pl.col("DEVELOPER_EN") == selected_developer)
        dev_projects = f_projects.sort("START_DATE", descending=True)

        st.subheader(selected_developer)
        kpi = dev_row.row(0, named=True) if dev_row.height > 0 else {}
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Projects", int(kpi.get("total_projects") or 0))
        c2.metric("Active", int(kpi.get("active") or 0))
        c3.metric("Pending", int(kpi.get("pending") or 0))
        c4.metric("Sales Transactions", int(kpi.get("sales_count") or 0))
        c5.metric("Gross Yield", f"{kpi['gross_yield']:.1%}" if kpi.get("gross_yield") else "—")

        st.divider()
        st.subheader("Projects")
        proj_display = dev_projects.select([
            "PROJECT_EN", "PROJECT_STATUS", "PERCENT_COMPLETED",
            "START_DATE", "END_DATE", "PROJECT_VALUE", "CNT_UNIT",
        ]).rename({
            "PROJECT_EN": "Project", "PROJECT_STATUS": "Status",
            "PERCENT_COMPLETED": "% Complete", "START_DATE": "Start",
            "END_DATE": "End", "PROJECT_VALUE": "Value (AED)", "CNT_UNIT": "Units",
        })
        st.dataframe(proj_display.to_pandas(), use_container_width=True, hide_index=True)

        project_names = dev_projects["PROJECT_EN"].drop_nulls().to_list()
        if project_names:
            st.divider()
            selected_project = st.selectbox("Drill into project", ["— Select —"] + project_names)
            if selected_project != "— Select —":
                st.subheader(f"Project: {selected_project}")
                proj_tx = f_transactions.filter(pl.col("PROJECT_EN") == selected_project)
                proj_rn = f_rents.filter(pl.col("PROJECT_EN") == selected_project)

                col_a, col_b = st.columns(2)
                with col_a:
                    if proj_tx.height > 0:
                        df = (
                            proj_tx.group_by("MONTH")
                            .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("Sales Value (M AED)"))
                            .sort("MONTH")
                            .to_pandas()
                        )
                        fig = px.line(df, x="MONTH", y="Sales Value (M AED)",
                                      title="Monthly Sales Volume (M AED)",
                                      labels={"MONTH": "Month"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No sales transactions found for this project.")
                with col_b:
                    if proj_tx.height > 0:
                        df = (
                            proj_tx.group_by("MONTH")
                            .agg(pl.col("PRICE_PER_SQM").median().alias("Median AED/sqm"))
                            .sort("MONTH")
                            .to_pandas()
                        )
                        fig = px.line(df, x="MONTH", y="Median AED/sqm",
                                      title="Median Price per sqm over time",
                                      labels={"MONTH": "Month"})
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No price data available.")

                if proj_tx.height > 0 and "PROP_TYPE_EN" in proj_tx.columns:
                    st.markdown("**Property Type Breakdown (Sales)**")
                    st.dataframe(
                        proj_tx.group_by("PROP_TYPE_EN")
                        .agg(pl.len().alias("Count"), (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("Value (M AED)"))
                        .sort("Count", descending=True).to_pandas(),
                        use_container_width=True, hide_index=True,
                    )

                if proj_rn.height > 0:
                    df = (
                        proj_rn.group_by("MONTH")
                        .agg((pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("Annual Rent (M AED)"))
                        .sort("MONTH")
                        .to_pandas()
                    )
                    fig = px.line(df, x="MONTH", y="Annual Rent (M AED)",
                                  title="Annual Rent Contracts",
                                  labels={"MONTH": "Month"})
                    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 – Transactions
# ══════════════════════════════════════════════════════════════════════════════
with tab_tx:
    st.subheader("Sales Transactions Overview")

    # ── Tab filters ──────────────────────────────────────────────────────────
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        tx_offplan_vals = ["All"] + sorted(
            f_transactions["IS_OFFPLAN_EN"].drop_nulls().unique().to_list()
        ) if "IS_OFFPLAN_EN" in f_transactions.columns else ["All"]
        tx_offplan = st.selectbox("Off-plan", tx_offplan_vals, key="tx_offplan")
    with f_col2:
        tx_prop_types = f_transactions["PROP_TYPE_EN"].drop_nulls().unique().sort().to_list() if "PROP_TYPE_EN" in f_transactions.columns else []
        tx_sel_types = st.multiselect("Property type", tx_prop_types, key="tx_prop_type")
    with f_col3:
        tx_area_vals = sorted(f_transactions["AREA_EN"].drop_nulls().unique().to_list()) if "AREA_EN" in f_transactions.columns else []
        tx_sel_areas = st.multiselect("Area", tx_area_vals, key="tx_area")
    t = f_transactions
    if tx_offplan != "All":
        t = t.filter(pl.col("IS_OFFPLAN_EN") == tx_offplan)
    if tx_sel_types:
        t = t.filter(pl.col("PROP_TYPE_EN").is_in(tx_sel_types))
    if tx_sel_areas:
        t = t.filter(pl.col("AREA_EN").is_in(tx_sel_areas))

    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Transactions", f"{t.height:,}")
    k2.metric("Total Sales Value (M AED)", fmt_m(t['TRANS_VALUE'].sum()) if t.height > 0 else "—")
    k3.metric("Median Price/sqm (AED)", f"{t['PRICE_PER_SQM'].median():,.0f}" if t.height > 0 else "—")
    k4.metric("Avg Transaction Value (M AED)", fmt_m(t['TRANS_VALUE'].mean()) if t.height > 0 else "—")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if t.height > 0:
            df = (
                t.group_by("MONTH")
                .agg((pl.col("TRANS_VALUE").sum() / 1_000_000).alias("Sales Value (M AED)"))
                .sort("MONTH")
                .to_pandas()
            )
            fig = px.line(df, x="MONTH", y="Sales Value (M AED)",
                          title="Monthly Sales Volume (M AED)",
                          labels={"MONTH": "Month"})
            fig.update_traces(line_width=2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transactions.")

    with col2:
        if t.height > 0:
            df = (
                t.group_by("MONTH")
                .agg(pl.len().alias("Transactions"))
                .sort("MONTH")
                .to_pandas()
            )
            fig = px.bar(df, x="MONTH", y="Transactions",
                         title="Monthly Transaction Count",
                         labels={"MONTH": "Month"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No transactions.")

    if t.height > 0:
        df = (
            t.group_by("MONTH")
            .agg(pl.col("PRICE_PER_SQM").median().alias("Median AED/sqm"))
            .sort("MONTH")
            .to_pandas()
        )
        fig = px.line(df, x="MONTH", y="Median AED/sqm",
                      title="Median Price/sqm by Month",
                      labels={"MONTH": "Month"})
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 – Property Types
# ══════════════════════════════════════════════════════════════════════════════
with tab_prop:
    st.subheader("Sales by Property Type")

    # ── Tab filter ───────────────────────────────────────────────────────────
    pf_col1, pf_col2 = st.columns(2)
    with pf_col1:
        prop_offplan_vals = ["All"] + sorted(
            f_transactions["IS_OFFPLAN_EN"].drop_nulls().unique().to_list()
        ) if "IS_OFFPLAN_EN" in f_transactions.columns else ["All"]
        prop_offplan = st.selectbox("Off-plan / Ready", prop_offplan_vals, key="prop_offplan")
    with pf_col2:
        prop_area_vals = sorted(f_transactions["AREA_EN"].drop_nulls().unique().to_list()) if "AREA_EN" in f_transactions.columns else []
        prop_sel_areas = st.multiselect("Area", prop_area_vals, key="prop_area")
    prop_tx = f_transactions
    if prop_offplan != "All":
        prop_tx = prop_tx.filter(pl.col("IS_OFFPLAN_EN") == prop_offplan)
    if prop_sel_areas:
        prop_tx = prop_tx.filter(pl.col("AREA_EN").is_in(prop_sel_areas))

    st.divider()
    if prop_tx.height > 0 and "PROP_TYPE_EN" in prop_tx.columns:
        by_type = (
            prop_tx.filter(pl.col("PROP_TYPE_EN").is_not_null())
            .group_by("PROP_TYPE_EN")
            .agg(
                pl.len().alias("Transactions"),
                (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("Sales Value (M AED)"),
                pl.col("PRICE_PER_SQM").median().alias("Median Price/sqm"),
                pl.col("EFFECTIVE_AREA").median().alias("Median Area (sqm)"),
            )
            .sort("Transactions", descending=True)
            .to_pandas()
        )
        st.dataframe(by_type, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(by_type, x="PROP_TYPE_EN", y="Transactions",
                         title="Transaction Count by Property Type",
                         labels={"PROP_TYPE_EN": "Property Type"},
                         color="PROP_TYPE_EN")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(by_type, x="PROP_TYPE_EN", y="Median Price/sqm",
                         title="Median Price/sqm by Property Type",
                         labels={"PROP_TYPE_EN": "Property Type"},
                         color="PROP_TYPE_EN")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Price/sqm Trend by Property Type**")
        prop_types = by_type["PROP_TYPE_EN"].dropna().tolist()
        selected_types = st.multiselect("Property types", prop_types, default=prop_types[:4])
        if selected_types:
            trend = (
                prop_tx.filter(pl.col("PROP_TYPE_EN").is_in(selected_types))
                .group_by(["MONTH", "PROP_TYPE_EN"])
                .agg(pl.col("PRICE_PER_SQM").median().alias("Median AED/sqm"))
                .sort("MONTH")
                .to_pandas()
            )
            fig = px.line(trend, x="MONTH", y="Median AED/sqm", color="PROP_TYPE_EN",
                          title="Price/sqm Trend by Property Type",
                          labels={"MONTH": "Month", "PROP_TYPE_EN": "Type"})
            fig.update_traces(line_width=2)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transaction data with property type information.")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 5 – Rent Market
# ══════════════════════════════════════════════════════════════════════════════
with tab_rent:
    st.subheader("Rent Market Overview")

    # ── Tab filters ──────────────────────────────────────────────────────────
    rf_col1, rf_col2 = st.columns(2)
    with rf_col1:
        rn_prop_types = f_rents["PROP_TYPE_EN"].drop_nulls().unique().sort().to_list() if "PROP_TYPE_EN" in f_rents.columns else []
        rn_sel_types = st.multiselect("Property type", rn_prop_types, key="rn_prop_type")
    with rf_col2:
        rn_area_vals = sorted(f_rents["AREA_EN"].drop_nulls().unique().to_list()) if "AREA_EN" in f_rents.columns else []
        rn_sel_areas = st.multiselect("Area", rn_area_vals, key="rn_area")
    r = f_rents
    if rn_sel_types:
        r = r.filter(pl.col("PROP_TYPE_EN").is_in(rn_sel_types))
    if rn_sel_areas:
        r = r.filter(pl.col("AREA_EN").is_in(rn_sel_areas))

    st.divider()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Contracts", f"{r.height:,}")
    k2.metric("Total Annual Rent (M AED)", fmt_m(r['ANNUAL_AMOUNT'].sum()) if r.height > 0 else "—")
    k3.metric("Median Rent/sqm (AED)", f"{r['RENT_PER_SQM'].median():,.0f}" if r.height > 0 else "—")
    k4.metric("Avg Annual Contract (AED)", f"{r['ANNUAL_AMOUNT'].mean():,.0f}" if r.height > 0 else "—")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if r.height > 0:
            df = (
                r.group_by("MONTH")
                .agg((pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("Annual Rent (M AED)"))
                .sort("MONTH")
                .to_pandas()
            )
            fig = px.line(df, x="MONTH", y="Annual Rent (M AED)",
                          title="Monthly Rent Volume (M AED)",
                          labels={"MONTH": "Month"})
            fig.update_traces(line_width=2)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rent contracts.")

    with col2:
        if r.height > 0:
            df = (
                r.group_by("MONTH")
                .agg(pl.len().alias("Contracts"))
                .sort("MONTH")
                .to_pandas()
            )
            fig = px.bar(df, x="MONTH", y="Contracts",
                         title="Monthly Contract Count",
                         labels={"MONTH": "Month"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No rent contracts.")

    if r.height > 0 and "PROP_TYPE_EN" in r.columns:
        by_type_rent = (
            r.filter(pl.col("PROP_TYPE_EN").is_not_null())
            .group_by("PROP_TYPE_EN")
            .agg(
                pl.len().alias("Contracts"),
                (pl.col("ANNUAL_AMOUNT").sum() / 1_000_000).alias("Annual Rent (M AED)"),
                pl.col("RENT_PER_SQM").median().alias("Median Rent/sqm"),
            )
            .sort("Contracts", descending=True)
            .to_pandas()
        )
        st.markdown("**Rent by Property Type**")
        st.dataframe(by_type_rent, use_container_width=True, hide_index=True)

        st.markdown("**Median Rent/sqm Trend by Property Type**")
        rent_types = by_type_rent["PROP_TYPE_EN"].dropna().tolist()
        selected_rent_types = st.multiselect("Property types", rent_types, default=rent_types[:4], key="rent_types")
        if selected_rent_types:
            rent_trend = (
                r.filter(pl.col("PROP_TYPE_EN").is_in(selected_rent_types))
                .group_by(["MONTH", "PROP_TYPE_EN"])
                .agg(pl.col("RENT_PER_SQM").median().alias("Median Rent/sqm"))
                .sort("MONTH")
                .to_pandas()
            )
            fig = px.line(rent_trend, x="MONTH", y="Median Rent/sqm", color="PROP_TYPE_EN",
                          title="Median Rent/sqm Trend by Property Type",
                          labels={"MONTH": "Month", "PROP_TYPE_EN": "Type"})
            fig.update_traces(line_width=2)
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 6 – Land & Supply
# ══════════════════════════════════════════════════════════════════════════════
with tab_supply:
    st.subheader("Land & Supply Pipeline")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Land Parcels", f"{lands.height:,}")
    total_area = lands["ACTUAL_AREA"].sum()
    k2.metric("Total Land Area (sqm)", f"{total_area:,.0f}" if total_area else "—")
    active_projects = (projects["PROJECT_STATUS"] == "ACTIVE").sum()
    pending_projects = (projects["PROJECT_STATUS"] == "PENDING").sum()
    units_pipeline = int(projects["CNT_UNIT"].cast(pl.Float64, strict=False).sum())
    k3.metric("Active / Pending Projects", f"{active_projects:,} / {pending_projects:,}")
    k4.metric("Units in Pipeline", f"{units_pipeline:,}")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Land Type Distribution**")
        if "LAND_TYPE_EN" in lands.columns:
            land_type_counts = (
                lands.filter(pl.col("LAND_TYPE_EN").is_not_null())
                .group_by("LAND_TYPE_EN")
                .agg(
                    pl.len().alias("Parcels"),
                    pl.col("ACTUAL_AREA").sum().alias("Total Area (sqm)"),
                )
                .sort("Parcels", descending=True)
                .to_pandas()
            )
            fig = px.bar(land_type_counts, x="LAND_TYPE_EN", y="Parcels",
                         title="Land Type Distribution",
                         labels={"LAND_TYPE_EN": "Land Type"},
                         color="LAND_TYPE_EN")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Property Sub-type Distribution**")
        if "PROP_SUB_TYPE_EN" in lands.columns:
            sub_type_counts = (
                lands.filter(pl.col("PROP_SUB_TYPE_EN").is_not_null())
                .group_by("PROP_SUB_TYPE_EN")
                .agg(pl.len().alias("Parcels"))
                .sort("Parcels", descending=True)
                .head(15)
                .to_pandas()
            )
            fig = px.bar(sub_type_counts, x="PROP_SUB_TYPE_EN", y="Parcels",
                         title="Property Sub-type Distribution (top 15)",
                         labels={"PROP_SUB_TYPE_EN": "Sub-type"})
            fig.update_layout(xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    if "END_DATE" in projects.columns:
        pipeline_by_year = (
            projects.filter(pl.col("END_DATE").is_not_null())
            .with_columns(pl.col("END_DATE").dt.year().alias("Completion Year"))
            .group_by("Completion Year")
            .agg(
                pl.col("CNT_UNIT").cast(pl.Float64, strict=False).sum().alias("Units"),
                pl.len().alias("Projects"),
            )
            .sort("Completion Year")
            .filter(pl.col("Completion Year") >= 2024)
            .to_pandas()
        )
        fig = px.bar(pipeline_by_year, x="Completion Year", y="Units",
                     title="Units Pipeline by Completion Year",
                     text="Projects",
                     labels={"Completion Year": "Year"})
        fig.update_traces(texttemplate="%{text} projects", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    if "PERCENT_COMPLETED" in projects.columns:
        completed = projects.filter(pl.col("PERCENT_COMPLETED").is_not_null())
        if completed.height > 0:
            bins_df = (
                completed
                .with_columns(
                    pl.when(pl.col("PERCENT_COMPLETED") == 0).then(pl.lit("0%"))
                    .when(pl.col("PERCENT_COMPLETED") < 25).then(pl.lit("1–24%"))
                    .when(pl.col("PERCENT_COMPLETED") < 50).then(pl.lit("25–49%"))
                    .when(pl.col("PERCENT_COMPLETED") < 75).then(pl.lit("50–74%"))
                    .when(pl.col("PERCENT_COMPLETED") < 100).then(pl.lit("75–99%"))
                    .otherwise(pl.lit("100%"))
                    .alias("Completion Band")
                )
                .group_by("Completion Band")
                .agg(pl.len().alias("Projects"))
                .sort("Completion Band")
                .to_pandas()
            )
            fig = px.bar(bins_df, x="Completion Band", y="Projects",
                         title="Completion Progress Distribution",
                         color="Completion Band")
            st.plotly_chart(fig, use_container_width=True)
