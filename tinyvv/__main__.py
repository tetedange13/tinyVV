import logging
import dash_ag_grid as dag
from dash import Dash, Input, Output, State, dcc, html, no_update, callback
import polars as pl
from polars import col as c
import os.path as osp
import yaml
import json
from time import perf_counter
# LOCAL imports
from .filtering import make_filter_expr_list
from .styling import style_columns
from .utils import parse_args, nice_dict
from .query import lake_schema, lake_data
logger = logging.getLogger(__name__)
pl.Config.set_engine_affinity("streaming")


# MAIN
def main():
    #Output to log file:
    #logging.basicConfig(filename='tinyvv.log', level=logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)


    def scan_ldf(
        ldf,
        ldf_schema_dict,
        filter_model=None,
        col_def_dict=None,
        sort_model=None,
        ):
        columns = list(col_def_dict.keys())
        if columns:
            ldf = ldf.select(columns)
        if filter_model:
            filter_query = make_filter_expr_list(filter_model, col_def_dict, ldf_schema_dict)
            print("FULL_filter_query:", nice_dict(filter_model))
            print(f"polars_filter_query: {filter_query}")
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
        conf = {}

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
        # Create 'chr-pos-ref-alt' col:
        DATA_SOURCE = DATA_SOURCE.with_columns(
            pl.concat_str(
                [
                    c('chromosome'),
                    c('position').cast(str),
                    c('reference'),
                    c('alternate').list.join(separator=""),
                ],
                separator="-",
            ).alias("CHROMPOSREFALT")
        )
        # Compute AB col (VAF):
        for gt_col in GT_cols:
            ad_colname = gt_col.replace('_GT', '_AD')
            dp_colname = gt_col.replace('_GT', '_DP')
            ab_colname = gt_col.replace('_GT', '_AB')
            DATA_SOURCE = DATA_SOURCE.with_columns(
                (c(ad_colname).list[1]/c(dp_colname)).alias(ab_colname)
            )
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


    # FROM HERE: should be independent of input type (lake or single pq)
    if args.show_cols:
        logger.info("List INFO columns and exit:")
        [print(col) for col in all_ann_cols]
        exit()

    # Get 'sample_AB' (VAF) col_names:
    AB_cols = []
    for a_gt in GT_cols:
        ab_colname = a_gt.replace('_GT', '_AB')
        dp_colname = a_gt.replace('_GT', '_DP')
        AB_cols.append(ab_colname)

    # wanted_cols:
    # Also add all 'format' ones ? (eg: DP)
    wanted_cols = ["CHROMPOSREFALT"]
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
                c(conf['sort'][0]).list.join(separator="").cast(pl.Int32)
                ).sort(by=conf['sort'][0], descending=conf['sort'][1])
        else: # just sort
            DATA_SOURCE = DATA_SOURCE.with_columns(
                ).sort(by=conf['sort'][0], descending=conf['sort'][1])

    # Collect schema of final lf:
    final_schema = DATA_SOURCE.collect_schema()
    # MEMO: Bellow dtypes are not really 'pl.dtypes'
    #       But rather 'str' eval of 'pl.dtypes'
    #       -> Should be OK anyway ?
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


    number_cols_list = [ c for c in wanted_cols if dict_schema[c] in ("UInt32","Float64","Int64","Int32") ]
    pre_columnDefs = style_columns(config_OK, conf, wanted_cols, number_cols_list)

    logger.debug(nice_dict(list(pre_columnDefs.values())))

    # Count total rows:
    start = perf_counter()
    total_rows = DATA_SOURCE.select(pl.len()).collect().item()
    logger.debug(f"Counted a total of {total_rows} rows (in {perf_counter()-start} s)")


    app = Dash()

    app.layout = html.Div([
            # Zone de définition des filtres
            html.Div(id="filter-builder", children=[
                html.Div([
                    dcc.Dropdown(
                        id="filter-logic",
                        options=[
                            {"label": "AND", "value": "and"},
                            {"label": "OR", "value": "or"},
                        ],
                        value="and",
                        style={"width": "125px", "display": "inline-block", "marginRight": "10px"}
                    ),
                    dcc.Dropdown(
                        id="filter-column",
                        options=[{"label": col, "value": col} for col in wanted_cols],
                        placeholder="Columns",
                        style={"width": "180px", "display": "inline-block", "marginRight": "10px"}
                    ),
                    dcc.Dropdown(
                        id="filter-operator",
                        options=[
                            {"label": "Contains", "value": "contains"},
                            {"label": "Does not contain", "value": "notContains"},
                            {"label": "Equals", "value": "equals"},
                            {"label": "Does not equal", "value": "notEqual"},
                            {"label": "Greater than", "value": "greaterThan"},
                            {"label": "Greater than or equal to", "value": "greaterThanOrEqual"},
                            {"label": "Less than", "value": "lessThan"},
                            {"label": "Less than or equal to", "value": "lessThanOrEqual"},
                            {"label": "Starts with", "value": "startsWith"},
                            {"label": "Ends with", "value": "endsWith"},
                            {"label": "Blank", "value": "isEmpty"},
                            {"label": "Not blank", "value": "isNotEmpty"},
                        ],
                        placeholder="Condition",
                        style={"width": "180px", "display": "inline-block", "marginRight": "10px"}
                    ),
                    dcc.Input(
                        id="filter-value",
                        type="text",
                        placeholder="Value",
                        style={"width": "180px", "display": "inline-block", "marginRight": "10px"}
                    ),
                    html.Button("ADD filter", id="add-filter", n_clicks=0),
                ], style={"marginBottom": "20px"}),
                # Liste des filtres ajoutés
                html.Div(id="filter-list"),
            ]),

            # Apply/reset filters bouttons
            html.Div([
                html.Button("APPLY filters", id="apply-filters", n_clicks=0, style={"marginRight": "10px"}),
                html.Button("RESET filters", id="reset-filters", n_clicks=0),
            ], style={"marginBottom": "20px"}),
            # Load/save filters bouttons
            html.Div([
                dcc.Input(
                    id="load-filter-value",
                    type="text",
                    placeholder="Eg: saved_filters.json",
                    style={"width": "180px", "display": "inline-block", "marginRight": "10px"}
                ),
                html.Button("LOAD filters", id="load-filters", n_clicks=0),
            ], style={"marginBottom": "20px"}),

            dag.AgGrid(
                id="grid",
                style={"height": 600, "width": "100%"},
                columnDefs=list(pre_columnDefs.values()),
                defaultColDef={
                    "sortable": False,
                    "filter": False,
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
            dcc.Store(id="stored-filters", data=[]),
            html.Div(id="infinite-output"),
        ],
        style={"margin": 20},
    )


    @app.callback(
        Output("filter-list", "children", allow_duplicate=True),  # DUPLICATED
        Output("stored-filters", "data", allow_duplicate=True),  # DUPLICATED
        Input("reset-filters", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(n_clicks):
        # FIXME: reset_filters should update grid and remove applied filters ???
        return html.Div(id="filter-list"), []

    @app.callback(
        Output("filter-list", "children", allow_duplicate=True),  # DUPLICATED
        Output("stored-filters", "data", allow_duplicate=True),  # DUPLICATED
        Input("load-filters", "n_clicks"),
        prevent_initial_call=True,
    )
    def load_filters(n_clicks):
        saved_filters_path = "saved_filters.json"
        with open(saved_filters_path, 'r') as saved_filters_file:
            saved_filters = json.load(saved_filters_file)
        # Shown filters list
        # ENH: Deduplicate bellow code (cf. 'add_filter()')
        filter_items = [
            html.Div([
                html.Span(
                    f" {f['logic'].upper()} ",
                    style={"fontWeight": "bold", "marginLeft": "10px", "marginRight": "10px"}
                ),
                html.Span(f"{f['column']} {f['operator']} {f['value']}"),
            ], style={"marginBottom": "5px", "padding": "5px", "border": "1px solid #ddd", "borderRadius": "5px"})
            for f in saved_filters
        ]
        # Le premier filtre n'a pas de "ET/OU" avant
        if filter_items:
            filter_items[0] = html.Div([
                html.Span(f"{saved_filters[0]['column']} {saved_filters[0]['operator']} {saved_filters[0]['value']}"),
            ], style={"marginBottom": "5px", "padding": "5px", "border": "1px solid #ddd", "borderRadius": "5px"})

        return html.Div(filter_items), saved_filters

    @app.callback(
        Output("filter-list", "children"),  # DUPLICATED
        Output("stored-filters", "data"),  # DUPLICATED
        Input("add-filter", "n_clicks"),
        State("filter-logic", "value"),
        State("filter-column", "value"),
        State("filter-operator", "value"),
        State("filter-value", "value"),
        State("stored-filters", "data"),
        prevent_initial_call=True,
    )
    def add_filter(n_clicks, logic, col, op, val, stored_filters):
        if not col or not op or (val is None and op not in ["isEmpty", "isNotEmpty"]):
            return html.Div("Veuillez remplir tous les champs.", style={"color": "red"}), stored_filters

        new_filter = {"logic": logic, "column": col, "operator": op, "value": val}
        stored_filters = stored_filters or []
        stored_filters.append(new_filter)

        # Shown filters list
        filter_items = [
            html.Div([
                html.Span(
                    f" {f['logic'].upper()} ",
                    style={"fontWeight": "bold", "marginLeft": "10px", "marginRight": "10px"}
                ),
                html.Span(f"{f['column']} {f['operator']} {f['value']}"),
            ], style={"marginBottom": "5px", "padding": "5px", "border": "1px solid #ddd", "borderRadius": "5px"})
            for f in stored_filters
        ]
        # Le premier filtre n'a pas de "ET/OU" avant
        if filter_items:
            filter_items[0] = html.Div([
                html.Span(f"{stored_filters[0]['column']} {stored_filters[0]['operator']} {stored_filters[0]['value']}"),
            ], style={"marginBottom": "5px", "padding": "5px", "border": "1px solid #ddd", "borderRadius": "5px"})

        return html.Div(filter_items), stored_filters

    @app.callback(
    Output("grid", "getRowsResponse"),
    Input("grid", "getRowsRequest"),
    Input("apply-filters", "n_clicks"),
    State("stored-filters", "data"),
    prevent_initial_call=True,
    )
    def infinite_scroll(request, n_clicks, filters):
        if request is None:
            return no_update
        # ENH: Save filters only when asked by user
        if filters:
            with open("saved_filters.json", 'w') as saved_filters_path:
                json.dump(filters, saved_filters_path, indent=2)
        ldf = scan_ldf(
            DATA_SOURCE,
            dict_schema,
            filter_model=filters,
            col_def_dict=pre_columnDefs
        )
        start_call = perf_counter()
        partial = ldf[request["startRow"] : request["endRow"]].collect()
        dict_data = {
            "rowData": partial.to_dicts(),
        }
        dict_data["rowCount"] = total_rows
        rows_count = partial.shape[0]
        if request["filterModel"] and rows_count == 0:
            # MEMO: Does NOT set 'rowCount' in other context
            #       Otherwise it stops scrolling when end reached
            dict_data["rowCount"] = 0
        logger.debug(f"Nb rows after filtering: {rows_count} (in {perf_counter()-start_call} seconds)")
        logger.debug(f"Estimated dataFrame size: {partial.estimated_size(unit='mb')} MB")
        return dict_data


    app.run(debug=False)

if __name__ == "__main__":
    main()
