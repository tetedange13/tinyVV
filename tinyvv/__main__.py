import logging
import dash_ag_grid as dag
from dash import Dash, Input, Output, dcc, html, no_update, callback
import polars as pl
import sys
import os.path as osp
import yaml
# LOCAL imports
from .filtering import parse_column_filter, make_filter_expr_list
from .styling import colorize_GT, aggKey_to_func
from .utils import nice_dict
logger = logging.getLogger(__name__)


# MAIN
def main():
    #Output to log file:
    #logging.basicConfig(filename='tinyvv.log', level=logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)

    def scan_ldf(
        filter_model=None,
        columns=None,
        sort_model=None,
        ):
        ldf = DATA_SOURCE
        if columns:
            ldf = ldf.select(columns)
        if filter_model:
            expression_list = make_filter_expr_list(filter_model)
            if expression_list:
                filter_query = None
                for expr in expression_list:
                    if filter_query is None:
                        filter_query = expr
                    else:
                        filter_query &= expr
                ldf = ldf.filter(filter_query)
        return ldf


    in_parquet_path = sys.argv[1]
    root_path = osp.splitext(in_parquet_path)[0]
    attached_yaml = root_path + '.yaml'
    if osp.isfile(attached_yaml):
        logging.info("Found 'sample.yaml' -> loading conf")
        with open(attached_yaml, 'r') as conf_file:
            conf = yaml.safe_load(conf_file)
        logging.debug(nice_dict(conf))

    else:
        logging.warning("No 'sample.yaml' found near input 'sample.parquet'")

    DATA_SOURCE = pl.scan_parquet(in_parquet_path)

    full_schema = DATA_SOURCE.collect_schema()
    all_cols = full_schema.names()
    #logger.debug(all_cols)

    # Find genotype columns by their name:
    GT_cols = []
    for a_col in all_cols:
        if a_col.startswith('format_') and a_col.endswith('_GT'):
            GT_cols.append(a_col)

    wanted_cols = [
        'chromosome',
        'position',
        'reference',
        'alternate'
    ]
    wanted_cols += GT_cols
    wanted_cols += [ c for c in all_cols if c.startswith('info_')]

    # FUTURE: Tooltip pop_freq:

    # WARN: vcf2pq puts 'list[str]' dtype for all INFO cols...
    #       -> Have to use '.list.join' + '.cast' to have proper sort
    # WARN2: Cast works only for int score (what about 'float' score)
    if osp.isfile(attached_yaml) and 'sort' in conf.keys():
        if full_schema[conf['sort'][0]] == pl.List(str):
            # First join list(str) -> str, then cast to int
            DATA_SOURCE = DATA_SOURCE.with_columns(
                pl.col(conf['sort'][0]).list.join(separator="").cast(pl.Int32)
                ).sort(by=conf['sort'][0], descending=conf['sort'][1]
                ).select(wanted_cols)
        else: # just sort
            DATA_SOURCE = DATA_SOURCE.with_columns(
                ).sort(by=conf['sort'][0], descending=conf['sort'][1]
                ).select(wanted_cols)

    else:
        DATA_SOURCE = DATA_SOURCE.select(wanted_cols)

    # Bellow is a kind of assert (FAIL if selected wrong cols):
    logger.info("Show first 10 rows of data:")
    print(DATA_SOURCE.head().collect())

    columnDefs=[{"field": i} for i in wanted_cols]

    # Color GT cols:
    for a_col in columnDefs:
        if a_col['field'] in GT_cols:
            a_col['cellStyle'] = colorize_GT()

    # Add tooltips:
    ## Write 1st line of JS file describing custom tooltip:
    with open('tinyvv/assets/dashAgGridComponentFunctions.js', 'w') as tooltip_file:
        tooltip_file.write("var dagcomponentfuncs = (window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {});\n\n")
    ## Then aggKey_to_func() writes a JS func for each col where tooltip is added:
    if 'agg_in_tooltip' in conf.keys():
        to_hide = [x for sublist in conf['agg_in_tooltip'].values() for x in sublist]
        for a_col in columnDefs:
            if a_col['field'] in conf['agg_in_tooltip'].keys():
                a_col["tooltipField"] = a_col['field']  # Mandatory
                a_col["tooltipComponent"] = aggKey_to_func(conf['agg_in_tooltip'], a_col['field'])
            # Hide columns whose data are in tooltip:
            if a_col['field'] in to_hide:
                a_col["hide"] = True

        logger.info("Wrote 'tinyvv/assets/dashAgGridComponentFunctions.js' for customTooltips")

    logger.debug(nice_dict(columnDefs))

    # Count total rows:
    # MEMO: Select 1st col speed up operation
    #total_rows = DATA_SOURCE.select('chromosome').with_row_index().last().select('index').collect().item()

    app = Dash()

    app.layout = html.Div(
        [
            dcc.Markdown("Infinite scroll with selectable rows"),
            dag.AgGrid(
                id="infinite-grid",
                style={"height": 600, "width": "100%"},
                columnDefs=columnDefs,
                defaultColDef={
                    "sortable": False,
                    "filter": True,
                },
                rowModelType="infinite",
                dashGridOptions={
                    # The number of rows rendered outside the viewable area the grid renders.
                    "rowBuffer": 0,
                    # How many blocks to keep in the store. Default is no limit, so every requested block is kept.
                    "maxBlocksInCache": 1,
                    "rowSelection": {'mode': 'multiRow'},
                    "tooltipShowDelay": 0,
                },
            ),
            dcc.Store(id="filter-model"),
            html.Div(id="infinite-output"),
        ],
        style={"margin": 20},
    )

    @app.callback(
    Output("infinite-grid", "getRowsResponse"),
    Output("filter-model", "data"),
    Input("infinite-grid", "getRowsRequest"),
    Input("infinite-grid", "columnDefs")
    )
    def infinite_scroll(request, columnDefs):
        if request is None:
            return no_update
        columns = [col["field"] for col in columnDefs]
        ldf = scan_ldf(filter_model=request["filterModel"], columns=columns)
        partial = ldf[request["startRow"] : request["endRow"]].collect()
        # Count rows after filter, but handle case where filter return nothing:
        rows_count_df = ldf.select('chromosome').with_row_index().last().select('index').collect()
        if rows_count_df.shape[0] == 0:
            rows_count = 0
        else:
            rows_count = rows_count_df.item()

        return {
            "rowData": partial.to_dicts(),
            "rowCount": rows_count,
        }, request["filterModel"]

    app.run(debug=False)


if __name__ == "__main__":
    main()
