import logging
import dash_ag_grid as dag
from dash import Dash, Input, Output, dcc, html, no_update, callback
import polars as pl
import os.path as osp
import yaml
from time import perf_counter
# LOCAL imports
from .filtering import make_filter_expr_list
from .styling import colorize_GT, aggKey_to_func, format_to_tooltip
from .utils import parse_args, nice_dict
from .query import lake_schema, lake_data
logger = logging.getLogger(__name__)
#pl.Config.set_engine_affinity("streaming")


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
        # Declare 'conf' anyway cuz used for 'agg_in_tooltip' on occurrence, GT:
        conf = {"agg_in_tooltip": {"occurrence": None}}

    # Add columns selected by user:
    if config_OK and 'col_selection' in conf.keys():
        selected_cols = conf['col_selection']
        # Also add cols declared in 'agg_in_tooltip' section:
        if 'agg_in_tooltip' in conf.keys():
            selected_cols += conf['agg_in_tooltip'].keys()
            selected_cols += [x for sublist in conf['agg_in_tooltip'].values() for x in sublist]
        # Add col from 'sort' section:
        if 'sort' in conf.keys():
            selected_cols += [conf['sort'][0]]
        selected_cols = list(dict.fromkeys(selected_cols))  # De-duplicate

    # Add/process cols depending on input type:
    if args.parquet:  # Single pq input
        assert osp.isfile(args.parquet), f"Provided parquet '{args.parquet}' not found"
        DATA_SOURCE = pl.scan_parquet(args.parquet)
        # Collect original colnames 1st, to discriminate INFO cols:
        original_colnames = DATA_SOURCE.collect_schema().names()
        # Can also get GT, AD columns by their name:
        GT_cols = [ c.replace('format_', '') for c in original_colnames if c.startswith('format_') and c.endswith('_GT') ]
        AD_cols = [ c.replace('format_', '') for c in original_colnames if c.startswith('format_') and c.endswith('_AD') ]
        DP_cols = [ c.replace('format_', '') for c in original_colnames if c.startswith('format_') and c.endswith('_DP') ]
        GQ_cols = [ c.replace('format_', '') for c in original_colnames if c.startswith('format_') and c.endswith('_GQ') ]
        # Then rename cols with '.' inside, cuz not supported:
        # Also remove 'info_' prefix at the same time
        rename_dict = {c:c.replace('.', '_').replace('info_', '').replace('format_', '') for c in original_colnames}
        DATA_SOURCE = DATA_SOURCE.rename(rename_dict)
        # Collect new renamed schema:
        full_schema = DATA_SOURCE.collect_schema()
        # List of INFO cols (with their new names):
        all_ann_cols = [c.replace('.', '_').replace('info_', '') for c in original_colnames if c.startswith('info_')]

    elif args.input:  # Lake input
        # WARN: Bellow 'full_schema' only contains ANN cols...
        full_schema = lake_schema(args.lake)
        all_ann_cols = [c for c in full_schema.names() if not c.endswith('id')]
        if config_OK and 'col_selection' in conf.keys():
            cols_list = selected_cols
        else:
            cols_list = all_ann_cols
        DATA_SOURCE = lake_data(args.lake, args.input, cols_list)
        # Define and fix gt_cols (1 -> 0/1 etc):
        GT_cols = [ f"{s}_GT" for s in args.input ]
        AD_cols = [ f"{s}_AD" for s in args.input ]
        DP_cols = [ f"{s}_DP" for s in args.input ]
        GQ_cols = [ f"{s}_GQ" for s in args.input ]
        for gt_col in GT_cols:
            DATA_SOURCE = DATA_SOURCE.with_columns(
                pl.col(gt_col).fill_null("0/0")
            )
            # Convert to 'List(str)':
            # ENH: Not very efficient to concat_list for later str.join('')
            DATA_SOURCE = DATA_SOURCE.with_columns(
                pl.concat_list([pl.col(gt_col)])
            )


    # FROM HERE: should be independent of input type (lake or single pq)
    if args.show_cols:
        logger.info("List INFO columns and exit:")
        [print(col) for col in all_ann_cols]
        exit()

    # Create 'chr-pos-ref-alt' col:
    DATA_SOURCE = DATA_SOURCE.with_columns(
        pl.concat_list([
            pl.col('chromosome') + '-',
            pl.col('position').cast(str) + '-',
            pl.col('reference') + '-',
            pl.col('alternate'),
        ]).alias("#CHROMPOSREFALT")
    )

    # Create 'sample_AB' (VAF) cols:
    AB_cols = []
    for a_ad in AD_cols:
        ab_colname = a_ad.replace('_AD', '_AB')
        dp_colname = a_ad.replace('_AD', '_DP')
        AB_cols.append(ab_colname)

    # wanted_cols:
    # Also add all 'format' ones ? (eg: DP)
    wanted_cols = ["#CHROMPOSREFALT"]
    #wanted_cols += ['id']  # DEBUG only

    if args.input:
        wanted_cols += ["occurrence", "found_in"]
    wanted_cols += GT_cols
    wanted_cols += GQ_cols
    wanted_cols += DP_cols
    wanted_cols += AD_cols
    wanted_cols += AB_cols

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

    # Collect schema of final lf:
    final_schema = DATA_SOURCE.collect_schema()
    dict_schema = {k:str(final_schema[k]) for k in final_schema}
    logger.debug(nice_dict(dict_schema))

    # Bellow is a kind of assert (FAIL if selected wrong cols):
    start_head = perf_counter()
    head_of_data = DATA_SOURCE.head().collect()
    logger.info(head_of_data)
    logger.info(f"Showed first 10 rows of data (in {perf_counter()-start_head} seconds)")

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


    # Set colDefs properties
    # MEMO: Ag-grid expects a list of {field:i}
    #       But for now simpler to use a dict with colname as key
    pre_columnDefs={i:{"field": i} for i in wanted_cols}

    # Color GT cols:
    # ENH: Auto put DP,GQ as tooltip for 1st GT col ? (done in Achab)
    for gt_col in GT_cols:
        pre_columnDefs[gt_col]["cellStyle"] = colorize_GT()
        pre_columnDefs[gt_col]["width"] = 150

    # Render link in 'chr-pos-ref-alt' col:
    # MEMO: JS func defined in 'dashAgGridComponentFunctions.js'
    pre_columnDefs["#CHROMPOSREFALT"]["cellRenderer"] = "chrPosRefAltLink"
    pre_columnDefs["#CHROMPOSREFALT"]["width"] = 100

    # Change filterType of 'sort' column:
    if config_OK and "sort" in conf.keys():
        pre_columnDefs[conf["sort"][0]]["filter"] = "agNumberColumnFilter"

    # Change filterType of relevant 'FORMAT' column:
    nb_format_cols = GQ_cols + DP_cols + AB_cols
    for fmt_col in nb_format_cols:
        pre_columnDefs[fmt_col]["filter"] = "agNumberColumnFilter"
    # Disable filtering on 'AD' cols (dtype incompat):
    for fmt_col in AD_cols:
        pre_columnDefs[fmt_col]["filter"] = False

    # Change filterType of 'occurrence' column (if defined):
    if 'occurrence' in pre_columnDefs.keys():
        pre_columnDefs["occurrence"]["filter"] = "agNumberColumnFilter"
        pre_columnDefs["occurrence"]["width"] = 100
        conf["agg_in_tooltip"]["occurrence"] = ["found_in"]

    # Add tooltips:
    # First add 'FORMAT' cols
    if len(GT_cols) > 1:
        conf["agg_in_tooltip"][GT_cols[0]] = format_to_tooltip(GT_cols)
    if len(GT_cols) > 1 or (config_OK and "agg_in_tooltip" in conf.keys()):
        to_hide = [x for sublist in conf["agg_in_tooltip"].values() for x in sublist]

        for a_col in conf["agg_in_tooltip"].keys():
            pre_columnDefs[a_col]["tooltipField"] = a_col  # Mandatory
            ## aggKey_to_func() writes a JS func for each col where tooltip is added:
            pre_columnDefs[a_col]["tooltipComponent"] = aggKey_to_func(conf['agg_in_tooltip'], a_col)

        # Hide columns whose data are in tooltip:
        for hide_col in to_hide:
            pre_columnDefs[hide_col]["hide"] = True

        logger.info("Wrote 'tinyvv/assets/dashAgGridComponentFunctions.js' for customTooltips")

    logger.debug(nice_dict(list(pre_columnDefs.values())))

    # Count total rows:
    start = perf_counter()
    total_rows = DATA_SOURCE.select(pl.len()).collect().item()
    logger.debug(f"Counted a total of {total_rows} rows (in {perf_counter()-start} s)")


    app = Dash()

    app.layout = html.Div(
        [
            dcc.Markdown("Infinite scroll with selectable rows"),
            dag.AgGrid(
                id="infinite-grid",
                style={"height": 600, "width": "100%"},
                columnDefs=list(pre_columnDefs.values()),
                defaultColDef={
                    "sortable": False,
                    "filter": True,
                },
                rowModelType="infinite",
                dashGridOptions={
                    # Auto-height slow grid: https://www.ag-grid.com/javascript-data-grid/scrolling-performance/#avoid-auto-height
                    "rowHeight": 42,
                    # The number of rows rendered outside the viewable area the grid renders.
                    # Default=10
                    "rowBuffer": 100,
                    # Number of rows sent by server (default=100)
                    "cacheBlockSize": 50000,
                    # How many blocks to keep in the store. Default is no limit, so every requested block is kept.
                    "maxBlocksInCache": 1,
                    "rowSelection": {'mode': 'multiRow'},
                    "tooltipShowDelay": 0,
                    "enableCellTextSelection": True,
                    "skipHeaderOnAutoSize": True,
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
        start_call = perf_counter()
        partial = ldf[request["startRow"] : request["endRow"]].collect()
        dict_data = {
            "rowData": partial.to_dicts(),
        }
        dict_data["rowCount"] = total_rows
        rows_count = partial.shape[0]
        if rows_count == 0:
            # FIXME: Bellow stops scrolling when consumed all filtered rows
            #dict_data["rowCount"] = 0
            pass
        logger.debug(f"Nb rows after filtering: {rows_count} (in {perf_counter()-start_call} seconds)")
        logger.debug(f"Estimated dataFrame size: {partial.estimated_size(unit='mb')} MB")
        return dict_data, request["filterModel"]

    app.run(debug=False)


if __name__ == "__main__":
    main()
