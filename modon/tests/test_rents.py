from __future__ import annotations


SAMPLE_SIZE = 500  # matches conftest sampled_state n= for rents


class TestRentKPIs:
    def test_status_200(self, client):
        assert client.get("/api/rents/kpis").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/rents/kpis").json()
        assert {"total_contracts", "total_annual_rent",
                "median_rent_sqm", "avg_annual_contract"} <= data.keys()

    def test_total_contracts_lte_sample(self, client):
        data = client.get("/api/rents/kpis").json()
        assert data["total_contracts"] <= SAMPLE_SIZE

    def test_total_annual_rent_positive(self, client):
        assert client.get("/api/rents/kpis").json()["total_annual_rent"] > 0

    def test_developer_filter_reduces_count(self, client, known_developer):
        total = client.get("/api/rents/kpis").json()["total_contracts"]
        filtered = client.get(
            f"/api/rents/kpis?developer={known_developer}"
        ).json()["total_contracts"]
        assert filtered <= total

    def test_area_filter_reduces_count(self, client, sampled_state):
        rents_area = (
            sampled_state.rents["AREA_EN"].drop_nulls().unique().sort().head(1).to_list()
        )
        if not rents_area:
            return
        total = client.get("/api/rents/kpis").json()["total_contracts"]
        filtered = client.get(
            f"/api/rents/kpis?area={rents_area[0]}"
        ).json()["total_contracts"]
        assert filtered <= total


class TestRentTrends:
    def test_monthly_200(self, client):
        assert client.get("/api/rents/monthly").status_code == 200

    def test_monthly_count_200(self, client):
        assert client.get("/api/rents/monthly-count").status_code == 200

    def test_weekly_200(self, client):
        assert client.get("/api/rents/weekly").status_code == 200

    def test_weekly_count_200(self, client):
        assert client.get("/api/rents/weekly-count").status_code == 200

    def test_monthly_sorted(self, client):
        data = client.get("/api/rents/monthly").json()
        months = [row["month"] for row in data]
        assert months == sorted(months)

    def test_monthly_item_shape(self, client):
        data = client.get("/api/rents/monthly").json()
        assert len(data) > 0
        assert {"month", "value"} <= data[0].keys()

    def test_weekly_sorted(self, client):
        data = client.get("/api/rents/weekly").json()
        weeks = [row["month"] for row in data]
        assert weeks == sorted(weeks)

    def test_weekly_item_shape(self, client):
        data = client.get("/api/rents/weekly").json()
        assert len(data) > 0
        assert {"month", "value"} <= data[0].keys()


class TestRentByType:
    def test_status_200(self, client):
        assert client.get("/api/rents/by-type").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/rents/by-type").json(), list)

    def test_item_shape(self, client):
        data = client.get("/api/rents/by-type").json()
        if data:
            assert {"prop_type", "contract_count", "annual_rent_m",
                    "median_rent_sqm"} <= data[0].keys()

    def test_sorted_by_count_descending(self, client):
        data = client.get("/api/rents/by-type").json()
        counts = [row["contract_count"] for row in data]
        assert counts == sorted(counts, reverse=True)


class TestRentTypeTrend:
    def test_status_200(self, client):
        assert client.get("/api/rents/type-trend").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/rents/type-trend").json(), list)

    def test_sorted_by_month(self, client):
        data = client.get("/api/rents/type-trend").json()
        months = [row["month"] for row in data]
        assert months == sorted(months)

    def test_prop_types_filter(self, client, sampled_state):
        prop_types = (
            sampled_state.rents["PROP_TYPE_EN"]
            .drop_nulls().unique().sort().head(1).to_list()
        )
        if not prop_types:
            return
        r = client.get(f"/api/rents/type-trend?prop_types={prop_types[0]}")
        assert r.status_code == 200
        for row in r.json():
            assert row["prop_type"] == prop_types[0]

    def test_weekly_frequency(self, client):
        r = client.get("/api/rents/type-trend?frequency=weekly")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
            assert {"month", "prop_type", "median_rent_sqm"} <= data[0].keys()

    def test_weekly_sorted_by_period(self, client):
        data = client.get("/api/rents/type-trend?frequency=weekly").json()
        periods = [row["month"] for row in data]
        assert periods == sorted(periods)


class TestRentByArea:
    def test_status_200(self, client):
        assert client.get("/api/rents/by-area").status_code == 200

    def test_top_param(self, client):
        data = client.get("/api/rents/by-area?top=5").json()
        assert len(data) <= 5

    def test_item_shape(self, client):
        data = client.get("/api/rents/by-area").json()
        if data:
            assert {"area", "median_rent_sqm", "contract_count"} <= data[0].keys()

    def test_sorted_by_rent_descending(self, client):
        data = client.get("/api/rents/by-area?top=20").json()
        rents = [row["median_rent_sqm"] for row in data]
        assert rents == sorted(rents, reverse=True)

    def test_area_heatmap_200(self, client):
        assert client.get("/api/rents/area-heatmap").status_code == 200

    def test_area_heatmap_item_shape(self, client):
        data = client.get("/api/rents/area-heatmap").json()
        assert len(data) > 0
        assert {"area", "contract_count", "annual_rent_m"} <= data[0].keys()

    def test_area_heatmap_sorted(self, client):
        data = client.get("/api/rents/area-heatmap?top=10").json()
        counts = [row["contract_count"] for row in data]
        assert counts == sorted(counts, reverse=True)

    def test_area_heatmap_area_filter(self, client, sampled_state):
        areas = (
            sampled_state.rents["AREA_EN"].drop_nulls().unique().sort().head(1).to_list()
        )
        if not areas:
            return
        data = client.get(f"/api/rents/area-heatmap?area={areas[0]}").json()
        assert len(data) == 1
        assert data[0]["area"] == areas[0]


class TestRentsPaginated:
    def test_status_200(self, client):
        assert client.get("/api/rents").status_code == 200

    def test_pagination_shape(self, client):
        data = client.get("/api/rents").json()
        assert {"total", "page", "page_size", "items"} <= data.keys()

    def test_default_page_size(self, client):
        data = client.get("/api/rents").json()
        assert data["page_size"] == 50
        assert len(data["items"]) <= 50

    def test_custom_page_size(self, client):
        data = client.get("/api/rents?page_size=5").json()
        assert len(data["items"]) <= 5

    def test_total_matches_kpi(self, client):
        total_paginated = client.get("/api/rents").json()["total"]
        total_kpi = client.get("/api/rents/kpis").json()["total_contracts"]
        assert total_paginated == total_kpi

    def test_page_size_capped_at_500(self, client):
        assert client.get("/api/rents?page_size=501").status_code == 422

    def test_item_shape(self, client):
        items = client.get("/api/rents?page_size=1").json()["items"]
        assert len(items) == 1
        row = items[0]
        assert "annual_amount" in row
        assert "rent_per_sqm" in row

    def test_area_filter_applied_to_items(self, client, sampled_state):
        areas = (
            sampled_state.rents["AREA_EN"].drop_nulls().unique().sort().head(1).to_list()
        )
        if not areas:
            return
        data = client.get(f"/api/rents?area={areas[0]}").json()
        for row in data["items"]:
            assert row["area"] == areas[0]
