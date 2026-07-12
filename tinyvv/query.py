import polars as pl
import os.path as osp


def lake_schema(LAKE):
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    # Rename cols with '.' inside, cuz not supported:
    rename_dict = {c:c.replace('.', '_') for c in ann.collect_schema().names() if '.' in c}
    return ann.rename(rename_dict).collect_schema()


def lake_data(LAKE, samples_list, cols_list=None):
    # Build a list of 'genotypes' pq, with renamed cols for join:
    pqs_list = []
    for s in samples_list:
        pq_path = f"{LAKE}/genotypes/samples/{s}.parquet"
        selected_cols = ['id','gt', 'ad']
        rename_dict = { c:f'format_{s}_{c.upper()}' for c in selected_cols if c != 'id' }
        pq_to_join = pl.scan_parquet(pq_path).select(selected_cols).rename(rename_dict)
        pqs_list.append(pq_to_join)

    # Full join on id:
    # ENH: Find a way to do that in SQL bellow ???
    joint_gt = pqs_list[0]  # Init to 1st pq
    for pq in pqs_list[1:]:
        joint_gt = joint_gt.join(
            pq,
            how='full',
            on='id',
            coalesce=True,
            maintain_order='left_right'
        )
    all_parquets = { 'joint_gt': joint_gt }

    # Add 'variants' for context passing:
    all_parquets["v"] = pl.scan_parquet(f'{LAKE}/uniq_variants/*.parquet')
    # Same for annot but 1st rename cols with '.' inside, cuz not supported:
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    rename_dict = {c:c.replace('.', '_') for c in ann.collect_schema().names() if '.' in c}
    all_parquets["ann"] = ann.rename(rename_dict)

    # Register all lf in global namespace: ctx = pl.SQLContext(register_globals=True)
    ctx = pl.SQLContext(frames=all_parquets)
    
    gt_cols = ','.join([f"format_{x}_GT" for x in samples_list])
    if cols_list:
        ann_cols = ','.join([a for a in cols_list])
    else:
        ann_cols = ','.join([a for a in all_parquets["ann"].collect_schema().names() if not a.endswith('id')])

    query_lf = f"""
    SELECT
        chr as chromosome,
        pos AS position,
        ref AS reference,
        alt AS alternate,
        {gt_cols},
        {ann_cols},

        FROM joint_gt
            LEFT JOIN v
            ON id=v.id
            LEFT JOIN ann
            ON id=ann.id
    """
    print(query_lf)
    return ctx.execute(query_lf)


def count_occurr(LAKE):
    # Compute occurrences of all variants from all samples in lake
    # MEMO: Keep using 'genotypes/*' instead of 'variants/*'
    #       So that can have list of samples supporting occurrence
    ctx = pl.SQLContext(frames={'all_samples': pl.scan_parquet(f"{LAKE}/genotypes/samples/*.parquet")})
    query_occurr = """
    SELECT
        id,
        count(*),
        STRING_AGG(sample),
    FROM all_samples
    GROUP BY id;
    """
    return ctx.execute(query_occurr)
