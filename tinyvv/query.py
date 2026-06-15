import polars as pl


def source_data():
    lake = "./lake"
    s = pl.scan_parquet(f'{lake}/genotypes/samples/*')
    v = pl.scan_parquet(f'{lake}/uniq_variants/*')
    a = pl.scan_parquet(f'{lake}/annotations/*')
    # Register all lf in global namespace: ctx = pl.SQLContext(register_globals=True)
    #ctx = pl.SQLContext(frames={"a": a, "s": s, "v": v})
    # string_agg() is equivalent to duckdb's list()
    #    s.id,first(COLUMNS(v.*)),first(COLUMNS(a.*)),stringagg(COLUMNS(['sample','gt','dp']) order by sample asc)

    # Collect 'first' for all columns from 'variants' and 'annotations' tables:
    v_cols = ','.join([f"first({vcol})" for vcol in v.collect_schema().names() if vcol!='id'])
    a_cols = ','.join([f"first('{acol}').alias('{acol}')" for acol in a.collect_schema().names() if acol not in ('annovar_id','id','dp')])

    query_lf = f"""
    SELECT
        s.id,
        STRING_AGG(sample order by sample asc),
        STRING_AGG(gt order by sample asc),
        {v_cols},
        {a_cols},
    FROM s
        LEFT JOIN v
        ON s.id=v.id
            LEFT JOIN a
            ON s.id=a.id
    GROUP BY s.id
    """
    #toto = ctx.execute(query_lf)
    toto = pl.sql(query_lf)
    print(toto.collect_schema().names())
    print(toto.head().collect()); exit()
