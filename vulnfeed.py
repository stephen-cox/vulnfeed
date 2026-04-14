import requests
import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)


def fetch_github_advisories(repo: str, token: str | None = None) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/security-advisories"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
