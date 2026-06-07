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
