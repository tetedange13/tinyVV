import polars as pl
#pl.Config.set_engine_affinity("streaming")


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
        selected_cols = ['id', 'gt', 'gq', 'ad', 'dp', 'ab']
        rename_dict = { c:f"{s}_{c.upper()}" for c in selected_cols if c != 'id' }
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
    # WARN: 'concat diag' not doing a full join
    #joint_gt = pl.concat(pqs_list, how='diagonal')
    all_parquets = { 'joint_gt': joint_gt }

    # Add 'variants' for context passing:
    all_parquets["c"] = pl.scan_parquet(f'{LAKE}/occurrences/*.parquet')
    all_parquets["v"] = pl.scan_parquet(f'{LAKE}/uniq_variants/*.parquet')
    # Same for annot but 1st rename cols with '.' inside, cuz not supported:
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    if cols_list:
        ann = ann.select(['id'] + cols_list)
    rename_dict = {c:c.replace('.', '_') for c in ann.collect_schema().names() if '.' in c}
    all_parquets["ann"] = ann.rename(rename_dict)

    # Register all lf in global namespace: ctx = pl.SQLContext(register_globals=True)
    ctx = pl.SQLContext(frames=all_parquets)
    
    gt_cols = ','.join([f"{x}_GT" for x in samples_list])
    gq_cols = ','.join([f"{x}_GQ" for x in samples_list])
    ad_cols = ','.join([f"{x}_AD" for x in samples_list])
    dp_cols = ','.join([f"{x}_DP" for x in samples_list])
    ab_cols = ','.join([f"{x}_AB" for x in samples_list])
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
        occurrence,
        found_in,
        {gt_cols},
        {gq_cols},
        {ad_cols},
        {dp_cols},
        {ab_cols},
        {ann_cols},

        FROM joint_gt
            LEFT JOIN c
            ON id=c.id
            LEFT JOIN v
            ON id=v.id
            LEFT JOIN ann
            ON id=ann.id
    """
    print(query_lf)
    return ctx.execute(query_lf)


if __name__ == "__main__":
    sliced = lake_data("parquets_lake2/", ["HG001", "HG002", "HG003", "HG004"])[0:100]

    # Show query exec
    # MEMO: Only 'stream' engine has 'physical' plan
    # MEMO: Run code with 'DISPLAY=":0"'
    sliced.show_graph(
        engine="streaming",
        plan_stage="physical",
        show=False,
        output_path="plan.png",
    )

    # Collect and profile query:
    partial, profile_df = sliced.profile()
    profile_df.with_columns([
    (pl.col("end") - pl.col("start")).alias("duration")
]).with_columns([
    (pl.col("duration") / pl.col("duration").sum() * 100).alias("percent_total")
]).write_csv('profile.tsv', separator="\t")
