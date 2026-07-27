import polars as pl


def convert_list_str(colname):
    """
    Most text-based columns are typed 'List(str)' by variant-planer/vcf2parquet
    Convert them back to string avoid dtype incompatibily error when filtering
    'ignore_nulls' is disabled to allow 'blank / non-blank' filtering
    """
    return pl.col(
        colname
            ).list.join(
                separator="",
                ignore_nulls=False,
            )


def parse_column_filter(filter_obj, col_name, lf_schema_dict):
    """Build a polars filter expression based on the filter object"""

    converted_col = pl.col(col_name)
    # Convert 'text' col if pl.dtype == 'list(str):
    if filter_obj["filterType"] == "text" and lf_schema_dict[col_name] == "List(String)":
        converted_col = convert_list_str(col_name)
        print("DEBUG:filtering:Converted dtype from List(str) to str:", col_name)  # DEBUG

    if filter_obj["filterType"] == "set":
        expr = None
        for val in filter_obj["values"]:
            expr |= converted_col.cast(pl.Utf8).cast(pl.Categorical) == val
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
            expr = converted_col.str.to_lowercase().str.contains(lower)


        elif filter_obj["type"] == "notContains":
            lower = (crit1).lower()
            expr = ~converted_col.str.to_lowercase().str.contains(lower)
        elif filter_obj["type"] == "startsWith":
            lower = (crit1).lower()
            expr = converted_col.str.starts_with(lower)


        elif filter_obj["type"] == "notStartsWith":
            lower = (crit1).lower()
            expr = ~converted_col.str.starts_with(lower)


        elif filter_obj["type"] == "endsWith":
            lower = (crit1).lower()
            expr = converted_col.str.ends_with(lower)


        elif filter_obj["type"] == "notEndsWith":
            lower = (crit1).lower()
            expr = ~converted_col.str.ends_with(lower)


        elif filter_obj["type"] == "blank":
            expr = converted_col.is_null()


        elif filter_obj["type"] == "notBlank":
            expr = ~converted_col.is_null()


        elif filter_obj["type"] == "equals":
            expr = converted_col == crit1


        elif filter_obj["type"] == "notEqual":
            expr = converted_col != crit1


        elif filter_obj["type"] == "lessThan":
            expr = converted_col < crit1


        elif filter_obj["type"] == "lessThanOrEqual":
            expr = converted_col <= crit1


        elif filter_obj["type"] == "greaterThan":
            expr = converted_col > crit1


        elif filter_obj["type"] == "greaterThanOrEqual":
            expr = converted_col >= crit1


        elif filter_obj["type"] == "inRange":
            if filter_obj["filterType"] == "date":
                expr = (converted_col >= crit1) & (converted_col <= crit2)
            else:
                expr = (converted_col >= crit1) & (converted_col <= crit2)
        else:
            None


    return expr


def make_filter_expr_list(filt_model, lf_schema_dict):
    expr_list = []  # init Polars expression
    logic_list = []
    filt_obj = {}
    #dict_logic = 
    for a_filt in filt_model:
       # mimic object structure for column-wise filtering
       filt_obj = {
          "filterType":"text",
          "type":a_filt['operator'],
          "filter":a_filt["value"]
       }
       # Cannot init a polars expr -> have to put in a list
       logic_list.append(a_filt['logic'])
       expr_list.append(
          parse_column_filter(filt_obj, a_filt["column"], lf_schema_dict)
       )

    if len(expr_list)==1:
        return expr_list[0]

    final_expr = expr_list[0]
    for i,a_expr in enumerate(expr_list[1:]):
       if logic_list[i] == "and":
          final_expr = final_expr.and_(a_expr)
       elif logic_list[i] == "or":
          final_expr = final_expr.and_(a_expr)        
    return final_expr
