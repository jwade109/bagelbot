import yaml
import logging
import os

log = logging.getLogger("parameters")
log.setLevel(logging.DEBUG)

YAML_PATH = "/home/pi/bagelbot/bagelbot_state.yaml"

def load_yaml(fn):
    if not os.path.exists(fn):
        dump_yaml({}, fn)
    file = open(fn, "r")
    state = yaml.safe_load(file)
    return state

def dump_yaml(dict, fn):
    file = open(fn, "w")
    yaml.dump(dict, file, default_flow_style=False)

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
    set_param(name, default)
    return default
