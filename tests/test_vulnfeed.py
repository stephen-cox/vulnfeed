from vulnfeed import load_config


def test_load_config(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - zammad/zammad
      - django/django
"""
    )

    config = load_config(str(config_file))

    assert len(config["feeds"]) == 1
    assert config["feeds"][0]["source"] == "github"
    assert config["feeds"][0]["repos"] == ["zammad/zammad", "django/django"]
