# Data Summary — Dubai DLD Open Data (snapshot: 2026-04-13)

All six CSV files cover **Q1 2026** activity (January–April 12 2026), loaded with
`infer_schema=False, null_values=[""]`. Temporal window is narrow (~3.5 months).

---

## 1. developers (111 × 13)

### Purpose
Entity registry of DLD-registered developers. One row per developer entity.

### Schema

| Column | Type after cast | Nulls | Notes |
|---|---|---|---|
| `DEVELOPER_NUMBER` | String (ID) | 0 | Unique primary key; range 2598–2708 — **different ID space from projects file** |
| `DEVELOPER_EN` | String | 0 | Developer name; all unique |
| `REGISTRATION_DATE` | Datetime | 0 | Range: 2026-01-06 → 2026-04-08 — **all 111 developers registered in 2026** |
| `LICENSE_SOURCE_EN` | String | 2 (2%) | 95% from "DUBAI ECONOMIC DEPARTMENT" |
| `LICENSE_TYPE_EN` | String | 88 (79%) | Only 23 have "PROFESSIONAL"; 88 null |
| `LEGAL_STATUS_EN` | String | 110 (99%) | Only 1 row populated ("Limited Responsibility") |
| `WEBPAGE` | String | 111 (100%) | **Entirely empty** |
| `PHONE` | String | 92 (83%) | Mostly empty |
| `FAX` | String | 96 (86%) | Mostly empty |
| `LICENSE_NUMBER` | String | 0 | All populated |
| `LICENSE_ISSUE_DATE` | Datetime | 0 | Range: 2013-02-20 → 2026-04-08 |
| `LICENSE_EXPIRY_DATE` | Datetime | 0 | Range: 2025-03-22 → 2027-04-22 |
| `CHAMBER_OF_COMMERCE_NO` | String | 111 (100%) | **Entirely empty** |

### Key Findings
- **Snapshot of newly active developers only.** All 111 registered within 3 months of the data snapshot. DLD does not include historical developer registry in this export.
- **6 developers already have expired licenses** (LICENSE_EXPIRY_DATE < 2026-04-13); 25 expire during 2026.
- **The developers file and projects file cannot be joined at all — not by ID and not by name.** DEVELOPER_NUMBER ranges are disjoint (2598–2708 vs 1002–2520), and zero company names match between the two files (checked case-insensitively). They represent entirely different populations of legal entities. The developers file is useful only as a standalone registry.
- `LEGAL_STATUS_EN`, `WEBPAGE`, `CHAMBER_OF_COMMERCE_NO` are useless (≥99% null).

### Usable Columns
`DEVELOPER_NUMBER` (within file), `DEVELOPER_EN`, `REGISTRATION_DATE`, `LICENSE_SOURCE_EN`, `LICENSE_NUMBER`, `LICENSE_ISSUE_DATE`, `LICENSE_EXPIRY_DATE`

---

## 2. projects (187 × 22)

### Purpose
Off-plan project registry. One row per registered project. Covers only DLD-registered
off-plan development projects active in 2026.

### Schema

| Column | Type after cast | Nulls | Notes |
|---|---|---|---|
| `PROJECT_NUMBER` | String (ID) | 0 | Unique; range 3189–3592 (recent projects) |
| `PROJECT_EN` | String | 0 | Project name; all 187 unique |
| `DEVELOPER_NUMBER` | String | 0 | Does not link to developers file (different ID space) |
| `DEVELOPER_EN` | String | 0 | 135 unique developer names |
| `START_DATE` | Date | 0 | All dates 2026-01-01 → 2026-04-13 — **start date = registration date** |
| `END_DATE` | Date | 0 | Planned completion: 2027-06-30 → 2032-12-31 — no projects overdue |
| `ADOPTION_DATE` | Date | 53 (28%) | DLD approval date; missing for pending projects |
| `PRJ_TYPE_EN` | String | 0 | Always "Normal" (no value) |
| `PROJECT_VALUE` | Float | 0 | Total declared project value; range 11M–6.5B AED; median 125M AED |
| `ESCROW_ACCOUNT_NUMBER` | String | 47 (25%) | Off-plan escrow; missing for ~25% |
| `PROJECT_STATUS` | String | 0 | ACTIVE: 132, PENDING: 55 |
| `PERCENT_COMPLETED` | Float | 13 (7%) | 174/187 projects < 25% complete; all effectively new |
| `INSPECTION_DATE` | Date | 13 (7%) | DLD inspection; aligns with null PERCENT_COMPLETED |
| `COMPLETION_DATE` | Date | 185 (99%) | **Almost entirely null** (actual completion not recorded) |
| `DESCRIPTION_EN` | String | varies | Free-text project description |
| `AREA_EN` | String | 0 | Project location; 44 unique areas |
| `ZONE_EN` | String | 74 (40%) | Further location detail |
| `CNT_LAND` | Int | 0 | Plot count; median 0, max N/A |
| `CNT_BUILDING` | Int | 0 | Building count |
| `CNT_VILLA` | Int | 0 | Villa count |
| `CNT_UNIT` | Int | 0 | Unit count; median 131, mean 243, max 2,169 |
| `MASTER_PROJECT_EN` | String | 185 (99%) | Master project (phase grouping); only 2 populated |

### Key Findings
- **File scope: 2026-registered projects only.** START_DATE and REGISTRATION_DATE are effectively the same thing. This is NOT a complete historical project registry.
- **All projects are new builds** (<25% complete). Median project value 125M AED, max 6.5B AED.
- **PROJECT_STATUS = PENDING (55 projects)** means DLD approval not yet granted; ADOPTION_DATE and escrow often missing for these.
- **DEVELOPER_NUMBER key is incompatible with developers file** — projects use IDs in the 1002–2520 range, developers file has 2598–2708. No numeric join possible.
- **MASTER_PROJECT_EN is 99% null** — cannot use it for phase grouping.
- Top areas: Madinat Al Mataar (24), Wadi Al Safa 3 (14), Palm Deira (12).
- `PRJ_TYPE_EN` is always "Normal" — drop this column. `COMPLETION_DATE` is 99% null — unreliable.

### Usable Columns
`PROJECT_NUMBER`, `PROJECT_EN`, `DEVELOPER_EN`, `START_DATE`, `END_DATE`, `PROJECT_VALUE`, `PROJECT_STATUS`, `PERCENT_COMPLETED`, `AREA_EN`, `CNT_UNIT`, `ESCROW_ACCOUNT_NUMBER` (as escrow flag)

---

## 3. lands (256,464 × 12)

### Purpose
Property/land parcel registry — a property master list. One row per registered parcel or
property unit. The largest reference table.

### Schema

| Column | Type after cast | Nulls | Notes |
|---|---|---|---|
| `LAND_TYPE_EN` | String | 20,190 (7.9%) | Commercial: 148K, Residential: 56K, Industrial: 11K, ... |
| `PROP_SUB_TYPE_EN` | String | 41,688 (16.3%) | Residential: 105K, Commercial: 43K, R/Villa: 23K, ... |
| `ACTUAL_AREA` | Float | 1,587 (0.6%) | Parcel area in sqm; median 768, p95 5,587; **52 outliers >10M sqm** |
| `IS_OFFPLAN_EN` | String | 0 | Ready: 248,015 (97%), Off-Plan: 8,449 (3%) |
| `PRE_REGISTRATION_NUMBER` | String | 137,055 (53.4%) | Historical reference number; mixed formats |
| `IS_FREE_HOLD_EN` | String | 0 | Free Hold: 128K (50%), Non Free Hold: 129K (50%) |
| `DM_ZIP_CODE` | String | 0 | 100% populated; Dubai Municipality ZIP |
| `MASTER_PROJECT_EN` | String | 256,449 (100%) | **Entirely empty** — do not use |
| `PROJECT_NUMBER` | Float | 169,725 (66.2%) | Numeric project ID (1–4,000s); **does NOT match projects file** numbers |
| `PROJECT_EN` | String | 169,725 (66.2%) | Project name for 34% of parcels |
| `AREA_EN` | String | 0 | 256 unique areas |
| `ZONE_EN` | String | 0 | Always "Dubai" — useless (2 unique values: "Dubai" and null) |

### Key Findings
- **No temporal dimension** — no date column. This is a static property register.
- **No developer column** — cannot determine property ownership from lands alone.
- **PROJECT_NUMBER key space (1–4,000s) does NOT match projects file** (3189–3592). The 3,854 unique project numbers in lands yield 0 matches against the projects file — they appear to be DLD parcel registration IDs, not project registration IDs.
- **66% of parcels have no project linkage** — they are standalone properties (older parcels not associated with a DLD-registered project).
- **52 records with `ACTUAL_AREA` > 10M sqm** — detailed analysis reveals three distinct categories:
  - **1 genuine data error**: Al Ruwayyah parcel assigned 2,631,387,198 sqm (64% of Dubai's total land area). Unconditional removal.
  - **7 zone-area stamped on sub-parcels**: Palm Jabal Ali — exact value 49,091,250 sqm repeated on all 7 rows with different `PROJECT_EN` values (Kempinski, Azizi Platine, etc.). The master development footprint (~49 km²) is being copied to each individual project parcel. Keep for land-type distribution; exclude from per-parcel area calculations.
  - **44 legitimately large parcels**: Government Authority land (Al Maktoum Airport zone at 64 km², DXB at 28 km²), Jabal Ali industrial zones, agricultural land in Hatta/Remah/Umm Addamin, World Islands, Palm Jumeirah aggregates. All are `IS_OFFPLAN_EN = Ready`. These are real parcels.
- **Recommended filter for price/area calculations**: `ACTUAL_AREA < 1,000,000 sqm` (1 km²) — removes macro-zone records while keeping large-but-real individual parcels. p99 = 49,977 sqm; p999 = 907,957 sqm; sane max = 9,981,038 sqm.
- Top areas by parcel count: Madinat Hind 4 (16K), Al Hebiah Fifth (9K), Al Aweer First (9K).
- `ZONE_EN` is always "Dubai" — drop. `MASTER_PROJECT_EN` is 100% null — drop.

### Usable Columns
`LAND_TYPE_EN`, `PROP_SUB_TYPE_EN`, `ACTUAL_AREA`, `IS_OFFPLAN_EN`, `IS_FREE_HOLD_EN`, `DM_ZIP_CODE`, `PROJECT_EN`, `AREA_EN`

---

## 4. transactions (69,413 × 22)

### Purpose
DLD real estate transaction registry. One row per registered transaction event.
Covers ALL transaction types (Sales, Mortgage, Gifts) in Q1 2026.

### Schema & Filters Applied in `prepare_transactions`

| Filter | Rows removed | Reason |
|---|---|---|
| `GROUP_EN == "Sales"` | −15,504 | Removes Mortgage (13,223) + Gifts (2,281) |
| `TRANS_VALUE > 0 & EFFECTIVE_AREA > 0` | −0 | No additional removal |
| **After filter** | **53,909** | Sales-only transaction dataset |

### Key Columns

| Column | Type after cast | Nulls (raw) | Notes |
|---|---|---|---|
| `TRANSACTION_NUMBER` | String (ID) | 0 | Unique per row in Sales; shared across rows in Portfolio Mortgage |
| `INSTANCE_DATE` | Date | 0 | Range: 2026-01-01 → 2026-04-12 |
| `GROUP_EN` | String | 0 | Sales / Mortgage Registration / Gift |
| `PROCEDURE_EN` | String | 0 | Sub-type: Sale, Mortgage Registration, Portfolio Mortgage, Gift, etc. |
| `TRANS_VALUE` | Float | 0 (post-numeric cast) | AED; Sales median ~1.3M AED |
| `ACTUAL_AREA` | Float | ~14% null | Property area; fallback to `PROCEDURE_AREA` |
| `PROCEDURE_AREA` | Float | ~12% null | Registered area |
| `EFFECTIVE_AREA` | Derived | 0 (after coalesce) | `coalesce(ACTUAL_AREA, PROCEDURE_AREA)` |
| `PRICE_PER_SQM` | Derived | 0 | `TRANS_VALUE / EFFECTIVE_AREA` |
| `IS_OFFPLAN_EN` | String | 0 | Off-Plan or Ready |
| `PROP_TYPE_EN` | String | 0 | Unit, Villa, Land, Building |
| `PROP_SUB_TYPE_EN` | String | ~5% null | Flat, Apartment, Villa, etc. |
| `PROJECT_EN` | String | ~60% null | Project name; sparse |
| `MASTER_PROJECT_EN` | String | ~90% null | Very sparse |
| `AREA_EN` | String | 0 | 252 unique areas |
| `DEVELOPER_EN` | String | 86% null | Enriched via project join; mostly fails |
| `TOTAL_BUYER` | Int | 0 | Number of buyers; useful for investment analysis |
| `IS_FREE_HOLD_EN` | String | 0 | Free Hold / Non Free Hold |

### Non-Sales Groups (filtered out)

**Mortgage Registration (9,178 rows):**
- Standard mortgage; `TRANS_VALUE` = full property value of the mortgaged asset
- Median TRANS_VALUE: ~1.32M AED; 100% Ready properties; Jan 2026 had huge spike (4,274 registrations worth 32.3B AED)

**Portfolio Mortgage Registration (1,128 rows):**
- Single facility covering multiple properties simultaneously
- `TRANSACTION_NUMBER` is shared across 2–227 rows (one row per property in the portfolio)
- **`TRANS_VALUE` = total facility amount ÷ number of properties** (equal split per row)
- Summing `TRANS_VALUE` across all rows of the same `TRANSACTION_NUMBER` correctly reconstructs the total loan amount — no double-counting
- Example: TX 43-74-2026 — 227 Units, each `TRANS_VALUE` = 528,634 AED, total = 120M AED
- All portfolio mortgage rows have `PROJECT_EN = null`

**Delayed Mortgage Registration (1,050 rows):**
- Mortgage formalized after an off-plan period delay

**Gifts (2,281 rows):**
- Property transfers as gift; `TRANS_VALUE` often nominal

### Key Findings
- **86.1% null `DEVELOPER_EN`** after enrichment — primary limitation for developer analytics
- **60% null `PROJECT_EN`** — many transactions are standalone property sales
- `PRICE_PER_SQM` is the most reliable derived metric for market analysis
- Top areas by volume: Business Bay, Dubai Marina, Jumeirah Village Circle
- Off-plan share significant (check monthly trend for split)

### Usable for Sales Analysis
`INSTANCE_DATE`, `TRANS_VALUE`, `EFFECTIVE_AREA`, `PRICE_PER_SQM`, `IS_OFFPLAN_EN`, `PROP_TYPE_EN`, `PROP_SUB_TYPE_EN`, `AREA_EN`, `TOTAL_BUYER`, `IS_FREE_HOLD_EN`

---

## 5. rents (317,235 × 20)

### Purpose
DLD rental contract registry. One row per registered rental contract.
Covers Q1 2026 contract registrations (new and renewals).

### Schema

| Column | Type after cast | Nulls | Notes |
|---|---|---|---|
| `REGISTRATION_DATE` | Date | 0 | Range: 2026-01-01 → 2026-04-12 |
| `START_DATE` | Date | 0 | Contract start (may pre-date registration) |
| `END_DATE` | Date | 0 | Contract end |
| `VERSION_EN` | String | 0 | New: 130,775 (41%), Renewed: 186,460 (59%) |
| `AREA_EN` | String | 0 | 190 unique areas |
| `CONTRACT_AMOUNT` | Float | 0 | Total contract value; median 73K AED; same as ANNUAL_AMOUNT for 90% |
| `ANNUAL_AMOUNT` | Float | 0 | Annual rent; median 75K AED |
| `IS_FREE_HOLD_EN` | String | 0 | Free Hold: 159K (50%), Non Free Hold: 158K (50%) |
| `ACTUAL_AREA` | Float | 0 | Area in sqm; median 68.75; **1 extreme outlier at 373M sqm** |
| `PROP_TYPE_EN` | String | 0 | Unit: 285K, Villa: 17K, Virtual Unit: 14K, Land: 1K, Building: 89 |
| `PROP_SUB_TYPE_EN` | String | 1,117 (0.4%) | Flat: 184K, Office: 44K, Labour Camps: 31K, Shop: 26K |
| `ROOMS` | String | 307,220 (96.8%) | Almost entirely null; 3-bed most common among present values |
| `USAGE_EN` | String | 1,232 (0.4%) | Residential: 234K (74%), Commercial: 81K (26%) |
| `NEAREST_METRO_EN` | String | 46,520 (14.7%) | Nearest metro station |
| `NEAREST_MALL_EN` | String | 51,318 (16.2%) | Nearest mall |
| `NEAREST_LANDMARK_EN` | String | 28,112 (8.9%) | Nearest landmark |
| `PARKING` | Float | 311,121 (98.1%) | **Almost entirely null** |
| `TOTAL_PROPERTIES` | Float | 0 | Properties in contract; usually 1; max 408 |
| `MASTER_PROJECT_EN` | String | 317,143 (100%) | **Entirely empty** |
| `PROJECT_EN` | String | 237,993 (75%) | 75% null — enrichment nearly impossible |

### Key Findings
- **Largest file by row count (317K rows)**; 3.5 months of Q1 2026 contracts
- **59% are renewals** — does not represent "new rental demand" alone; renewal registrations are a legal requirement in Dubai
- **CONTRACT_AMOUNT ≈ ANNUAL_AMOUNT for 90% of rows** (ratio median = 1.0); difference occurs for multi-year contracts or partial periods
- **Annual rent per sqm: p25=668, median=1,000, p75=1,948 AED/sqm/year** — consistent with Dubai residential/commercial mix
- **Virtual Unit (13,681)** — a DLD unit type for properties not yet assigned a physical unit number (common in off-plan)
- **Labor Camps (30,851 sub-type)** — large industrial rental segment in areas like Jabal Ali, Al Quoz
- **55,380 contracts cover >1 property** (TOTAL_PROPERTIES > 1) — portfolio leases; use `ANNUAL_AMOUNT/TOTAL_PROPERTIES` for per-unit analysis
- **ROOMS: 97% null** — not useful for bedroom analysis
- **PARKING: 98% null** — not useful
- **PROJECT_EN: 75% null** — enrichment to DEVELOPER_EN nearly impossible (~100% null after enrichment)
- Top areas by contract count: Business Bay (14K), Jabal Ali Industrial First (12K), Al Warsan First (12K)
- Monthly trend: Jan 112K → Feb 94K → Mar 76K → Apr (partial) 35K — declining volume through quarter (common seasonal pattern)

### Anomaly: ACTUAL_AREA
- Max is 373M sqm (~373 km², larger than Dubai itself)
- p95 is only 330 sqm — extreme outlier, likely data entry error
- Filter `ACTUAL_AREA < 10,000 sqm` for meaningful rent-per-sqm analysis

### Usable Columns
`REGISTRATION_DATE`, `VERSION_EN`, `AREA_EN`, `ANNUAL_AMOUNT`, `CONTRACT_AMOUNT`, `IS_FREE_HOLD_EN`, `ACTUAL_AREA` (with outlier filter), `PROP_TYPE_EN`, `PROP_SUB_TYPE_EN`, `USAGE_EN`, `TOTAL_PROPERTIES`, `NEAREST_METRO_EN`, `NEAREST_MALL_EN`, `NEAREST_LANDMARK_EN`

---

## 6. valuations (1,505 × 10)

### Purpose
DLD official property valuation records. One row per valuation procedure.
Much smaller than other files — only formal DLD valuations (not all transactions).

### Schema

| Column | Type after cast | Nulls | Notes |
|---|---|---|---|
| `PROCEDURE_NUMBER` | String | 0 | Valuation ID; **not unique** (can have multiple valuations per procedure batch) |
| `PROCEDURE_YEAR` | Float | 0 | 2026: 1,500, 2025: 1, 2023: 4 — almost all 2026 |
| `INSTANCE_DATE` | Date | 0 | Range: 2026-01-02 → 2026-04-10 |
| `AREA_EN` | String | 0 | 168 unique areas |
| `PROPERTY_TYPE_EN` | String | 0 | Land: 1,127 (75%), Unit: 343 (23%), Building: 35 (2%) |
| `PROP_SUB_TYPE_EN` | String | 102 (6.8%) | Commercial: 415, Residential: 386, Flat: 309, Villa: 62 |
| `ACTUAL_AREA` | Float | 0 | Area of valued property; median 1,282 sqm; max 31M sqm (likely land) |
| `PROCEDURE_AREA` | Float | 0 | Same as ACTUAL_AREA in almost all cases |
| `ACTUAL_WORTH` | Float | 0 | **Assessed market value**; median 9.6M AED; matches PROPERTY_TOTAL_VALUE in 78% of rows |
| `PROPERTY_TOTAL_VALUE` | Float | 1 (0.1%) | Declared total value (may include improvements); median 9.6M AED |

### Key Findings
- **75% of valuations are Land parcels** (not built units); reflects DLD's role in land value certification for development finance
- **Median assessed value: 9.6M AED** (vs median sales TRANS_VALUE ~1.3M AED) — this is because land parcels are larger commercial/residential land, not individual apartments
- **Value per sqm: p25=5,649, median=10,337, p75=16,146 AED/sqm** — reflects mostly commercial/mixed-use land in prime areas
- **ACTUAL_WORTH vs PROPERTY_TOTAL_VALUE**: equal in 78% of cases; when different, `PROPERTY_TOTAL_VALUE` is slightly higher (includes building/improvement value on top of land)
- **Top areas: Palm Deira (90), Me'Aisem First (84), World Islands (45), Marsa Dubai (38)** — unusual areas suggesting specific development activity requiring DLD valuation sign-off
- No `PROJECT_EN`, `DEVELOPER_EN`, or `IS_OFFPLAN_EN` columns — **cannot link to projects, developers, or transactions**
- `PROCEDURE_NUMBER` is not unique (sequential IDs reused across batches)
- Minimal historical data (4 rows from 2023, 1 from 2025) — not useful for time-series

### Usable Columns
`INSTANCE_DATE`, `AREA_EN`, `PROPERTY_TYPE_EN`, `PROP_SUB_TYPE_EN`, `ACTUAL_AREA`, `ACTUAL_WORTH`, `PROPERTY_TOTAL_VALUE`

---

## 7. Cross-File Relationships

### Join Summary

| Left | Right | Join key | Result | Recommended use |
|---|---|---|---|---|
| `developers` | `projects` | `DEVELOPER_NUMBER` | ❌ No overlap | Do not join |
| `developers` | `projects` | `DEVELOPER_EN` | ❌ No overlap | Do not join |
| `projects` | `lands` | `PROJECT_NUMBER` | ❌ Broken | Do not use |
| `projects` | `lands` | `PROJECT_EN` | ✅ Strong | Primary project-to-land join |
| `projects` | `transactions` | `PROJECT_EN` | ⚠️ Weak | Limited enrichment only |
| `projects` | `rents` | `PROJECT_EN` | ❌ Nearly unusable | Avoid for reporting |
| `transactions` | `rents` | `AREA_EN` | ⚠️ Partial | Area-level market comparisons only |
| `transactions` | `lands` | `AREA_EN` | ⚠️ Partial | Area/property context only |
| `valuations` | any other file | any obvious key | ❌ No shared key | Treat as standalone |

### What Joins Actually Work

| Join | Status | Notes |
|---|---|---|
| `projects.DEVELOPER_EN` → `developers.DEVELOPER_EN` | ❌ No overlap | Zero exact name matches; completely different sets of entities |
| `projects.DEVELOPER_NUMBER` → `developers.DEVELOPER_NUMBER` | ❌ Broken | ID ranges are disjoint (2598–2708 vs 1002–2520) |
| `lands.PROJECT_EN` → `projects.PROJECT_EN` | ✅ 177/187 | Best join: 177 projects match by name in lands |
| `transactions.PROJECT_EN` → `projects.PROJECT_EN` | ⚠️ Weak | Only 104/2719 tx project names match (4%) — transactions span many more projects than just 2026 registry |
| `rents.PROJECT_EN` → `projects.PROJECT_EN` | ⚠️ Very weak | Only 2/1640 rent project names match |
| `lands.PROJECT_NUMBER` → `projects.PROJECT_NUMBER` | ❌ Broken | Completely different number spaces |
| `valuations` → any other file | ❌ No key | No shared identifier |
| `AREA_EN` across transactions/rents/lands/valuations | ✅ Partial | 147/295 area names shared between tx and rents; area name varies slightly |

### AREA_EN Consistency
| Pair | Shared / Total union |
|---|---|
| transactions ↔ rents | 147 / 295 (50%) — same market, different sub-area granularity |
| transactions ↔ lands | 152 / 356 (43%) |
| transactions ↔ valuations | 137 / 283 (48%) |

The overlap is partial because DLD uses slightly different area name strings across systems, and the geographic scope of each register differs (lands covers all parcels, rents/tx cover transacted properties only).

### Root Cause of 86% Null DEVELOPER_EN in Transactions

The enrichment pipeline joins `transactions.PROJECT_EN_KEY` → `projects.PROJECT_EN_KEY`. Of the 2,719 unique project names in transactions, only 104 (4%) match the 187 projects in the projects file. The projects file contains only 2026-registered new projects; transactions include sales of any property ever — the vast majority reference older projects or standalone properties.

**There is no feasible fix without a complete historical projects registry.** Options:
1. Accept 14% developer attribution coverage and mark others as "Unknown"
2. Supplement with a full DLD historical projects dataset

---

## 8. Data Quality Summary

| Issue | File(s) | Severity | Recommendation |
|---|---|---|---|
| DEVELOPER_NUMBER key spaces disjoint | developers ↔ projects | 🔴 Critical | No reliable join exists; treat developers as standalone |
| PROJECT_NUMBER key spaces disjoint | lands ↔ projects | 🔴 Critical | Join on PROJECT_EN name only |
| 86% null DEVELOPER_EN in transactions | transactions | 🔴 Critical | Historical projects file needed |
| ~100% null DEVELOPER_EN in rents | rents | 🔴 Critical | PROJECT_EN 75% null, no fix possible |
| ACTUAL_AREA outlier (373M sqm) | rents | 🔴 Critical | Filter ACTUAL_AREA < 10,000 before rent/sqm calc |
| ACTUAL_AREA outliers (52 records >10M sqm) | lands | 🟡 Medium | 1 data error (2.6B sqm → remove); 7 zone-area duplicates (use with caution); 44 legitimately large gov/industrial parcels (keep). Filter < 1M sqm for per-parcel area calcs |
| Snapshot covers 2026 only | all files | 🟡 Medium | Cannot show year-over-year trends |
| MASTER_PROJECT_EN 99–100% null | all files | 🟡 Medium | Drop column from all pipelines |
| COMPLETION_DATE 99% null | projects | 🟡 Medium | Use END_DATE as planned completion proxy |
| ROOMS 97% null | rents | 🟡 Medium | Drop from bedroom analysis |
| PARKING 98% null | rents | 🟡 Medium | Drop |
| PRJ_TYPE_EN always "Normal" | projects | 🟢 Low | Drop |
| ZONE_EN always "Dubai" | lands | 🟢 Low | Drop |
| LEGAL_STATUS_EN 99% null | developers | 🟢 Low | Drop |
| LICENSE_TYPE_EN 79% null | developers | 🟢 Low | Low utility |
| 6 developers already expired | developers | 🟢 Low | Flag in UI if showing developer status |
| Portfolio Mortgage TRANS_VALUE = total/n | transactions | ℹ️ Info | Each row is an equal share; summing is correct |
| CONTRACT_AMOUNT ≈ ANNUAL_AMOUNT | rents | ℹ️ Info | 90% identical; use ANNUAL_AMOUNT for yield calc |
| ACTUAL_WORTH ≈ PROPERTY_TOTAL_VALUE | valuations | ℹ️ Info | Equal in 78% of cases; use ACTUAL_WORTH as market value |

---

## 9. What Each File Can Reliably Power

| Use Case | File(s) | Confidence |
|---|---|---|
| Sales market KPIs (volume, value, price/sqm) | transactions (Sales) | ✅ High |
| Area-level price trends | transactions | ✅ High |
| Off-plan vs Ready split | transactions, lands | ✅ High |
| Property type breakdown | transactions, rents | ✅ High |
| Rental market (new contracts) | rents (VERSION_EN=New) | ✅ High |
| Rental market (renewals vs new) | rents | ✅ High |
| Gross yield (rent/price) | transactions + rents by area | ⚠️ Medium (area-level only, not per-project) |
| Developer pipeline (project count, units, value) | projects | ✅ High (2026 cohort only) |
| Developer completion status | projects | ✅ High (2026 cohort only) |
| Developer sales attribution | transactions + projects | ❌ Low (86% null) |
| Property valuation benchmarks | valuations | ⚠️ Medium (land-heavy, not units) |
| Mortgage market activity | transactions (Mortgage groups) | ✅ High (if NOT joining to developer) |
| Mortgage reporting by month / procedure | transactions (Mortgage Registration, Portfolio Mortgage, Delayed Mortgage) | ✅ High |
| Mortgage facility value totals | transactions (Mortgage groups) | ✅ High |
| Mortgage transaction counts / average facility size | transactions (Mortgage groups) | ⚠️ Medium (dedupe Portfolio Mortgage by `TRANSACTION_NUMBER`) |
| Land type / free-hold breakdown | lands | ✅ High |
| Parcel-level property lookup | lands | ✅ High |
| Developer entity validation | developers | ⚠️ Medium (2026 cohort, no history) |

### Mortgage Reporting Note

Yes — mortgage can be reported reliably from the transactions file, but the metric definition matters:

- **Count of mortgage events**: use Mortgage-group rows, but for `Portfolio Mortgage Registration` count **unique `TRANSACTION_NUMBER`**, not raw rows.
- **Total mortgage value**: summing row-level `TRANS_VALUE` is valid, including portfolio mortgages, because each portfolio facility is split across its property rows and the row sum reconstructs the total facility amount.
- **Average mortgage size**: compute at the transaction level, not the row level. For portfolio mortgages, aggregate to one row per `TRANSACTION_NUMBER` first.
- **Breakdowns that work well**: monthly trend, procedure type mix, area mix, property type mix, Ready vs Off-Plan split.
- **Breakdowns that remain weak**: developer-level mortgage reporting, because `PROJECT_EN` is sparse and developer enrichment mostly fails.
