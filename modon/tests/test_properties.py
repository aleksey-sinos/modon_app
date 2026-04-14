from __future__ import annotations


class TestPropertyTypes:
    def test_status_200(self, client):
        assert client.get("/api/properties/types").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/api/properties/types").json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_item_shape(self, client):
        row = client.get("/api/properties/types").json()[0]
        assert {"prop_type", "transaction_count", "sales_value_m",
                "median_price_sqm", "median_area_sqm"} <= row.keys()

    def test_sorted_by_count_descending(self, client):
        data = client.get("/api/properties/types").json()
        counts = [row["transaction_count"] for row in data]
        assert counts == sorted(counts, reverse=True)

    def test_transaction_counts_positive(self, client):
        for row in client.get("/api/properties/types").json():
            assert row["transaction_count"] > 0
            assert row["sales_value_m"] >= 0

    def test_developer_filter(self, client, known_developer):
        r = client.get(f"/api/properties/types?developer={known_developer}")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_area_filter(self, client, known_area):
        r = client.get(f"/api/properties/types?area={known_area}")
        assert r.status_code == 200

    def test_offplan_filter(self, client, sampled_state):
        # Get a real offplan value from the data
        offplan_values = (
            sampled_state.transactions["IS_OFFPLAN_EN"].drop_nulls().unique().to_list()
        )
        if not offplan_values:
            return
        r = client.get(f"/api/properties/types?is_offplan={offplan_values[0]}")
        assert r.status_code == 200


class TestPropertyTypeTrend:
    def test_status_200(self, client):
        assert client.get("/api/properties/type-trend").status_code == 200

    def test_returns_list(self, client):
        assert isinstance(client.get("/api/properties/type-trend").json(), list)

    def test_item_shape(self, client):
        data = client.get("/api/properties/type-trend").json()
        if data:
            assert {"month", "prop_type", "median_price_sqm"} <= data[0].keys()

    def test_sorted_by_month(self, client):
        data = client.get("/api/properties/type-trend").json()
        months = [row["month"] for row in data]
        assert months == sorted(months)

    def test_prop_types_filter(self, client, known_prop_type):
        r = client.get(f"/api/properties/type-trend?prop_types={known_prop_type}")
        assert r.status_code == 200
        for row in r.json():
            assert row["prop_type"] == known_prop_type

    def test_multiple_prop_types_filter(self, client, sampled_state):
        types = (
            sampled_state.transactions["PROP_TYPE_EN"]
            .drop_nulls().unique().sort().head(2).to_list()
        )
        joined = ",".join(types)
        r = client.get(f"/api/properties/type-trend?prop_types={joined}")
        assert r.status_code == 200
        returned_types = {row["prop_type"] for row in r.json()}
        assert returned_types <= set(types)

    def test_weekly_frequency(self, client):
        r = client.get("/api/properties/type-trend?frequency=weekly")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        if data:
          assert {"month", "prop_type", "median_price_sqm"} <= data[0].keys()

    def test_weekly_sorted_by_period(self, client):
        data = client.get("/api/properties/type-trend?frequency=weekly").json()
        periods = [row["month"] for row in data]
        assert periods == sorted(periods)
