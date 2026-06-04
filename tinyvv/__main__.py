import dash_ag_grid as dag
from dash import Dash, Input, Output, dcc, html, no_update, callback
import polars as pl
import sys


def parse_column_filter(filter_obj, col_name):
   """Build a polars filter expression based on the filter object"""
   if filter_obj["filterType"] == "set":
       expr = None
       for val in filter_obj["values"]:
           expr |= pl.col(col_name).cast(pl.Utf8).cast(pl.Categorical) == val
   else:
       if filter_obj["filterType"] == "date":
           crit1 = filter_obj["dateFrom"]


           if "dateTo" in filter_obj:
               crit2 = filter_obj["dateTo"]


       else:
           if "filter" in filter_obj:
               crit1 = filter_obj["filter"]
           if "filterTo" in filter_obj:
               crit2 = filter_obj["filterTo"]


       if filter_obj["type"] == "contains":
           lower = (crit1).lower()
           expr = pl.col(col_name).str.to_lowercase().str.contains(lower)


       elif filter_obj["type"] == "notContains":
           lower = (crit1).lower()
           expr = ~pl.col(col_name).str.to_lowercase().str.contains(lower)
       elif filter_obj["type"] == "startsWith":
           lower = (crit1).lower()
           expr = pl.col(col_name).str.starts_with(lower)


       elif filter_obj["type"] == "notStartsWith":
           lower = (crit1).lower()
           expr = ~pl.col(col_name).str.starts_with(lower)


       elif filter_obj["type"] == "endsWith":
           lower = (crit1).lower()
           expr = pl.col(col_name).str.ends_with(lower)


       elif filter_obj["type"] == "notEndsWith":
           lower = (crit1).lower()
           expr = ~pl.col(col_name).str.ends_with(lower)


       elif filter_obj["type"] == "blank":
           expr = pl.col(col_name).is_null()


       elif filter_obj["type"] == "notBlank":
           expr = ~pl.col(col_name).is_null()


       elif filter_obj["type"] == "equals":
           expr = pl.col(col_name) == crit1


       elif filter_obj["type"] == "notEqual":
           expr = pl.col(col_name) != crit1


       elif filter_obj["type"] == "lessThan":
           expr = pl.col(col_name) < crit1


       elif filter_obj["type"] == "lessThanOrEqual":
           expr = pl.col(col_name) <= crit1


       elif filter_obj["type"] == "greaterThan":
           expr = pl.col(col_name) > crit1


       elif filter_obj["type"] == "greaterThanOrEqual":
           expr = pl.col(col_name) >= crit1


       elif filter_obj["type"] == "inRange":
           if filter_obj["filterType"] == "date":
               expr = (pl.col(col_name) >= crit1) & (pl.col(col_name) <= crit2)
           else:
               expr = (pl.col(col_name) >= crit1) & (pl.col(col_name) <= crit2)
       else:
           None


   return expr


def make_filter_expr_list(filt_model):
   expr_list = []
   for a_col in filt_model:
      expr_list.append(parse_column_filter(filt_model[a_col], a_col))
   return expr_list


def colorize_GT():
    style_dict = {
        # Default style if no rules apply
        "defaultStyle": {"backgroundColor": "mediumaquamarine"}
    }

    # Set of rules
    style_dict["styleConditions"] = [
                {
                    "condition": "params.value=='1/1'",
                    "style": {"backgroundColor": "sandybrown"},
                },
                {
                    "condition": "params.value=='0/1'",
                    "style": {"backgroundColor": "lightcoral"},
                }
            ]

    return style_dict


# MAIN
def main():

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
                    print(str(expr))
                    if filter_query is None:
                        filter_query = expr
                    else:
                        filter_query &= expr
                ldf = ldf.filter(filter_query)
        return ldf

    app = Dash()

    DATA_SOURCE = pl.scan_parquet(sys.argv[1])

    all_cols = DATA_SOURCE.collect_schema().names()
    #print(all_cols)  # DEBUG

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
    #'tooltipValueGetter': {"function": "params.data.athlete + ' was ' + params.data.age + ' in ' + params.value"},
    # wanted_cols += [
    #     'info_gnomAD_exome_ALL',
    #     'info_gnomAD_exome_AFR'
    #     ]

    DATA_SOURCE = DATA_SOURCE.select(wanted_cols)
    # Bellow is a kind of assert (FAIL if selected wrong cols):
    DATA_SOURCE.head().collect()

    columnDefs=[{"field": i} for i in wanted_cols]

    # Color GT cols:
    for a_col in columnDefs:
        if a_col['field'] in GT_cols:
            a_col['cellStyle'] = colorize_GT()
    #print(columnDefs) ; exit()  # DEBUG

    # Count total rows:
    # MEMO: Select 1st col speed up operation
    #total_rows = DATA_SOURCE.select('chromosome').with_row_index().last().select('index').collect().item()

    app.layout = html.Div(
        [
            dcc.Markdown("Infinite scroll with selectable rows"),
            dag.AgGrid(
                id="infinite-grid",
                style={"height": 600, "width": "100%"},
                columnDefs=columnDefs,
                defaultColDef={"sortable": False, "filter": True},
                rowModelType="infinite",
                dashGridOptions={
                    # The number of rows rendered outside the viewable area the grid renders.
                    "rowBuffer": 0,
                    # How many blocks to keep in the store. Default is no limit, so every requested block is kept.
                    "maxBlocksInCache": 1,
                    "rowSelection": {'mode': 'multiRow'},
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
        print(request["filterModel"])
        ldf = scan_ldf(filter_model=request["filterModel"], columns=columns)
        partial = ldf[request["startRow"] : request["endRow"]].collect()
        # Count rows after filter, but handle case where filter return nothing:
        rows_count_df = ldf.select('chromosome').with_row_index().last().select('index').collect()
        print(rows_count_df.shape)
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
