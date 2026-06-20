import logging
import dash_ag_grid as dag
from dash import Dash, Input, Output, dcc, html, no_update, callback
import polars as pl
import os.path as osp
import yaml
# LOCAL imports
from .filtering import make_filter_expr_list
from .styling import colorize_GT, aggKey_to_func
from .utils import parse_args, nice_dict
from .query import lake_data, lake_schema
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

    # Parse arguments:
    args = parse_args()

    config_OK = args.config and osp.isfile(args.config)
    if config_OK:
        logging.info("Found 'sample.yaml' -> loading conf")
        with open(args.config, 'r') as conf_file:
            conf = yaml.safe_load(conf_file)
        logging.debug(nice_dict(conf))
    else:
        logging.warning("No 'sample.yaml' found near input 'sample.parquet'")

    # Add columns selected by user:
    if config_OK and 'col_selection' in conf.keys():
        selected_cols = conf['col_selection']
        # Also add cols declared in 'agg_in_tooltip' section:
        if 'agg_in_tooltip' in conf.keys():
            selected_cols += conf['agg_in_tooltip'].keys()
            selected_cols += [x for sublist in conf['agg_in_tooltip'].values() for x in sublist]
            selected_cols = list(dict.fromkeys(selected_cols))  # De-duplicate
        # Do we need to add col from 'sort' section ???

    # Add/process cols depending on input type:
    if args.parquet:  # Single pq input
        assert osp.isfile(args.parquet), f"Provided parquet '{args.parquet}' not found"
        DATA_SOURCE = pl.scan_parquet(args.parquet)
        full_schema = DATA_SOURCE.collect_schema()
        all_ann_cols = [ c for c in full_schema.names() if c.startswith('info_') ]
        # Find genotype columns by their name:
        GT_cols = [ c for c in full_schema.names() if c.startswith('format_') and c.endswith('_GT') ]
        # Fix cols:
        DATA_SOURCE = DATA_SOURCE.with_columns(
            pl.col("alternate").list.join(separator="")
            )

    elif args.input:  # Lake input
        # WARN: Bellow 'full_schema' only contains ANN cols...
        full_schema = lake_schema(args.lake)
        all_ann_cols = [c for c in full_schema.names() if not c.endswith('id')]
        GT_cols = [ f"format_{s}_GT" for s in args.input ]
        if config_OK and 'col_selection' in conf.keys():
            cols_list = selected_cols
        else:
            cols_list = all_ann_cols
        DATA_SOURCE = lake_data(args.lake, args.input, cols_list)


    # FROM HERE: should be independent of input type (lake or single pq)
    if args.show_cols:
        logger.info("List INFO columns and exit:")
        [print(col) for col in all_ann_cols]
        exit()

    # Create 'chr-pos-ref-alt' col:
    to_concat = [
        'chromosome',
        'position',
        'reference',
        'alternate',
    ]
    DATA_SOURCE = DATA_SOURCE.with_columns(
        pl.concat_str(
            to_concat,
            separator="-"
        ).alias("#CHROMPOSREFALT")
    ).drop(to_concat)

    # wanted_cols:
    # Also add all 'format' ones ? (eg: DP)
    wanted_cols = ["#CHROMPOSREFALT"]
    wanted_cols += GT_cols

    if config_OK and 'col_selection' in conf.keys():
        wanted_cols += selected_cols
    else:
        wanted_cols += all_ann_cols

   # WARN: vcf2pq puts 'list[str]' dtype for all INFO cols...
    #       -> Have to use '.list.join' + '.cast' to have proper sort
    # WARN2: Cast works only for int score (what about 'float' score)
    if config_OK and 'sort' in conf.keys():
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
    # ENH: Auto put DP,GQ as tooltip for 1st GT col ? (done in Achab)
    for a_col in columnDefs:
        if a_col["field"] in GT_cols:
            a_col["cellStyle"] = colorize_GT()

    # Add hyperlink to 'chr-pos-ref-alt' col:
    # ENH: Use MobiDetails instead (API key required to query variant)
    # MEMO: 1st line declares customCompon and is common to tooltip compon
    custom_compon = """var dagcomponentfuncs = (window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {});

dagcomponentfuncs.chrPosRefAltLink = function (props) {
    return React.createElement(
        'a',
        {href: 'https://franklin.genoox.com/clinical-db/variant/snp/' + props.value + '-BUILD'},
        props.value
    );
};

"""
    with open('tinyvv/assets/dashAgGridComponentFunctions.js', 'w') as compon_file:
        compon_file.write(custom_compon.replace('BUILD', args.build))

    # ENH: Do not parcours colDef twice
    for a_col in columnDefs:
        if a_col["field"] == "#CHROMPOSREFALT":
            # JS func defined in 'dashAgGridComponentFunctions.js':
            a_col["cellRenderer"] = "chrPosRefAltLink"

    # Add tooltips:
    if config_OK and 'agg_in_tooltip' in conf.keys():
        ## Then aggKey_to_func() writes a JS func for each col where tooltip is added:
        to_hide = [x for sublist in conf['agg_in_tooltip'].values() for x in sublist]
        for a_col in columnDefs:
            col_name = a_col["field"]
            if col_name in conf['agg_in_tooltip'].keys():
                a_col["tooltipField"] = col_name  # Mandatory
                a_col["tooltipComponent"] = aggKey_to_func(conf['agg_in_tooltip'], col_name)
            # Hide columns whose data are in tooltip:
            if col_name in to_hide:
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
        rows_count_df = ldf.select('#CHROMPOSREFALT').with_row_index().last().select('index').collect()
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
