#!/usr/bin/env python3


import sys
import json
import polars as pl
import variantplaner
from variantplaner import ContigsLength


if __name__ == "__main__":
    inTsv = sys.argv[1]
    chrom2length_file = sys.argv[2]
    outPqPath = sys.argv[3]

    # Read chrom_to_len file using dedicated class:
    chrom2length = ContigsLength()
    chrom2length.from_path(chrom2length_file)

    # Read header and force str type for all 'ANN_' cols:
    # Otherwise issues with inferred dtypes for some cols
    header = pl.read_csv(
        inTsv,
        separator="\t",
        has_header=False,
        n_rows=1,
    ).transpose()['column_0'].to_list()
    schema_override = {c:pl.String for c in header if c.startswith('ANN_') or c.startswith('CSQ_')}
    schema_override['POS'] = pl.UInt64

    annotations = pl.scan_csv(
        inTsv,
        schema_overrides=schema_override,
        separator="\t",
        null_values=["."],
    )

    # Turn String cols to List(str):
    # For homogeneity with rest of project
    for a_col in [c for c in schema_override.keys() if c != 'POS']:
        annotations = annotations.with_columns(
            pl.concat_list([pl.col(a_col)])
        )

    # Rename columns variantplaner:
    vp_rename= {
        "CHROM":"chr",
        "POS":"pos",
        "REF":"ref",
        "ALT":"alt",
        "ID":"old_id",
    }
    annotations = annotations.rename(vp_rename)

    # Rename to remove 'prefix' (eg: ANN_ or CSQ_):
    source_colnames = annotations.collect_schema().names()
    prf_rename = {c:c.replace('ANN_','').replace('CSQ_','') for c in source_colnames if c.startswith('ANN_') or c.startswith('CSQ_')}
    annotations = annotations.rename(prf_rename)

    final_schema = annotations.collect_schema()
    dict_schema = {k:str(final_schema[k]) for k in final_schema}
    print(json.dumps(dict_schema, indent=2))

    # Add variant-planer's variant_id:
    tsv_with_id = variantplaner.normalization.add_variant_id(
        annotations,
        chrom2length.lf,
    ).drop(
        ['chr', 'pos', 'ref', 'alt']
    )
    print(tsv_with_id.head().collect())

    # Write outParquet:
    tsv_with_id.sink_parquet(
       outPqPath,
       compression='zstd'
    )
    print(f"Wrote: {outPqPath}")
