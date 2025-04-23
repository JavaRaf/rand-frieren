from pathlib import Path

from ruamel.yaml import YAML



yaml: YAML = YAML()  # Criando a instância primeiro
yaml.preserve_quotes = True  # Configurando preserve_quotes separadamente
yaml.indent(mapping=2, sequence=4, offset=2)  # Corrigindo a indentação corretamente
yaml.default_flow_style = False


CONFIGS_PATH = Path.cwd() / "configs.yml"


def load_configs() -> dict:
    if not CONFIGS_PATH.exists():
        print(f"Config file not found: {CONFIGS_PATH}", flush=True)
        return {}

    try:
        with open(CONFIGS_PATH, "r") as file:
            return yaml.load(file)
    except Exception as e:
        print(f"Error while loading configs: {e}", flush=True)
        return {}
