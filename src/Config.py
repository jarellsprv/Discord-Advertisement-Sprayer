import os
import json

config_path = os.path.join(os.path.dirname(__file__), "..", "input", "config.json")
config_path = os.path.abspath(config_path)

with open(config_path, "r") as f:
    CONFIG = json.load(f)
