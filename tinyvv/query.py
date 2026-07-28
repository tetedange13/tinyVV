import polars as pl
import sys
pl.Config.set_engine_affinity("streaming")


def lake_schema(LAKE):
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    # Rename cols with '.' inside, cuz not supported:
    rename_dict = {c:c.replace('.', '_') for c in ann.collect_schema().names() if '.' in c}
    return ann.rename(rename_dict).collect_schema()


def join_gt_frames(LAKE, samples_list, cols_list=None):

    # Build a list of 'genotypes' pq, with renamed cols for join:
    pqs_list = []
    for s in samples_list:
        pq_path = f"{LAKE}/genotypes/samples/{s}.parquet"
        selected_cols = ['id', 'gt', 'gq', 'ad', 'dp', 'ab']
        #selected_cols = ['id', 'gt', 'gq']  # DEBUG
        rename_dict = { c:f"{s}_{c.upper()}" for c in selected_cols if c != 'id' }
        pq_to_join = pl.scan_parquet(pq_path).select(selected_cols).rename(rename_dict)
        pqs_list.append(pq_to_join.set_sorted('id'))

    all_parquets = { f"{samples_list[i]}":pq for i, pq in enumerate(pqs_list) }
    ctx = pl.SQLContext(frames=all_parquets)

    # Full join on id:
    # MEMO: 'NATURAL' means 'join on common cols + coalesce'
    # WARN: Should I make sure 'id' is the only common col ???
    join_gt_expr = '\n'.join([ f"NATURAL FULL JOIN {samples_list[other+1]}" for other,_ in enumerate(pqs_list[1:]) ])

    # WARN: 'concat diag' not doing a full join
    #joint_gt = pl.concat(pqs_list, how='diagonal')

    query_join = f"""
    SELECT *
        FROM {samples_list[0]}
        {join_gt_expr}
    """

    print(query_join)
    joint_gt = ctx.execute(query_join)
    #joint_gt.sink_parquet("joint_gt.parquet")  # DEBUG

    return joint_gt


def lake_data(LAKE, samples_list, cols_list=None):
    # Add joint_gt:
    all_parquets = {"joint_gt": join_gt_frames(LAKE, samples_list, cols_list)}

    # Add 'variants' for context passing:
    all_parquets["c"] = pl.scan_parquet(f'{LAKE}/occurrences/*.parquet')
    all_parquets["v"] = pl.scan_parquet(f'{LAKE}/uniq_variants/*.parquet')
    # Same for annot:
    ann = pl.scan_parquet(f'{LAKE}/annotations/*.parquet')
    if cols_list:
        ann = ann.select(['id'] + cols_list)
    all_parquets["ann"] = ann

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
        joint_gt.id,
        CHROMPOSREFALT,
        occurrence,
        found_in,
        {gt_cols},
        {gq_cols},
        {ad_cols},
        {dp_cols},
        {ab_cols},
        {ann_cols},

        FROM joint_gt
            LEFT JOIN c ON id=c.id
            LEFT JOIN v ON id=v.id
            LEFT JOIN ann ON id=ann.id
    """
    print(query_lf)
    joint_all = ctx.execute(query_lf)
    #joint_all.sink_parquet("joint_all.parquet")  # DEBUG
    return joint_all


if __name__ == "__main__":
    LAKE = sys.argv[1]
    samplesList = sys.argv[2]
    firstSample = samplesList.split(',')[0]
    GT_cols = [f"{s}_GT" for s in samplesList.split(',')]

    full_data = lake_data(LAKE, samplesList.split(','))
    if len(sys.argv) == 4:
        full_data.select(
            ['CHROMPOSREFALT']+GT_cols
        ).sink_csv(
            sys.argv[3],
            include_header=False,
            separator="\t",
            null_value="0/0",
        )
    sliced = full_data
    # Filter
    #sliced = sliced.filter(pl.col(f"{firstSample}_GT")=="0/1")
    # Filter2: harder cuz all joins have to happen first
    sliced = sliced.filter(pl.col(f"{firstSample}_GT").eq("0/1") & pl.col("SYMBOL").eq("0/1"))
    # Slice
    sliced = sliced[0:50000]
    print(sliced.explain(optimized=True))
    print(sliced.collect_schema())

    # Show query exec
    # MEMO: Only 'stream' engine has 'physical' plan
    # MEMO: Run code with 'DISPLAY=":0"'
    sliced.show_graph(
        engine="streaming",
        plan_stage="physical",
        show=False,
        output_path="plan.png",
    )

    # Simply collect:
    print(sliced.collect())
    exit()

    # Collect and profile query:
    # WARN: '.profile()' works only with 'in-memory' engine
    #       Cf: https://github.com/pola-rs/polars/issues/28274
    partial, profile_df = sliced.profile(engine="in-memory")
    profile_df.with_columns([
    (pl.col("end") - pl.col("start")).alias("duration")
]).with_columns([
    (pl.col("duration") / pl.col("duration").sum() * 100).alias("percent_total")
]).write_csv('profile.tsv', separator="\t")
