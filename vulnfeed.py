import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)
