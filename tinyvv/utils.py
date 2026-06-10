import json
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
                    prog='TinyVV',
                    description='Tiny but powerful variants viewer')
    parser.add_argument('-i', '--input')
    return parser.parse_args()


def nice_dict(a_dict):
    # Nice print of dicts or dict-like:
    return json.dumps(a_dict, indent=2)
