import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
                    prog='TinyVV',
                    description='Tiny but powerful variants viewer')
    parser.add_argument('-i', '--input', type=str, help="Input parquet file produced by vcf2parquet")
    parser.add_argument('-g', '--build', default='hg38', type=str, help="Genome build (default= 'hg38')")
    return parser.parse_args()


def nice_dict(a_dict):
    # Nice print of dicts or dict-like:
    return json.dumps(a_dict, indent=2)
