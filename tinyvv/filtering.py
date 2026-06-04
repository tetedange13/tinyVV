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
