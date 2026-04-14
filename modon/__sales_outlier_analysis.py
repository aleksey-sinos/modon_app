import polars as pl, sys
sys.path.insert(0, '.')
from src.loading import load_csvs_to_polars, get_df_by_prefix
from src.cleaning import prepare_transactions

dfs = load_csvs_to_polars()
tx = prepare_transactions(get_df_by_prefix(dfs, 'transactions'))
valid = tx.filter(pl.col('IS_SALES') & pl.col('IS_VALID_VALUE_AREA'))
col = valid['PRICE_PER_SQM'].drop_nulls()

mean_val   = col.mean()
median_val = col.median()
p25   = col.quantile(0.25)
p75   = col.quantile(0.75)
p95   = col.quantile(0.95)
p99   = col.quantile(0.99)
max_v = col.max()

print(f"Count : {len(col):,}")
print(f"Mean  : {mean_val:,.0f}")
print(f"Median: {median_val:,.0f}")
print(f"P25   : {p25:,.0f}")
print(f"P75   : {p75:,.0f}")
print(f"P95   : {p95:,.0f}")
print(f"P99   : {p99:,.0f}")
print(f"Max   : {max_v:,.0f}")

iqr   = p75 - p25
fence = p75 + 3 * iqr
print(f"\nIQR          : {iqr:,.0f}")
print(f"3xIQR fence  : {fence:,.0f}")

outliers = valid.filter(pl.col('PRICE_PER_SQM') > fence)
print(f"Outliers     : {outliers.height:,}  ({outliers.height/len(col)*100:.2f}%)")

outlier_sum = outliers['PRICE_PER_SQM'].drop_nulls().sum()
total_sum   = col.sum()
print(f"Outlier share of sum: {outlier_sum/total_sum*100:.1f}%")

print("\nOutliers by PROP_TYPE_EN:")
breakdown = (
    outliers.group_by('PROP_TYPE_EN')
    .agg(
        pl.len().alias('count'),
        pl.col('PRICE_PER_SQM').median().alias('median_psqm'),
        pl.col('PRICE_PER_SQM').max().alias('max_psqm'),
    )
    .sort('count', descending=True)
)
for r in breakdown.iter_rows(named=True):
    print("  {:>6,} records | median {:>10,.0f} | max {:>12,.0f} | {}".format(
        r['count'], r['median_psqm'], r['max_psqm'], r['PROP_TYPE_EN']
    ))

print("\nArea distribution among outliers:")
area_bins = outliers.with_columns(
    pl.when(pl.col('EFFECTIVE_AREA') < 1).then(pl.lit('<1 sqm'))
    .when(pl.col('EFFECTIVE_AREA') < 5).then(pl.lit('1-5 sqm'))
    .when(pl.col('EFFECTIVE_AREA') < 15).then(pl.lit('5-15 sqm'))
    .otherwise(pl.lit('>=15 sqm'))
    .alias('area_bin')
).group_by('area_bin').agg(
    pl.len().alias('count'),
    pl.col('PRICE_PER_SQM').median().alias('median_psqm'),
).sort('count', descending=True)
for r in area_bins.iter_rows(named=True):
    print("  {:>8} | {:>6,} records | median {:>12,.0f}".format(r['area_bin'], r['count'], r['median_psqm']))

print("\nTop 20 worst outliers:")
top = (
    outliers.select(['PROP_TYPE_EN','PROJECT_EN','AREA_EN','EFFECTIVE_AREA','TRANS_VALUE','PRICE_PER_SQM'])
    .sort('PRICE_PER_SQM', descending=True)
    .head(20)
)
for r in top.iter_rows(named=True):
    print("  {:>12,.0f} AED/sqm | area {:>8.2f} sqm | value {:>12,.0f} AED | {:<22} | {}".format(
        r['PRICE_PER_SQM'], r['EFFECTIVE_AREA'], r['TRANS_VALUE'],
        str(r['PROP_TYPE_EN'] or ''), str(r['PROJECT_EN'] or '')
    ))
