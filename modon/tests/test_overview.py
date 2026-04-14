from __future__ import annotations

from datetime import date, timedelta

import polars as pl


class TestKPIs:
    def test_status_200(self, client):
        assert client.get("/api/overview/kpis").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/overview/kpis").json()
        assert {"total_projects", "active_projects", "units_in_pipeline",
                "total_sales_value", "median_price_sqm"} <= data.keys()

    def test_total_projects_matches_sample(self, client, sampled_state):
        data = client.get("/api/overview/kpis").json()
        assert data["total_projects"] == sampled_state.projects.height

    def test_values_are_numeric(self, client):
        data = client.get("/api/overview/kpis").json()
        assert isinstance(data["total_projects"], int)
        assert isinstance(data["total_sales_value"], float)

    def test_active_projects_lte_total(self, client):
        data = client.get("/api/overview/kpis").json()
        assert data["active_projects"] <= data["total_projects"]


class TestMonthlySales:
    def test_status_200(self, client):
        assert client.get("/api/overview/monthly-sales").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/overview/monthly-sales").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        item = client.get("/api/overview/monthly-sales").json()[0]
        assert "month" in item
        assert "sales_value_m" in item
        assert "transaction_count" in item

    def test_months_are_sorted(self, client):
        months = [row["month"] for row in client.get("/api/overview/monthly-sales").json()]
        assert months == sorted(months)


class TestWeeklySales:
    def test_status_200(self, client):
        assert client.get("/api/overview/weekly-sales").status_code == 200

    def test_segment_status_200(self, client):
        assert client.get("/api/overview/weekly-sales?segment=off-plan").status_code == 200
        assert client.get("/api/overview/weekly-sales?segment=ready").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/overview/weekly-sales").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        item = client.get("/api/overview/weekly-sales").json()[0]
        assert "week" in item
        assert "sales_value_m" in item
        assert "transaction_count" in item

    def test_weeks_are_sorted(self, client):
        weeks = [row["week"] for row in client.get("/api/overview/weekly-sales").json()]
        assert weeks == sorted(weeks)

    def test_returns_last_12_weeks_max(self, client):
        data = client.get("/api/overview/weekly-sales").json()
        assert len(data) <= 12

    def test_excludes_current_week(self, client):
        data = client.get("/api/overview/weekly-sales").json()
        last_completed_sunday = _last_completed_sunday()
        current_week_start = last_completed_sunday - timedelta(days=6)
        assert all(row["week"] <= current_week_start.isoformat() for row in data)

    def test_segment_filter_matches_sampled_state(self, client, sampled_state):
        for segment, expected_value in [("off-plan", "Off-Plan"), ("ready", "Ready")]:
            data = client.get(f"/api/overview/weekly-sales?segment={segment}").json()
            cutoff_date = _last_completed_sunday()
            expected = (
                sampled_state.transactions
                .filter(pl.col("IS_OFFPLAN_EN") == expected_value)
                .filter(pl.col("INSTANCE_DATE") <= cutoff_date)
                .with_columns(pl.col("INSTANCE_DATE").dt.truncate("1w").alias("WEEK"))
                .group_by("WEEK")
                .agg(
                    (pl.col("TRANS_VALUE").sum() / 1_000_000).alias("sales_value_m"),
                    pl.len().alias("transaction_count"),
                )
                .sort("WEEK")
                .tail(12)
            )
            expected_rows = [
                {
                    "week": str(row["WEEK"]),
                    "sales_value_m": float(row["sales_value_m"] or 0),
                    "transaction_count": int(row["transaction_count"]),
                }
                for row in expected.iter_rows(named=True)
            ]
            assert data == expected_rows


class TestWeeklyRents:
    def test_status_200(self, client):
        assert client.get("/api/overview/weekly-rents").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/overview/weekly-rents").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        item = client.get("/api/overview/weekly-rents").json()[0]
        assert "week" in item
        assert "annual_rent_m" in item
        assert "contract_count" in item

    def test_weeks_are_sorted(self, client):
        weeks = [row["week"] for row in client.get("/api/overview/weekly-rents").json()]
        assert weeks == sorted(weeks)

    def test_returns_last_12_weeks_max(self, client):
        data = client.get("/api/overview/weekly-rents").json()
        assert len(data) <= 12

    def test_excludes_current_week(self, client):
        data = client.get("/api/overview/weekly-rents").json()
        last_completed_sunday = _last_completed_sunday()
        current_week_start = last_completed_sunday - timedelta(days=6)
        assert all(row["week"] <= current_week_start.isoformat() for row in data)


class TestMarketActivity:
    def test_status_200(self, client):
        assert client.get("/api/overview/market-activity").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/overview/market-activity").json()
        assert {"anchor_date", "window_days", "sales_count", "rent_count", "sales_price_per_sqm", "rent_price_per_sqm"} <= data.keys()
        assert {"last_30d", "previous_30d", "delta", "delta_pct"} <= data["sales_count"].keys()

    def test_window_days_is_30(self, client):
        data = client.get("/api/overview/market-activity").json()
        assert data["window_days"] == 30

    def test_counts_match_sampled_state(self, client, sampled_state):
        data = client.get("/api/overview/market-activity").json()

        anchor = max(
            sampled_state.transactions["INSTANCE_DATE"].max(),
            sampled_state.rents["REGISTRATION_DATE"].max(),
        )
        current_start = anchor - timedelta(days=29)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=29)

        sales_current = sampled_state.transactions.filter(
            pl.col("INSTANCE_DATE").is_between(current_start, anchor, closed="both")
        ).height
        sales_previous = sampled_state.transactions.filter(
            pl.col("INSTANCE_DATE").is_between(previous_start, previous_end, closed="both")
        ).height
        rents_current = sampled_state.rents.filter(
            pl.col("REGISTRATION_DATE").is_between(current_start, anchor, closed="both")
        ).height
        rents_previous = sampled_state.rents.filter(
            pl.col("REGISTRATION_DATE").is_between(previous_start, previous_end, closed="both")
        ).height

        assert data["sales_count"]["last_30d"] == sales_current
        assert data["sales_count"]["previous_30d"] == sales_previous
        assert data["rent_count"]["last_30d"] == rents_current
        assert data["rent_count"]["previous_30d"] == rents_previous

    def test_anchor_date_matches_latest_market_date(self, client, sampled_state):
        data = client.get("/api/overview/market-activity").json()
        latest = max(
            sampled_state.transactions["INSTANCE_DATE"].max(),
            sampled_state.rents["REGISTRATION_DATE"].max(),
        )
        assert data["anchor_date"] == latest.isoformat()


class TestDevelopmentActivity:
    def test_status_200(self, client):
        assert client.get("/api/overview/development-activity").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/overview/development-activity").json()
        assert {"anchor_date", "window_days", "projects_started"} <= data.keys()
        assert {"last_30d", "previous_30d", "delta", "delta_pct"} <= data["projects_started"].keys()

    def test_projects_started_matches_sampled_state(self, client, sampled_state):
        data = client.get("/api/overview/development-activity").json()
        projects = sampled_state.projects.filter(pl.col("START_DATE").is_not_null())
        anchor = projects["START_DATE"].max()
        current_start = anchor - timedelta(days=29)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=29)

        current_projects = projects.filter(
            pl.col("START_DATE").is_between(current_start, anchor, closed="both")
        ).height
        previous_projects = projects.filter(
            pl.col("START_DATE").is_between(previous_start, previous_end, closed="both")
        ).height

        assert data["projects_started"]["last_30d"] == current_projects
        assert data["projects_started"]["previous_30d"] == previous_projects

    def test_anchor_date_matches_latest_project_start(self, client, sampled_state):
        data = client.get("/api/overview/development-activity").json()
        latest = sampled_state.projects.filter(pl.col("START_DATE").is_not_null())["START_DATE"].max()
        assert data["anchor_date"] == latest.isoformat()


class TestMonthlyProjectLaunches:
    def test_status_200(self, client):
        assert client.get("/api/overview/monthly-project-launches").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/overview/monthly-project-launches").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        item = client.get("/api/overview/monthly-project-launches").json()[0]
        assert {"month", "projects_started", "project_value_m", "units_announced"} <= item.keys()

    def test_months_are_sorted(self, client):
        months = [row["month"] for row in client.get("/api/overview/monthly-project-launches").json()]
        assert months == sorted(months)

    def test_returns_last_12_months_max(self, client):
        data = client.get("/api/overview/monthly-project-launches").json()
        assert len(data) <= 12

    def test_excludes_latest_incomplete_month(self, client, sampled_state):
        data = client.get("/api/overview/monthly-project-launches").json()
        projects = sampled_state.projects.filter(pl.col("START_DATE").is_not_null())
        latest = projects["START_DATE"].max()
        if (latest + timedelta(days=1)).day != 1:
            excluded_month = latest.replace(day=1).isoformat()
            assert all(row["month"] < excluded_month for row in data)

    def test_matches_completed_month_aggregation(self, client, sampled_state):
        data = client.get("/api/overview/monthly-project-launches").json()
        projects = sampled_state.projects.filter(pl.col("START_DATE").is_not_null())
        latest = projects["START_DATE"].max()
        if (latest + timedelta(days=1)).day != 1:
            cutoff_date = latest.replace(day=1) - timedelta(days=1)
            projects = projects.filter(pl.col("START_DATE") <= cutoff_date)

        expected = (
            projects.with_columns(pl.col("START_DATE").dt.truncate("1mo").alias("MONTH"))
            .group_by("MONTH")
            .agg(
                pl.len().alias("projects_started"),
                (pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0).sum() / 1_000_000).alias("project_value_m"),
                pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0).sum().alias("units_announced"),
            )
            .sort("MONTH")
            .tail(12)
        )
        expected_rows = [
            {
                "month": str(row["MONTH"]),
                "projects_started": int(row["projects_started"]),
                "project_value_m": float(row["project_value_m"] or 0),
                "units_announced": float(row["units_announced"] or 0),
            }
            for row in expected.iter_rows(named=True)
        ]
        assert data == expected_rows


def _last_completed_sunday(today: date | None = None) -> date:
    reference = today or date.today()
    current_week_start = reference - timedelta(days=reference.weekday())
    return current_week_start - timedelta(days=1)


class TestTopAreasByPrice:
    def test_status_200(self, client):
        assert client.get("/api/overview/top-areas-price").status_code == 200

    def test_top_param_limits_results(self, client):
        data = client.get("/api/overview/top-areas-price?top=5").json()
        assert len(data) <= 5

    def test_item_shape(self, client):
        data = client.get("/api/overview/top-areas-price").json()
        if data:
            assert {"area", "median_price_sqm", "transaction_count"} <= data[0].keys()

    def test_sorted_by_price_descending(self, client):
        data = client.get("/api/overview/top-areas-price?top=20").json()
        prices = [row["median_price_sqm"] for row in data]
        assert prices == sorted(prices, reverse=True)


class TestTopAreasByVolume:
    def test_status_200(self, client):
        assert client.get("/api/overview/top-areas-volume").status_code == 200

    def test_top_param(self, client):
        data = client.get("/api/overview/top-areas-volume?top=3").json()
        assert len(data) <= 3

    def test_item_shape(self, client):
        data = client.get("/api/overview/top-areas-volume").json()
        if data:
            assert {"area", "sales_value_m"} <= data[0].keys()


class TestProjectStatus:
    def test_status_200(self, client):
        assert client.get("/api/overview/project-status").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/overview/project-status").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        for row in client.get("/api/overview/project-status").json():
            assert "status" in row
            assert "count" in row
            assert isinstance(row["count"], int)

    def test_counts_sum_to_total_projects(self, client, sampled_state):
        data = client.get("/api/overview/project-status").json()
        total = sum(row["count"] for row in data)
        assert total == sampled_state.projects.height


class TestTrendingDevelopmentAreas:
    def test_status_200(self, client):
        assert client.get("/api/overview/trending-development-areas").status_code == 200

    def test_top_param_limits_results(self, client):
        data = client.get("/api/overview/trending-development-areas?top=5").json()
        assert len(data) <= 5

    def test_item_shape(self, client):
        data = client.get("/api/overview/trending-development-areas").json()
        if data:
            assert {
                "area", "projects_started", "active_projects", "pending_projects",
                "units_announced", "active_units_announced", "pending_units_announced",
                "project_value_m", "active_project_value_m", "pending_project_value_m",
            } <= data[0].keys()

    def test_matches_recent_project_aggregation(self, client, sampled_state):
        data = client.get("/api/overview/trending-development-areas?top=8&window_days=90").json()
        projects = sampled_state.projects.filter(
            pl.col("AREA_EN").is_not_null()
            & (pl.col("AREA_EN").cast(pl.Utf8).str.strip_chars() != "")
            & pl.col("START_DATE").is_not_null()
        )
        anchor = projects["START_DATE"].max()
        expected = (
            projects
            .filter(pl.col("START_DATE").is_between(anchor - timedelta(days=89), anchor, closed="both"))
            .group_by("AREA_EN")
            .agg(
                pl.len().alias("projects_started"),
                (pl.col("PROJECT_STATUS") == "ACTIVE").sum().alias("active_projects"),
                (pl.col("PROJECT_STATUS") == "PENDING").sum().alias("pending_projects"),
                pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0).sum().alias("units_announced"),
                pl.when(pl.col("PROJECT_STATUS") == "ACTIVE").then(pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum().alias("active_units_announced"),
                pl.when(pl.col("PROJECT_STATUS") == "PENDING").then(pl.col("CNT_UNIT").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum().alias("pending_units_announced"),
                (pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0).sum() / 1_000_000).alias("project_value_m"),
                (pl.when(pl.col("PROJECT_STATUS") == "ACTIVE").then(pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum() / 1_000_000).alias("active_project_value_m"),
                (pl.when(pl.col("PROJECT_STATUS") == "PENDING").then(pl.col("PROJECT_VALUE").cast(pl.Float64, strict=False).fill_null(0)).otherwise(0).sum() / 1_000_000).alias("pending_project_value_m"),
            )
            .sort(
                by=["projects_started", "units_announced", "project_value_m", "AREA_EN"],
                descending=[True, True, True, False],
            )
            .head(8)
        )
        expected_rows = [
            {
                "area": str(row["AREA_EN"]),
                "projects_started": int(row["projects_started"]),
                "active_projects": int(row["active_projects"] or 0),
                "pending_projects": int(row["pending_projects"] or 0),
                "units_announced": float(row["units_announced"] or 0),
                "active_units_announced": float(row["active_units_announced"] or 0),
                "pending_units_announced": float(row["pending_units_announced"] or 0),
                "project_value_m": float(row["project_value_m"] or 0),
                "active_project_value_m": float(row["active_project_value_m"] or 0),
                "pending_project_value_m": float(row["pending_project_value_m"] or 0),
            }
            for row in expected.iter_rows(named=True)
        ]
        assert data == expected_rows


class TestFilterOptions:
    def test_status_200(self, client):
        assert client.get("/api/overview/filter-options").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/overview/filter-options").json()
        assert "developers" in data
        assert "areas" in data
        assert "prop_types" in data

    def test_lists_are_sorted(self, client):
        data = client.get("/api/overview/filter-options").json()
        assert data["developers"] == sorted(data["developers"])
        assert data["areas"] == sorted(data["areas"])

    def test_area_filters_developers(self, client, known_area, sampled_state):
        data = client.get(f"/api/overview/filter-options?area={known_area}").json()
        expected = sorted(
            sampled_state.transactions
            .filter(pl.col("AREA_EN") == known_area)
            ["DEVELOPER_EN"]
            .drop_nulls()
            .unique()
            .to_list()
        )
        assert data["developers"] == expected

    def test_developer_filters_areas(self, client, known_developer, sampled_state):
        data = client.get(f"/api/overview/filter-options?developer={known_developer}").json()
        expected = sorted(
            sampled_state.transactions
            .filter(pl.col("DEVELOPER_EN") == known_developer)
            ["AREA_EN"]
            .drop_nulls()
            .unique()
            .to_list()
        )
        assert data["areas"] == expected

    def test_date_range_filters_options(self, client, sampled_state):
        latest_date = sampled_state.transactions["INSTANCE_DATE"].max()
        earliest_date = latest_date
        data = client.get(
            f"/api/overview/filter-options?date_from={earliest_date.isoformat()}&date_to={latest_date.isoformat()}"
        ).json()
        expected_areas = sorted(
            sampled_state.transactions
            .filter(pl.col("INSTANCE_DATE") == latest_date)
            ["AREA_EN"]
            .drop_nulls()
            .unique()
            .to_list()
        )
        assert data["areas"] == expected_areas
