from __future__ import annotations

import urllib.parse

import polars as pl


class TestLeaderboard:
    def test_status_200(self, client):
        assert client.get("/api/developers").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/developers").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        row = client.get("/api/developers").json()[0]
        expected = {
            "developer", "total_projects", "active", "pending",
            "active_portfolio_value", "pending_portfolio_value",
            "active_units", "pending_units",
            "sales_count", "rent_count", "gross_yield",
        }
        assert expected <= row.keys()

    def test_sorted_by_total_projects_descending(self, client):
        data = client.get("/api/developers").json()
        counts = [row["total_projects"] for row in data]
        assert counts == sorted(counts, reverse=True)

    def test_active_plus_pending_lte_total(self, client):
        for row in client.get("/api/developers").json():
            assert row["active"] + row["pending"] <= row["total_projects"]

    def test_sales_count_non_negative(self, client):
        for row in client.get("/api/developers").json():
            assert row["sales_count"] >= 0
            assert row["rent_count"] >= 0

    def test_area_filter_returns_only_developers_with_projects_in_area(self, client, sampled_state):
        area = (
            sampled_state.projects["AREA_EN"]
            .drop_nulls()
            .unique()
            .sort()
            .head(1)[0]
        )
        encoded_area = urllib.parse.quote(str(area))
        data = client.get(f"/api/developers?area={encoded_area}").json()

        expected = (
            sampled_state.projects
            .filter(pl.col("AREA_EN") == area)
            .group_by("DEVELOPER_EN")
            .agg(pl.len().alias("total_projects"))
            .iter_rows(named=True)
        )
        expected_counts = {str(row["DEVELOPER_EN"] or ""): int(row["total_projects"]) for row in expected}

        assert len(data) == len(expected_counts)
        assert {row["developer"] for row in data} == set(expected_counts)
        for row in data:
            assert row["total_projects"] == expected_counts[row["developer"]]


class TestDeveloperDetail:
    def test_known_developer_200(self, client, known_developer):
        encoded = urllib.parse.quote(known_developer)
        r = client.get(f"/api/developers/{encoded}")
        assert r.status_code == 200

    def test_detail_shape(self, client, known_developer):
        encoded = urllib.parse.quote(known_developer)
        data = client.get(f"/api/developers/{encoded}").json()
        assert "developer" in data
        assert "kpis" in data
        assert "projects" in data
        assert "monthly_sales" in data

    def test_developer_name_matches(self, client, known_developer):
        encoded = urllib.parse.quote(known_developer)
        data = client.get(f"/api/developers/{encoded}").json()
        assert data["developer"] == known_developer

    def test_projects_list_shape(self, client, known_developer):
        encoded = urllib.parse.quote(known_developer)
        data = client.get(f"/api/developers/{encoded}").json()
        for proj in data["projects"]:
            assert "project" in proj
            assert "status" in proj

    def test_monthly_sales_sorted(self, client, known_developer):
        encoded = urllib.parse.quote(known_developer)
        data = client.get(f"/api/developers/{encoded}").json()
        months = [row["month"] for row in data["monthly_sales"]]
        assert months == sorted(months)

    def test_unknown_developer_404(self, client):
        r = client.get("/api/developers/DOES_NOT_EXIST_XYZ")
        assert r.status_code == 404
