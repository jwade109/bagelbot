import yaml
import logging
import os
from datetime import timedelta
from functools import reduce
import operator
from ws_dir import WORKSPACE_DIRECTORY

# yaml.warnings({'YAMLLoadWarning': False})
log = logging.getLogger("parameters")
log.setLevel(logging.DEBUG)

YAML_PATH = WORKSPACE_DIRECTORY + "/private/bagelbot_state.yaml"

def path_to_keys(path):
    keys = path.split("/")
    ops = [int, float]
    for i in range(len(keys)):
        for op in ops:
            try:
                keys[i] = op(keys[i])
                break
            except Exception:
                pass
    return keys

def deep_get(dictionary, path):
    keys = path_to_keys(path)
    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)

def deep_set(dictionary, path, value):
    keys = path_to_keys(path)
    d = dictionary
    for i, key in enumerate(keys):
        if i + 1 == len(keys):
            d[key] = value
            return
        if key not in d:
            d[key] = {}
        d = d[key]

def dt_repr(dumper, data):
    return dumper.represent_scalar(u'!timedelta', str(data.total_seconds()))

def dt_ctor(loader, node):
    value = loader.construct_scalar(node)
    return timedelta(seconds=float(value))

yaml.add_representer(timedelta, dt_repr)
yaml.add_constructor(u'!timedelta', dt_ctor)

class NoAliasDumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True

def load_yaml(fn):
    if not os.path.exists(fn):
        dump_yaml({}, fn)
    file = open(fn, "r")
    state = yaml.load(file)
    return state

def dump_yaml(dict, fn):
    file = open(fn, "w")
    yaml.dump(dict, file, default_flow_style=False, Dumper=NoAliasDumper)

def set_param(path, value, fn=YAML_PATH):
    # log.debug(f"Writing \"{path}\" to {YAML_PATH}")
    state = load_yaml(fn)
    if state is None:
        state = {}
    deep_set(state, path, value)
    dump_yaml(state, fn)

def get_param(path, default=None, fn=YAML_PATH):
    # log.debug(f"Reading \"{path}\" from {YAML_PATH}")
    state = load_yaml(fn)
    maybe = deep_get(state, path)
    if maybe is not None:
        return maybe
    print(f"Failed to get parameter {path}, using default: {default}")
    log.warning(f"Failed to get parameter {path}, using default: {default}")
    set_param(path, default, fn)
    return default
