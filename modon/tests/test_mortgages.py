from __future__ import annotations


class TestMortgageKPIs:
    def test_status_200(self, client):
        assert client.get("/api/mortgages/kpis").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/mortgages/kpis").json()
        assert {
            "total_mortgage_transactions",
            "total_mortgage_value",
            "avg_mortgage_value",
        } <= data.keys()


class TestMortgageMonthly:
    def test_status_200(self, client):
        assert client.get("/api/mortgages/monthly").status_code == 200

    def test_returns_sorted_months(self, client):
        data = client.get("/api/mortgages/monthly").json()
        months = [row["month"] for row in data]
        assert months == sorted(months)


class TestMortgageByProcedure:
    def test_status_200(self, client):
        assert client.get("/api/mortgages/by-procedure").status_code == 200

    def test_item_shape(self, client):
        data = client.get("/api/mortgages/by-procedure").json()
        if data:
            assert {
                "procedure",
                "transaction_count",
                "total_value_m",
                "avg_value",
            } <= data[0].keys()


class TestMortgageList:
    def test_status_200(self, client):
        assert client.get("/api/mortgages").status_code == 200

    def test_pagination_shape(self, client):
        data = client.get("/api/mortgages").json()
        assert {"total", "page", "page_size", "items"} <= data.keys()

    def test_item_shape(self, client):
        items = client.get("/api/mortgages?page_size=1").json()["items"]
        if items:
            assert {
                "transaction_number",
                "procedure",
                "mortgage_value",
                "row_count",
            } <= items[0].keys()
