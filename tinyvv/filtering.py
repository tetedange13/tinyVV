import polars as pl


def convert_list_str(colname):
    return pl.col(colname).list.join(separator="")


def parse_column_filter(filter_obj, col_name):
   """Build a polars filter expression based on the filter object"""

   if filter_obj["filterType"] == "text":
       # WARN: Bellow assume all 'text' cols are of pl.dtype == 'list(str):
       converted_col = convert_list_str(col_name)
   else:
       converted_col = pl.col(col_name)

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


def make_filter_expr_list(filt_model):
   expr_list = []
   for a_col in filt_model:
      expr_list.append(parse_column_filter(filt_model[a_col], a_col))
   return expr_list
