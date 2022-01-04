import yaml
import logging
import os

log = logging.getLogger("parameters")
log.setLevel(logging.DEBUG)

YAML_PATH = "/home/pi/bagelbot/bagelbot_state.yaml"

def load_yaml():
    if not os.path.exists(YAML_PATH):
        dump_yaml({})
    file = open(YAML_PATH, "r")
    state = yaml.safe_load(file)
    return state

def dump_yaml(dict):
    file = open(YAML_PATH, "w")
    yaml.dump(dict, file, default_flow_style=False)

def set_param(name, value):
    state = load_yaml()
    state[name] = value
    dump_yaml(state)

def get_param(name, default=None):
    state = load_yaml()
    if name in state:
        return state[name]
    print(f"Failed to get parameter {name}, using default: {default}")
    log.warning(f"Failed to get parameter {name}, using default: {default}")
    set_param(name, default)
    return default
