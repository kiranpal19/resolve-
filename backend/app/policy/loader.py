import os
import yaml
from typing import Dict, Any

class RuleLoader:
    def __init__(self, rules_dir: str = None):
        if rules_dir is None:
            rules_dir = os.path.join(os.path.dirname(__file__), "rules")
        self.rules_dir = rules_dir
        self._cache: Dict[str, Any] = {}

    def get_rule_set(self, rule_set_name: str) -> Dict[str, Any]:
        if rule_set_name in self._cache:
            return self._cache[rule_set_name]

        file_path = os.path.join(self.rules_dir, f"{rule_set_name}.yaml")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Rule set file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._cache[rule_set_name] = data
        return data

_loader_instance = None

def get_loader() -> RuleLoader:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = RuleLoader()
    return _loader_instance
