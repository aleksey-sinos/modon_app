# Modon Market API — Frontend Reference

## Base URL
```
http://localhost:8000/api
```
Interactive docs: `http://localhost:8000/docs`

---

## Global Notes
- All responses are JSON.
- All monetary values are in **AED**.
- Values suffixed `_m` are in **millions of AED** (e.g. `sales_value_m: 12.3` = 12.3 M AED).
- Dates are returned as `"YYYY-MM-DD"` strings. The `month` field is always `"YYYY-MM-01"` (truncated to month).
- `null` means the data was not available for that record.
- All list endpoints that support filters accept these **common query params**:
  - `developer` — exact developer name string
  - `area` — exact area name string
  - `date_from` / `date_to` — ISO date `YYYY-MM-DD`, filters on the transaction/registration date

# Modon Market API — Frontend Reference

## Base URL
```text
http://localhost:8000/api
```

Interactive docs:
```text
http://localhost:8000/docs
```

---

## API Shape

This API now exposes only two frontend-facing layers:

1. **Curated record endpoints**
These return row-level records, but only after applying business rules so they are safe to display in product tables and use for drill-downs.

2. **Aggregated endpoints**
These return KPIs, time series, or grouped summaries for charts and dashboards.

There are **no public raw-data endpoints**.

---

## Global Notes

- All responses are JSON.
- All monetary values are in **AED** unless the field ends with `_m`, in which case the value is in **millions of AED**.
- Dates are returned as `YYYY-MM-DD` strings.
- `month` values are month-truncated dates like `2026-01-01`.
- `null` means the field was unavailable or intentionally not computed for that record.

### Common filters

Many endpoints support these query params:

- `developer`: exact developer name
- `area`: exact area name
- `date_from`: ISO date `YYYY-MM-DD`
- `date_to`: ISO date `YYYY-MM-DD`

### Important data semantics

- `/transactions` returns **curated sales records only**. Mortgages and gifts are excluded.
- `/rents` returns **curated rent records only**. `rent_per_sqm` is computed only where area is considered valid for reporting.
- `/mortgages` returns **one row per mortgage transaction**, aggregated by `TRANSACTION_NUMBER`.
- Developer metrics are useful for project pipeline reporting, but developer attribution on transactions/rents remains incomplete because source joins are weak.

---

## `/overview` — Market Overview

### `GET /api/overview/kpis`
Top-level overview across the curated sales dataset and project registry.

Response shape:
```json
{
  "total_projects": 187,
  "active_projects": 132,
  "units_in_pipeline": 45486,
  "total_sales_value": 1234567890.0,
  "median_price_sqm": 13500.0
}
```

### `GET /api/overview/monthly-sales`
Monthly curated sales totals.

Response shape:
```json
[
  { "month": "2026-01-01", "sales_value_m": 320.5, "transaction_count": 1840 }
]
```

### `GET /api/overview/weekly-sales`
Weekly curated sales totals.

Semantics:
- returns only completed weeks
- current in-progress week is excluded
- data is capped to the most recent 12 completed weeks

Query params:
- `segment`: `total` (default), `off-plan`, or `ready`

Response shape:
```json
[
  { "week": "2026-04-06", "sales_value_m": 84.2, "transaction_count": 472 }
]
```

### `GET /api/overview/weekly-rents`
Weekly curated rent totals.

Semantics:
- returns only completed weeks
- current in-progress week is excluded
- data is capped to the most recent 12 completed weeks

Response shape:
```json
[
  { "week": "2026-04-06", "annual_rent_m": 126.8, "contract_count": 3412 }
]
```

### `GET /api/overview/market-activity`
Rolling 30-day market snapshot across curated sales and curated rents.

Semantics:
- `anchor_date` is the latest date available across sales and rents
- `last_30d` is the inclusive window ending on `anchor_date`
- `previous_30d` is the 30 days immediately before that
- `delta_pct` is percentage change vs `previous_30d`; `null` when previous window is zero or unavailable

Response shape:
```json
{
  "anchor_date": "2026-04-13",
  "window_days": 30,
  "sales_count": { "last_30d": 4200, "previous_30d": 3980, "delta": 220, "delta_pct": 5.5 },
  "rent_count": { "last_30d": 28100, "previous_30d": 27440, "delta": 660, "delta_pct": 2.4 },
  "sales_price_per_sqm": { "last_30d": 14200.0, "previous_30d": 13650.0, "delta": 550.0, "delta_pct": 4.0 },
  "rent_price_per_sqm": { "last_30d": 1010.0, "previous_30d": 980.0, "delta": 30.0, "delta_pct": 3.1 }
}
```

### `GET /api/overview/development-activity`
Rolling 30-day development snapshot based on project `START_DATE`.

Semantics:
- `anchor_date` is the latest available `START_DATE`
- `last_30d` is the inclusive window ending on `anchor_date`
- `previous_30d` is the 30 days immediately before that

Response shape:
```json
{
  "anchor_date": "2026-04-13",
  "window_days": 30,
  "projects_started": { "last_30d": 41, "previous_30d": 38, "delta": 3, "delta_pct": 7.9 }
}
```

### `GET /api/overview/market-summary`
Gemini-backed dashboard narrative for the top summary card.

Semantics:
- calls Google Gemini from the backend when `GEMINI_API_KEY` is configured
- uses the Google Search tool for grounded market context
- caches the market briefing in memory on the backend for 7 days
- falls back to deterministic server-generated copy when Gemini is unavailable or not configured
- keeps the API key server-side; the frontend never calls Gemini directly
- returns grounding sources when Gemini search grounding is available

Environment variables:
- `GEMINI_API_KEY`: required for Gemini generation
- `GEMINI_MODEL`: optional, defaults to `gemini-3-flash`

Local setup:
- put these values in `modon/.env`
- `api.main` loads `modon/.env` automatically on startup

Response shape:
```json
{
  "provider": "gemini",
  "model": "gemini-2.0-flash",
  "generated_at": "2026-04-14T12:00:00Z",
  "is_fallback": false,
  "note": null,
  "summary": "Sales, rents, and launches remain constructive across the latest completed market windows.",
  "sections": [
    { "title": "Market Activity", "body": "Sales activity stayed firm across the latest 30-day window..." },
    { "title": "Pricing", "body": "Sale pricing held above the prior comparison period..." },
    { "title": "Development", "body": "Project starts remained active while the pipeline stayed concentrated..." }
  ],
  "sources": [
    { "title": "Example source", "url": "https://example.com/source" }
  ]
}
```

### `GET /api/overview/market-news`
Grounded latest-market-news feed for the expandable news panel.

Semantics:
- calls Google Gemini with Google Search grounding
- caches the latest generated news payload in memory on the backend
- only re-runs Gemini when `refresh=true` is requested
- returns summarized news items plus the grounded source links used for those items

Query params:
- `refresh`: optional boolean, bypasses the cached news payload and generates a fresh one

Response shape:
```json
{
  "provider": "gemini",
  "model": "gemini-3-flash-preview",
  "generated_at": "2026-04-14T12:00:00Z",
  "is_fallback": false,
  "note": null,
  "news_items": [
    {
      "headline": "Dubai transaction volumes cool after Q1 surge",
      "summary": "Recent coverage indicates deal activity has moderated as the market shifts from breakout growth toward a more normalized pace."
    }
  ],
  "sources": [
    { "title": "Example source", "url": "https://example.com/source" }
  ]
}
```

### `GET /api/overview/monthly-project-launches`
Monthly development launch totals based on project `START_DATE`.

Semantics:
- returns only completed months
- the latest month is excluded when the newest `START_DATE` falls inside an in-progress month
- data is capped to the most recent 12 months

Response shape:
```json
[
  {
    "month": "2026-04-01",
    "projects_started": 4,
    "project_value_m": 845.2,
    "units_announced": 1320.0
  }
]
```

### `GET /api/overview/top-areas-price`
Top areas by median sales price per sqm.

Query params:
- `min_transactions` default `10`
- `top` default `20`

Response shape:
```json
[
  { "area": "Business Bay", "median_price_sqm": 28000.0, "transaction_count": 540 }
]
```

### `GET /api/overview/top-areas-volume`
Top areas by total curated sales value.

Query params:
- `top` default `10`

Response shape:
```json
[
  { "area": "Dubai Marina", "sales_value_m": 1200.4 }
]
```

### `GET /api/overview/project-status`
Project counts by status.

Response shape:
```json
[
  { "status": "ACTIVE", "count": 132 },
  { "status": "PENDING", "count": 55 }
]
```

### `GET /api/overview/filter-options`
Filter values for frontend dropdowns.

Response shape:
```json
{
  "developers": ["Developer A", "Developer B"],
  "areas": ["Business Bay", "Dubai Marina"],
  "prop_types": ["Unit", "Villa", "Land"]
}
```

---

## `/developers` — Developer Analytics

These endpoints are strongest for **project pipeline** analysis. Sales and rent attribution is limited by weak project-name joins in source data.

### `GET /api/developers`
Developer leaderboard.

Response shape:
```json
[
  {
    "developer": "Developer A",
    "total_projects": 12,
    "active": 8,
    "pending": 4,
    "portfolio_value": 950000000.0,
    "total_units": 4200.0,
    "sales_count": 120,
    "sales_value": 220000000.0,
    "rent_count": 15,
    "rent_value": 1200000.0,
    "median_price_sqm": 14000.0,
    "median_rent_sqm": 1200.0,
    "gross_yield": 0.0857
  }
]
```

### `GET /api/developers/{developer_name}`
Developer detail page.

Returns:
- `kpis`
- `projects`
- `monthly_sales`

Response shape:
```json
{
  "developer": "Developer A",
  "kpis": { "developer": "Developer A", "total_projects": 12 },
  "projects": [
    {
      "project": "Project 1",
      "status": "ACTIVE",
      "percent_completed": 12.0,
      "start_date": "2026-01-15",
      "end_date": "2028-06-30",
      "project_value": 180000000.0,
      "units": 220.0
    }
  ],
  "monthly_sales": [
    { "month": "2026-01-01", "sales_value_m": 14.2, "transaction_count": 12 }
  ]
}
```

---

## `/transactions` — Curated Sales Records + Aggregates

These endpoints are built from the **curated sales view**:

- only `Sales`
- requires positive transaction value
- requires positive effective area
- `price_per_sqm` is safe to use

### `GET /api/transactions/kpis`
Response shape:
```json
{
  "total_transactions": 53909,
  "total_sales_value": 14200000000.0,
  "median_price_sqm": 13500.0,
  "avg_transaction_value": 263400.0
}
```

### `GET /api/transactions/monthly`
Monthly curated sales value in M AED.

Response shape:
```json
[
  { "month": "2026-01-01", "value": 320.5 }
]
```

### `GET /api/transactions/monthly-count`
Monthly curated sales counts.

Response shape:
```json
[
  { "month": "2026-01-01", "value": 1840.0 }
]
```

### `GET /api/transactions/monthly-price`
Monthly median price per sqm.

Response shape:
```json
[
  { "month": "2026-01-01", "value": 13200.0 }
]
```

### `GET /api/transactions`
Paginated curated sales records.

Query params:
- common filters
- `page` default `1`
- `page_size` default `50`, max `500`

Response shape:
```json
{
  "total": 53909,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "transaction_number": "1-123-2026",
      "instance_date": "2026-03-15",
      "developer": null,
      "project": "Project X",
      "area": "Business Bay",
      "prop_type": "Unit",
      "trans_value": 2500000.0,
      "effective_area": 120.5,
      "price_per_sqm": 20747.0,
      "is_offplan": "Off-Plan",
      "rooms": null
    }
  ]
}
```

Use this endpoint for drill-down tables under sales charts.

---

## `/mortgages` — Curated Mortgage Transactions + Aggregates

These endpoints are built from the mortgage reporting view.

Important rule:
- portfolio mortgages are aggregated to **one row per `TRANSACTION_NUMBER`**
- total value is reconstructed by summing split row values

### `GET /api/mortgages/kpis`
Response shape:
```json
{
  "total_mortgage_transactions": 12095,
  "total_mortgage_value": 9876543210.0,
  "avg_mortgage_value": 816532.0
}
```

### `GET /api/mortgages/monthly`
Monthly mortgage value in M AED.

Query params:
- `procedure`
- `date_from`
- `date_to`

Response shape:
```json
[
  { "month": "2026-01-01", "value": 32000.0 }
]
```

### `GET /api/mortgages/by-procedure`
Mortgage counts and totals by procedure type.

Response shape:
```json
[
  {
    "procedure": "Mortgage Registration",
    "transaction_count": 9178,
    "total_value_m": 12345.6,
    "avg_value": 1320000.0
  },
  {
    "procedure": "Portfolio Mortgage Registration",
    "transaction_count": 86,
    "total_value_m": 845.2,
    "avg_value": 9820000.0
  }
]
```

### `GET /api/mortgages`
Paginated mortgage transactions.

Query params:
- `procedure`
- `date_from`
- `date_to`
- `page` default `1`
- `page_size` default `50`, max `500`

Response shape:
```json
{
  "total": 12095,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "transaction_number": "43-74-2026",
      "instance_date": "2026-01-20",
      "procedure": "Portfolio Mortgage Registration",
      "mortgage_value": 120000000.0,
      "row_count": 227,
      "area": null,
      "prop_type": "Unit",
      "is_offplan": "Ready"
    }
  ]
}
```

Use this endpoint for mortgage detail tables and portfolio mortgage reporting.

---

## `/properties` — Property Type Analysis

Built on curated sales records.

### `GET /api/properties/types`
Aggregated sales metrics by property type.

Query params:
- common filters
- `is_offplan` exact string like `Off-Plan` or `Ready`

Response shape:
```json
[
  {
    "prop_type": "Unit",
    "transaction_count": 8200,
    "sales_value_m": 9800.0,
    "median_price_sqm": 14500.0,
    "median_area_sqm": 85.0
  }
]
```

### `GET /api/properties/type-trend`
Monthly median price per sqm by property type.

Query params:
- `prop_types` comma-separated string
- common filters except `is_offplan`

Response shape:
```json
[
  { "month": "2026-01-01", "prop_type": "Unit", "median_price_sqm": 14200.0 }
]
```

---

## `/rents` — Curated Rent Records + Aggregates

These endpoints are built from the curated rent view.

Rules:
- requires positive annual amount
- requires positive area for inclusion in curated records
- `rent_per_sqm` is computed only when area is considered valid for reporting

### `GET /api/rents/kpis`
Response shape:
```json
{
  "total_contracts": 317234,
  "total_annual_rent": 12400000000.0,
  "median_rent_sqm": 1000.0,
  "avg_annual_contract": 39100.0
}
```

### `GET /api/rents/monthly`
Monthly annual rent totals in M AED.

Response shape:
```json
[
  { "month": "2026-01-01", "value": 280.5 }
]
```

### `GET /api/rents/monthly-count`
Monthly contract counts.

Response shape:
```json
[
  { "month": "2026-01-01", "value": 4200.0 }
]
```

### `GET /api/rents/by-type`
Aggregated by property type.

Response shape:
```json
[
  {
    "prop_type": "Unit",
    "contract_count": 240000,
    "annual_rent_m": 9800.0,
    "median_rent_sqm": 98.0
  }
]
```

### `GET /api/rents/type-trend`
Monthly median rent per sqm by property type.

Query params:
- `prop_types` comma-separated string
- common filters

Response shape:
```json
[
  { "month": "2026-01-01", "prop_type": "Unit", "median_rent_sqm": 96.0 }
]
```

### `GET /api/rents/by-area`
Top areas by median rent per sqm.

Query params:
- `top` default `20`, max `100`
- `min_contracts` default `5`
- `developer`
- `date_from`
- `date_to`

Response shape:
```json
[
  { "area": "Business Bay", "median_rent_sqm": 180.0, "contract_count": 4200 }
]
```

### `GET /api/rents`
Paginated curated rent records.

Query params:
- common filters
- `page` default `1`
- `page_size` default `50`, max `500`

Response shape:
```json
{
  "total": 317234,
  "page": 1,
  "page_size": 50,
  "items": [
    {
      "registration_date": "2026-02-10",
      "developer": null,
      "project": null,
      "area": "Business Bay",
      "prop_type": "Unit",
      "annual_amount": 320000.0,
      "effective_area": 420.0,
      "rent_per_sqm": 761.9,
      "rooms": null
    }
  ]
}
```

Use this endpoint for rent detail tables under rent charts.

---

## `/supply` — Land & Supply Pipeline

### `GET /api/supply/kpis`
Response shape:
```json
{
  "total_land_parcels": 256464,
  "total_land_area_sqm": 8200000000.0,
  "active_projects": 132,
  "pending_projects": 55,
  "units_in_pipeline": 45486
}
```

### `GET /api/supply/land-types`
Parcel count and total land area by land type.

Response shape:
```json
[
  { "land_type": "Commercial", "parcels": 148182, "total_area_sqm": 5400000000.0 }
]
```

### `GET /api/supply/sub-types`
Top property sub-types by parcel count.

Query params:
- `top` default `15`, max `100`

Response shape:
```json
[
  { "sub_type": "Residential", "parcels": 104893 }
]
```

### `GET /api/supply/pipeline-by-year`
Units and projects grouped by planned completion year.

Query params:
- `from_year` default `2024`

Response shape:
```json
[
  { "completion_year": 2027, "units": 8400.0, "projects": 18 }
]
```

### `GET /api/supply/completion-bands`
Project counts by completion band.

Response shape:
```json
[
  { "band": "0%", "projects": 12 },
  { "band": "1-24%", "projects": 174 }
]
```

---

## `/health`

### `GET /health`
Response shape:
```json
{ "status": "ok" }
```

---

## Suggested Page → Endpoint Mapping

| Page / Component | Endpoints |
|---|---|
| Dashboard / Market Overview | `/overview/kpis`, `/overview/monthly-sales`, `/overview/top-areas-price`, `/overview/top-areas-volume`, `/overview/project-status` |
| Global filters | `/overview/filter-options` |
| Developer leaderboard | `/developers` |
| Developer detail | `/developers/{name}` |
| Sales dashboard | `/transactions/kpis`, `/transactions/monthly`, `/transactions/monthly-count`, `/transactions/monthly-price`, `/transactions` |
| Mortgage dashboard | `/mortgages/kpis`, `/mortgages/monthly`, `/mortgages/by-procedure`, `/mortgages` |
| Property type analysis | `/properties/types`, `/properties/type-trend` |
| Rent dashboard | `/rents/kpis`, `/rents/monthly`, `/rents/monthly-count`, `/rents/by-type`, `/rents/type-trend`, `/rents/by-area`, `/rents` |
| Land & supply dashboard | `/supply/kpis`, `/supply/land-types`, `/supply/sub-types`, `/supply/pipeline-by-year`, `/supply/completion-bands` |

---

## Frontend Guidance

- Use `/transactions` and `/rents` for **detail tables** under charts.
- Use `/transactions/*`, `/rents/*`, and `/mortgages/*` aggregate endpoints for **KPIs and charts**.
- Do not assume developer attribution is complete on transactions and rents.
- For mortgage reporting, use `/mortgages` instead of trying to interpret mortgage rows from sales endpoints.
