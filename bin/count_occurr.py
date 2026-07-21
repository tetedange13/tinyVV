#!/usr/bin/env python3


import polars as pl
import sys
from time import perf_counter


def count_occurr(LAKE):
    """
    Compute occurrences of all variants from all samples in lake

    Use 'genotypes/*' instead of 'variants/*'
    Allow to have list of samples supporting occurrence

    WARN: Order of variants is random in 'occurr.parquet' ???
          Should not matter ???
    """

    concat_samples = pl.scan_parquet(f"{LAKE}/genotypes/samples/*.parquet"
        ).select(['id', 'sample'])
    #print(concat_samples.head().collect())  # DEBUG

    ctx = pl.SQLContext(frames={'all_samples': concat_samples})
    query_occurr = """
    SELECT
        id,
        count(*) AS occurrence,
        STRING_AGG(sample) AS found_in,
    FROM all_samples
    GROUP BY id;
    """
    lf = ctx.execute(query_occurr)

    # Cast 'found_in' col to 'list(str)' dtype
    lf = lf.with_columns(
        pl.concat_list([pl.col('found_in')])
    ).sort(by='id'
    ).sink_parquet(
        f"{LAKE}/occurrences/all_samples.parquet",
        compression='zstd',
    )


if __name__ == "__main__":
    # 1 arg = LAKE_PATH
    start = perf_counter()
    count_occurr(sys.argv[1])
    print(f"Occurrence computation took {perf_counter()-start} seconds")
