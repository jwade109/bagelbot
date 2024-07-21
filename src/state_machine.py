from ws_dir import WORKSPACE_DIRECTORY
from bagelshop.logging import log
from dataclasses import dataclass

import bagelshop.state_machine as bssm


YAML_PATH = WORKSPACE_DIRECTORY + "/private/bagelbot_state.yaml"


def set_param(path, value, fn=YAML_PATH):
    log.debug(f"Writing \"{path}\" to {YAML_PATH}")
    state = bssm.load_yaml(fn)
    if state is None:
        state = {}
    bssm.deep_set(state, path, value)
    bssm.dump_yaml(state, fn)


def get_param(path, default=None, fn=YAML_PATH):
    log.debug(f"Reading \"{path}\" from {YAML_PATH}")
    state = bssm.load_yaml(fn)
    maybe = bssm.deep_get(state, path)
    if maybe is not None:
        return maybe
    print(f"Failed to get parameter {path}, using default: {default}")
    log.warning(f"Failed to get parameter {path}, using default: {default}")
    set_param(path, default, fn)
    return default

