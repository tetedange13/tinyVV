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
    ctx = pl.SQLContext(frames={'all_samples': pl.scan_parquet(f"{LAKE}/genotypes/samples/*.parquet")})
    query_occurr = """
    SELECT
        id,
        count(*),
        STRING_AGG(sample),
    FROM all_samples
    GROUP BY id;
    """
    ctx.execute(
        query_occurr
    ).rename({'len':'occurrence'}
    ).sink_parquet(f"{LAKE}/occurrences/all_samples.parquet")


if __name__ == "__main__":
    # 1 arg = LAKE_PATH
    start = perf_counter()
    count_occurr(sys.argv[1])
    print(f"Took {perf_counter()-start} seconds")
