from __future__ import annotations


SAMPLE_SIZE = 500  # matches conftest sampled_state n= for transactions


class TestTransactionKPIs:
    def test_status_200(self, client):
        assert client.get("/api/transactions/kpis").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/transactions/kpis").json()
        assert {"total_transactions", "total_sales_value",
                "median_price_sqm", "avg_transaction_value"} <= data.keys()

    def test_total_transactions_lte_sample(self, client):
        data = client.get("/api/transactions/kpis").json()
        assert data["total_transactions"] <= SAMPLE_SIZE

    def test_developer_filter_reduces_count(self, client, known_developer):
        total = client.get("/api/transactions/kpis").json()["total_transactions"]
        filtered = client.get(
            f"/api/transactions/kpis?developer={known_developer}"
        ).json()["total_transactions"]
        assert filtered <= total

    def test_area_filter_reduces_count(self, client, known_area):
        total = client.get("/api/transactions/kpis").json()["total_transactions"]
        filtered = client.get(
            f"/api/transactions/kpis?area={known_area}"
        ).json()["total_transactions"]
        assert filtered <= total

    def test_total_sales_value_is_positive(self, client):
        data = client.get("/api/transactions/kpis").json()
        assert data["total_sales_value"] > 0


class TestTransactionTrends:
    def test_monthly_sales_200(self, client):
        assert client.get("/api/transactions/monthly").status_code == 200

    def test_monthly_count_200(self, client):
        assert client.get("/api/transactions/monthly-count").status_code == 200

    def test_monthly_price_200(self, client):
        assert client.get("/api/transactions/monthly-price").status_code == 200

    def test_monthly_sales_sorted(self, client):
        data = client.get("/api/transactions/monthly").json()
        months = [row["month"] for row in data]
        assert months == sorted(months)

    def test_monthly_item_shape(self, client):
        data = client.get("/api/transactions/monthly").json()
        assert len(data) > 0
        assert {"month", "value"} <= data[0].keys()

    def test_monthly_filter_by_developer(self, client, known_developer):
        r = client.get(f"/api/transactions/monthly?developer={known_developer}")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_weekly_sales_200(self, client):
        assert client.get("/api/transactions/weekly").status_code == 200

    def test_weekly_count_200(self, client):
        assert client.get("/api/transactions/weekly-count").status_code == 200

    def test_weekly_price_200(self, client):
        assert client.get("/api/transactions/weekly-price").status_code == 200

    def test_weekly_sales_sorted(self, client):
        data = client.get("/api/transactions/weekly").json()
        weeks = [row["month"] for row in data]
        assert weeks == sorted(weeks)

    def test_weekly_item_shape(self, client):
        data = client.get("/api/transactions/weekly").json()
        assert len(data) > 0
        assert {"month", "value"} <= data[0].keys()

    def test_area_heatmap_200(self, client):
        assert client.get("/api/transactions/area-heatmap").status_code == 200

    def test_area_heatmap_item_shape(self, client):
        data = client.get("/api/transactions/area-heatmap").json()
        assert len(data) > 0
        assert {"area", "transaction_count", "sales_value_m"} <= data[0].keys()

    def test_area_heatmap_sorted(self, client):
        data = client.get("/api/transactions/area-heatmap?top=10").json()
        counts = [row["transaction_count"] for row in data]
        assert counts == sorted(counts, reverse=True)

    def test_area_heatmap_area_filter(self, client, known_area):
        data = client.get(f"/api/transactions/area-heatmap?area={known_area}").json()
        assert len(data) == 1
        assert data[0]["area"] == known_area

    def test_by_area_200(self, client):
        assert client.get("/api/transactions/by-area").status_code == 200

    def test_by_area_item_shape(self, client):
        data = client.get("/api/transactions/by-area?top=10").json()
        assert len(data) > 0
        assert {"area", "median_price_sqm", "transaction_count"} <= data[0].keys()

    def test_by_area_sorted(self, client):
        data = client.get("/api/transactions/by-area?top=10").json()
        prices = [row["median_price_sqm"] for row in data]
        assert prices == sorted(prices, reverse=True)


class TestTransactionsPaginated:
    def test_status_200(self, client):
        assert client.get("/api/transactions").status_code == 200

    def test_pagination_shape(self, client):
        data = client.get("/api/transactions").json()
        assert {"total", "page", "page_size", "items"} <= data.keys()

    def test_default_page_is_1(self, client):
        data = client.get("/api/transactions").json()
        assert data["page"] == 1

    def test_default_page_size_is_50(self, client):
        data = client.get("/api/transactions").json()
        assert data["page_size"] == 50
        assert len(data["items"]) <= 50

    def test_custom_page_size(self, client):
        data = client.get("/api/transactions?page_size=10").json()
        assert len(data["items"]) <= 10
        assert data["page_size"] == 10

    def test_page_2_differs_from_page_1(self, client):
        p1 = client.get("/api/transactions?page_size=10&page=1").json()["items"]
        p2 = client.get("/api/transactions?page_size=10&page=2").json()["items"]
        # If total > 10, pages should differ
        total = client.get("/api/transactions").json()["total"]
        if total > 10:
            assert p1 != p2

    def test_total_matches_kpi(self, client):
        total_paginated = client.get("/api/transactions").json()["total"]
        total_kpi = client.get("/api/transactions/kpis").json()["total_transactions"]
        assert total_paginated == total_kpi

    def test_item_shape(self, client):
        items = client.get("/api/transactions?page_size=1").json()["items"]
        assert len(items) == 1
        row = items[0]
        assert "instance_date" in row
        assert "trans_value" in row
        assert "price_per_sqm" in row

    def test_page_size_capped_at_500(self, client):
        r = client.get("/api/transactions?page_size=501")
        assert r.status_code == 422  # FastAPI validation error

    def test_developer_filter_applied_to_items(self, client, known_developer):
        data = client.get(f"/api/transactions?developer={known_developer}").json()
        for row in data["items"]:
            assert row["developer"] == known_developer

    def test_area_filter_applied_to_items(self, client, known_area):
        data = client.get(f"/api/transactions?area={known_area}").json()
        for row in data["items"]:
            assert row["area"] == known_area

    def test_items_sorted_latest_first(self, client):
        items = client.get("/api/transactions?page_size=20").json()["items"]
        dates = [row["instance_date"] for row in items if row["instance_date"] is not None]
        assert dates == sorted(dates, reverse=True)
