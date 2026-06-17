import json
import argparse


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
