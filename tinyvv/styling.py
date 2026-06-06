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
    # Turn agg_in_tooltips to tooltipValueGetter function as bellow
    #Example: 'tooltipValueGetter': {"function": "params.data.athlete + ' was ' + params.data.age + ' in ' + params.value"}
    # MEMO: For unknown reason 'params.data' get undefined (even if not) -> crash app
    #       -> Check before and add a default tooltip value
    mandatory_check = "params.data == null || params.data === '' ? '- Missing -' : "
    sub_list = [f"'{x} = ' + params.data.{x}" for x in a_dict[a_key]]
    return mandatory_check + " + ' ' + ".join(sub_list)
