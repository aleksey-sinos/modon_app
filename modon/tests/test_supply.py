from __future__ import annotations


class TestSupplyKPIs:
    def test_status_200(self, client):
        assert client.get("/api/supply/kpis").status_code == 200

    def test_response_shape(self, client):
        data = client.get("/api/supply/kpis").json()
        assert {"total_land_parcels", "total_land_area_sqm",
                "active_projects", "pending_projects",
                "units_in_pipeline"} <= data.keys()

    def test_land_parcels_lte_sample(self, client, sampled_state):
        data = client.get("/api/supply/kpis").json()
        assert data["total_land_parcels"] == sampled_state.lands.height

    def test_active_projects_non_negative(self, client):
        data = client.get("/api/supply/kpis").json()
        assert data["active_projects"] >= 0
        assert data["pending_projects"] >= 0
        assert data["units_in_pipeline"] >= 0


class TestLandTypes:
    def test_status_200(self, client):
        assert client.get("/api/supply/land-types").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/supply/land-types").json(), list)

    def test_item_shape(self, client):
        data = client.get("/api/supply/land-types").json()
        if data:
            assert {"land_type", "parcels", "total_area_sqm"} <= data[0].keys()

    def test_sorted_by_parcels_descending(self, client):
        data = client.get("/api/supply/land-types").json()
        parcels = [row["parcels"] for row in data]
        assert parcels == sorted(parcels, reverse=True)

    def test_parcel_counts_positive(self, client):
        for row in client.get("/api/supply/land-types").json():
            assert row["parcels"] > 0


class TestSubTypes:
    def test_status_200(self, client):
        assert client.get("/api/supply/sub-types").status_code == 200

    def test_top_param(self, client):
        data = client.get("/api/supply/sub-types?top=5").json()
        assert len(data) <= 5

    def test_item_shape(self, client):
        data = client.get("/api/supply/sub-types").json()
        if data:
            assert {"sub_type", "parcels"} <= data[0].keys()

    def test_sorted_by_parcels_descending(self, client):
        data = client.get("/api/supply/sub-types").json()
        parcels = [row["parcels"] for row in data]
        assert parcels == sorted(parcels, reverse=True)


class TestPipelineByYear:
    def test_status_200(self, client):
        assert client.get("/api/supply/pipeline-by-year").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/supply/pipeline-by-year").json(), list)

    def test_item_shape(self, client):
        data = client.get("/api/supply/pipeline-by-year").json()
        if data:
            assert {"completion_year", "units", "projects"} <= data[0].keys()

    def test_years_gte_from_year(self, client):
        data = client.get("/api/supply/pipeline-by-year?from_year=2025").json()
        for row in data:
            assert row["completion_year"] >= 2025

    def test_sorted_by_year(self, client):
        data = client.get("/api/supply/pipeline-by-year").json()
        years = [row["completion_year"] for row in data]
        assert years == sorted(years)

    def test_units_non_negative(self, client):
        for row in client.get("/api/supply/pipeline-by-year").json():
            assert row["units"] >= 0
            assert row["projects"] > 0


class TestCompletionBands:
    EXPECTED_BANDS = {"0%", "1-24%", "25-49%", "50-74%", "75-99%", "100%"}

    def test_status_200(self, client):
        assert client.get("/api/supply/completion-bands").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/supply/completion-bands").json(), list)

    def test_item_shape(self, client):
        data = client.get("/api/supply/completion-bands").json()
        if data:
            assert {"band", "projects"} <= data[0].keys()

    def test_only_valid_bands(self, client):
        data = client.get("/api/supply/completion-bands").json()
        returned_bands = {row["band"] for row in data}
        assert returned_bands <= self.EXPECTED_BANDS

    def test_projects_counts_positive(self, client):
        for row in client.get("/api/supply/completion-bands").json():
            assert row["projects"] > 0


class TestNearestMetros:
    def test_status_200(self, client):
        assert client.get("/api/supply/nearest-metros").status_code == 200

    def test_top_param(self, client):
        data = client.get("/api/supply/nearest-metros?top=5").json()
        assert len(data) <= 5

    def test_sale_market_200(self, client):
        assert client.get("/api/supply/nearest-metros?market=sale").status_code == 200

    def test_item_shape(self, client):
        data = client.get("/api/supply/nearest-metros").json()
        if data:
            assert {
                "name", "contract_count", "annual_rent_m", "median_rent_sqm", "unique_areas",
                "current_median_rent_sqm", "previous_median_rent_sqm", "performance_30d_pct", "volatility_30d_pct",
            } <= data[0].keys()

    def test_sorted_by_price_descending(self, client):
        data = client.get("/api/supply/nearest-metros").json()
        prices = [row["median_rent_sqm"] for row in data if row["median_rent_sqm"] is not None]
        assert prices == sorted(prices, reverse=True)

    def test_sale_market_filters_extreme_performance_outliers(self, client):
        data = client.get("/api/supply/nearest-metros?market=sale").json()
        performance_values = [row["performance_30d_pct"] for row in data if row["performance_30d_pct"] is not None]
        assert all(abs(value) <= 200 for value in performance_values)


class TestNearestLandmarks:
    def test_status_200(self, client):
        assert client.get("/api/supply/nearest-landmarks").status_code == 200

    def test_top_param(self, client):
        data = client.get("/api/supply/nearest-landmarks?top=5").json()
        assert len(data) <= 5

    def test_sale_market_200(self, client):
        assert client.get("/api/supply/nearest-landmarks?market=sale").status_code == 200

    def test_item_shape(self, client):
        data = client.get("/api/supply/nearest-landmarks").json()
        if data:
            assert {
                "name", "contract_count", "annual_rent_m", "median_rent_sqm", "unique_areas",
                "current_median_rent_sqm", "previous_median_rent_sqm", "performance_30d_pct", "volatility_30d_pct",
            } <= data[0].keys()

    def test_sorted_by_price_descending(self, client):
        data = client.get("/api/supply/nearest-landmarks").json()
        prices = [row["median_rent_sqm"] for row in data if row["median_rent_sqm"] is not None]
        assert prices == sorted(prices, reverse=True)

    def test_sale_market_filters_extreme_performance_outliers(self, client):
        data = client.get("/api/supply/nearest-landmarks?market=sale").json()
        performance_values = [row["performance_30d_pct"] for row in data if row["performance_30d_pct"] is not None]
        assert all(abs(value) <= 200 for value in performance_values)
