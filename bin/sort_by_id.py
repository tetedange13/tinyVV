#!/usr/bin/env python3


import polars as pl
import sys
from os.path import basename
from time import perf_counter


if __name__ == "__main__":
    # 2 args = LAKE_PATH and parquet_path
    LAKE = sys.argv[1]
    pq_path = sys.argv[2]

    start = perf_counter()

    in_pq = pl.scan_parquet(pq_path)
    col_names = in_pq.collect_schema().names()

    # Specific to 'uniq_variants/':
    if 'chr' in col_names and 'pos' in col_names and 'ref' in col_names and 'alt' in col_names:
        in_pq = in_pq.with_columns(
            pl.concat_str(
                [
                    pl.col('chr'),
                    pl.col('pos').cast(str),
                    pl.col('ref'),
                    pl.col('alt'),
                ],
                separator="-",
            ).alias("CHROMPOSREFALT")
        )

    in_pq.sort(by='id'
        ).sink_parquet(
            f"{LAKE}/genotypes/sorted/{basename(pq_path)}",
            compression='zstd',
        )
    print(f"Sort by 'id' took {perf_counter()-start} seconds")
