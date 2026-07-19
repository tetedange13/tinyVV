#!/usr/bin/env python3


import polars as pl
import sys
from os.path import basename
from time import perf_counter


if __name__ == "__main__":
    # 2 args = LAKE_PATH and parquet_path
    LAKE = sys.argv[1]
    in_pq = sys.argv[2]

    start = perf_counter()
    pl.scan_parquet(in_pq
        ).sort(by='id'
        ).sink_parquet(f"{LAKE}/genotypes/sorted/{basename(in_pq)}")
    print(f"Sort took {perf_counter()-start} seconds")
