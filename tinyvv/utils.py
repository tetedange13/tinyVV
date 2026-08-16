import json
import argparse
from dash import html


def parse_args():
    parser = argparse.ArgumentParser(
                    prog='TinyVV',
                    description='Tiny (but powerful) Variants Viewer')
    parser.add_argument('-i', '--input', nargs='+', type=str, help="Samples to include (eg: B00GMSH B00GMSI)")
    parser.add_argument('-p', '--parquet', type=str, help="Path o input parquet file produced by vcf2parquet")
    parser.add_argument('-l', '--lake', type=str, default='./lake', help="Path to lake dir")
    parser.add_argument('-c', '--config', type=str, help="Path to config file")
    parser.add_argument('-g', '--build', default='hg38', type=str, help="Genome build (default= 'hg38')")
    parser.add_argument('-s', '--show_cols', action="store_true", help="If provided, only show INFO colnames and exit")
    return parser.parse_args()


def nice_dict(a_dict):
    # Nice print of dicts or dict-like:
    return json.dumps(a_dict, indent=2)


def filters_to_span(stored_filters):
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

    return html.Div(filter_items)
