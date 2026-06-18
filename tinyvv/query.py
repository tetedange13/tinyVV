import polars as pl
import os.path as osp


def lake_schema(LAKE):
    return pl.scan_parquet(f'{LAKE}/annotations/*').collect_schema()


def lake_data(LAKE, samples_list, cols_list=None):
    list_in = [f"{LAKE}/genotypes/samples/{s}.parquet" for s in samples_list]
    sample_parquets = { f"{osp.splitext(osp.basename(x))[0]}":pl.scan_parquet(x) for x in list_in }

    # Same but add 'variants' and 'ann' for context passing:
    all_parquets = { f"{osp.splitext(osp.basename(x))[0]}":pl.scan_parquet(x) for x in list_in }
    all_parquets["v"] = pl.scan_parquet(f'{LAKE}/uniq_variants/*')
    all_parquets["ann"] = pl.scan_parquet(f'{LAKE}/annotations/*')

    # Register all lf in global namespace: ctx = pl.SQLContext(register_globals=True)
    ctx = pl.SQLContext(frames=all_parquets)
    
    first_sample = list(sample_parquets.keys())[0]
    gt_cols = ','.join([f"{x}.gt AS format_{x}_GT" for x in sample_parquets.keys()])
    if cols_list:
        ann_cols = ','.join([a for a in cols_list])
    else:
        ann_cols = ','.join([a for a in all_parquets["ann"].collect_schema().names() if not a.endswith('id')])
    join_other_samples = '\n'.join([ f"LEFT JOIN {other} ON {first_sample}.id={other}.id" for other in list(sample_parquets.keys())[1:] ])

    # MEMOs:
    # * Diff colnames between variantplan and vcf2pq (colname vs info_colname)
    # * Cols like "info_Gene.refGene" raise and error (caused by '.')
    query_lf = f"""
    SELECT
        chr as chromosome,
        pos AS position,
        ref AS reference,
        alt AS alternate,
        {gt_cols},
        {ann_cols},
    FROM {first_sample}
    {join_other_samples}
            LEFT JOIN v
            ON {first_sample}.id=v.id
            LEFT JOIN ann
            ON {first_sample}.id=ann.id
    """
    print(query_lf)
    return ctx.execute(query_lf)
