import polars as pl
import os.path as osp


def lake_schema(LAKE):
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    # Rename cols with '.' inside, cuz not supported:
    rename_dict = {c:c.replace('.', '_') for c in ann.collect_schema().names() if '.' in c}
    return ann.rename(rename_dict).collect_schema()


def lake_data(LAKE, samples_list, cols_list=None):
    list_in = [f"{LAKE}/genotypes/samples/{s}.parquet" for s in samples_list]
    sample_parquets = { f"{osp.splitext(osp.basename(x))[0]}":pl.scan_parquet(x) for x in list_in }

    # Same but add 'variants' and 'ann' for context passing:
    all_parquets = { f"{osp.splitext(osp.basename(x))[0]}":pl.scan_parquet(x) for x in list_in }
    all_parquets["v"] = pl.scan_parquet(f'{LAKE}/uniq_variants/*.parquet')

    # Same for annot but 1st rename cols with '.' inside, cuz not supported:
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    rename_dict = {c:c.replace('.', '_') for c in ann.collect_schema().names() if '.' in c}
    all_parquets["ann"] = ann.rename(rename_dict)

    # Register all lf in global namespace: ctx = pl.SQLContext(register_globals=True)
    ctx = pl.SQLContext(frames=all_parquets)
    
    first_sample = list(sample_parquets.keys())[0]
    gt_cols = ','.join([f"{x}.gt AS format_{x}_GT" for x in sample_parquets.keys()])
    if cols_list:
        ann_cols = ','.join([a for a in cols_list])
    else:
        ann_cols = ','.join([a for a in all_parquets["ann"].collect_schema().names() if not a.endswith('id')])
    union_all_samples = '\n'.join([ f"UNION SELECT id FROM {other}" for other in list(sample_parquets.keys())[1:] ])
    join_gt_samples = '\n'.join([ f"LEFT JOIN {other} ON id={other}.id" for other in list(sample_parquets.keys()) ])
    # MEMOs:
    # * Diff colnames between variantplan and vcf2pq (colname vs info_colname)
    # * Cols like "info_Gene.refGene" raise and error (caused by '.')
    # * Intermediate query collect all uniq variants id for requested samples
    #   For later 'LEFT JOIN' -> result in a 'FULL JOIN'
    # * UNION result is random, not sure why
    #   -> ENH, do it with pl.Df.unique() instead ?
    query_lf = f"""
    WITH cte_gt AS (
        SELECT
            id,
        FROM {first_sample}
            {union_all_samples}
    )

    SELECT
        chr as chromosome,
        pos AS position,
        ref AS reference,
        alt AS alternate,
        {gt_cols},
        {ann_cols},

        FROM cte_gt
        {join_gt_samples}
            LEFT JOIN v
            ON id=v.id
            LEFT JOIN ann
            ON id=ann.id
    """
    print(query_lf)
    return ctx.execute(query_lf)


def count_occurr(LAKE):
    # Compute occurrences of all variants from all samples in lake
    # ENH: Do it on 'variants/*.parquet' instead ?
    #      This way could have 'chr,pos,ref,alt' too
    all_samples = pl.scan_parquet(f"{LAKE}/genotypes/samples/*.parquet")

    ctx = pl.SQLContext(frames={'all_samples': all_samples})
    query_occurr = """
    SELECT
        id id,count(*)
    FROM all_samples
    GROUP BY id;
    """
    print(query_occurr)
    return ctx.execute(query_occurr)
