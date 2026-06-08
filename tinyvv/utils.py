import json

def nice_dict(a_dict):
    # Nice print of dicts or dict-like:
    return json.dumps(a_dict, indent=2)
