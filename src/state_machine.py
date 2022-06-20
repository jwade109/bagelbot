import yaml
import logging
import os
from datetime import timedelta

# yaml.warnings({'YAMLLoadWarning': False})
log = logging.getLogger("parameters")
log.setLevel(logging.DEBUG)

YAML_PATH = "/home/pi/bagelbot/state/bagelbot_state.yaml"


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

def set_param(name, value, fn=YAML_PATH):
    state = load_yaml(fn)
    if state is None:
        state = {}
    state[name] = value
    dump_yaml(state, fn)

def get_param(name, default=None, fn=YAML_PATH):
    state = load_yaml(fn)
    if state and name in state:
        return state[name]
    print(f"Failed to get parameter {name}, using default: {default}")
    log.warning(f"Failed to get parameter {name}, using default: {default}")
    set_param(name, default, fn)
    return default
