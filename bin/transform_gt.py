#!/usr/bin/env python3


import polars as pl
import sys
from os.path import basename
from time import perf_counter


if __name__ == "__main__":
    # 1 arg = parquet_path
    pq_path = sys.argv[1]
    # ENH: In case manage to convert 'GT' to 'categorical'
    #      gt_dtype = pl.Categories(name="gt", namespace="org.gt", physical=pl.UInt8)
    #      ).with_columns(pl.col('gt').cast(str).replace(dict_gt).cast(pl.Categorical(gt_dtype))
    dict_gt = {"1":"0/1", "2":"1/1"}

    # - Convert '1'->'0/1' and '2'-> '1/1' 
    # - Compute AB (VAF) column
    # - Sort by 'id'

    start = perf_counter()
    pl.scan_parquet(pq_path
    ).with_columns(pl.col('gt').cast(str).replace(dict_gt)
    ).with_columns(ab=pl.col('ad').list[1]/pl.col('dp')
    ).sort(by='id'
    ).sink_parquet(
        pq_path.replace('/samples/', '/sorted/'),
        compression='zstd',
    )

    print(f"Genotype parquet transformation took {perf_counter()-start} seconds")
