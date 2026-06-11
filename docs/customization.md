
# Customization


## Intro
TinyVV will automatically look for a companion YAML file called `sample.yaml` near input `sample.parquet`

This file is completely optional and TinyVV will work even if not found

Under `example` sub-dir, there is a YAML detailing use cases

<br>

## Possible keys

### sort

Expects a list :
* 1st value is column to sort on
* 2nd value is a boolean (True/False) passed to `descending` argument of `sort` function

Only 1 col name is supported in this section

WARN: Currently `int` scores are supported
WARN2: Sorting is done on full dataset so can take long -> better sort your parquet BEFORE

### agg_in_tooltip

Expects a col name (**NOT** as a list), that will be the one that exhibit the tooltip
And for this col name a list of columns 

Multiple "tooltipped columns" can be specified


### col_selection

Expects a list of columns

Order will be preserved when show in `TinyVV`

All columns declared in `agg_in_tooltip` are automatically added too
