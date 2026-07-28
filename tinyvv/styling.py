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


def aggKey_to_func (a_dict, a_key):
    # Cannot render '\n' in tooltip -> have to use custom one
    # See: https://github.com/ag-grid/ag-grid/issues/8299
    template_line = "            React.createElement('div', {}, 'REPLACE= ' + props.data.REPLACE),"
    with open('tinyvv/assets/templateTooltip.js', 'r') as template:
        with open('tinyvv/assets/dashAgGridComponentFunctions.js', 'a') as tooltip_file:
            lines = template.read().replace('REPLACE', a_key)
            to_write = ""
            for x in a_dict[a_key]:
                to_write += template_line.replace('REPLACE', x) + '\n'

            tooltip_file.write(lines.replace("INSERT_HERE", to_write) + '\n')

    return f"CustomTooltip_{a_key}"


def format_to_tooltip(GT_cols):
    """
    Returns a list of col_names to be put as tooltip values
    """
    list_in_tooltip = []
    for gt_col in GT_cols[1:]:
        gq_colname = gt_col.replace('_GT', '_GQ')
        dp_colname = gt_col.replace('_GT', '_DP')
        ad_colname = gt_col.replace('_GT', '_AD')
        ab_colname = gt_col.replace('_GT', '_AB')
        list_in_tooltip += [
            gq_colname,
            dp_colname,
            ad_colname,
            ab_colname
        ]
    return list_in_tooltip


def style_columns(is_config_OK, conf_dict, wanted_cols_list):
    # Set colDefs properties
    # MEMO: Ag-grid expects a list of {field:i}
    #       But for now simpler to use a dict with colname as key
    pre_columnDefs={i:{"field": i} for i in wanted_cols_list}

    # Deduce GT cols from wanted_cols (assume order is preserved):
    GT_cols = [ c for c in wanted_cols_list if c.endswith('_GT') ]
    # Deduce other FORMAT cols from GT ones:
    GQ_cols = [ g.replace('_GT', '_GQ') for g in GT_cols ]
    AD_cols = [ g.replace('_GT', '_AD') for g in GT_cols ]
    DP_cols = [ g.replace('_GT', '_DP') for g in GT_cols ]
    AB_cols = [ g.replace('_GT', '_AB') for g in GT_cols ]

    # Color GT cols:
    # ENH: Auto put DP,GQ as tooltip for 1st GT col ? (done in Achab)
    for gt_col in GT_cols:
        pre_columnDefs[gt_col]["cellStyle"] = colorize_GT()
        pre_columnDefs[gt_col]["width"] = 150

    # Render link in 'chr-pos-ref-alt' col:
    # MEMO: JS func defined in 'dashAgGridComponentFunctions.js'
    pre_columnDefs["CHROMPOSREFALT"]["cellRenderer"] = "chrPosRefAltLink"
    pre_columnDefs["CHROMPOSREFALT"]["width"] = 100

    # Change filterType of 'sort' column:
    if is_config_OK and "sort" in conf_dict.keys():
        pre_columnDefs[conf_dict["sort"][0]]["filter"] = "agNumberColumnFilter"

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
        # Init "agg_in_tooltip" key if NO conf (parquets_lake case):
        if "agg_in_tooltip" not in conf_dict.keys():
            conf_dict["agg_in_tooltip"] = {"occurrence":["found_in"]}
        else:
            conf_dict["agg_in_tooltip"]["occurrence"] = ["found_in"]

    # Change filterType of 'id' column (if defined):
    if 'id' in pre_columnDefs.keys():
        pre_columnDefs["id"]["filter"] = "agNumberColumnFilter"

    # Add tooltips:
    # First add 'FORMAT' cols
    if len(GT_cols) > 1:
        # Init "agg_in_tooltip" key if NO conf (single_parquet case):
        if "agg_in_tooltip" not in conf_dict.keys():
            conf_dict["agg_in_tooltip"] = {GT_cols[0]:format_to_tooltip(GT_cols)}
        else:
            conf_dict["agg_in_tooltip"][GT_cols[0]] = format_to_tooltip(GT_cols)

    if len(GT_cols) > 1 or (is_config_OK and "agg_in_tooltip" in conf_dict.keys()):
        to_hide = [x for sublist in conf_dict["agg_in_tooltip"].values() for x in sublist]

        for a_col in conf_dict["agg_in_tooltip"].keys():
            pre_columnDefs[a_col]["tooltipField"] = a_col  # Mandatory
            ## aggKey_to_func() writes a JS func for each col where tooltip is added:
            pre_columnDefs[a_col]["tooltipComponent"] = aggKey_to_func(conf_dict['agg_in_tooltip'], a_col)

        # Hide columns whose data are in tooltip:
        for hide_col in to_hide:
            pre_columnDefs[hide_col]["hide"] = True

        print("Wrote 'tinyvv/assets/dashAgGridComponentFunctions.js' for customTooltips")

    return pre_columnDefs
