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
