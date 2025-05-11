from pathlib import Path

from ruamel.yaml import YAML

from src.logger import get_logger
yaml: YAML = YAML()  # Criando a instância primeiro
yaml.preserve_quotes = True  # Configurando preserve_quotes separadamente
yaml.indent(mapping=2, sequence=4, offset=2)  # Corrigindo a indentação corretamente
yaml.default_flow_style = False


logger = get_logger(__name__)
CONFIGS_PATH = Path.cwd() / "configs.yml"


def load_configs() -> dict:
    if not CONFIGS_PATH.exists():
        logger.error(f"Config file not found: {CONFIGS_PATH}", exc_info=True)
        return {}

    try:
        with open(CONFIGS_PATH, "r") as file:
            return yaml.load(file)
    except Exception as e:
        logger.error(f"Error while loading configs: {e}", exc_info=True)
        return {}


