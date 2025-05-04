"""
defaults.py: Basic configuration defaults
"""

from dataclasses import dataclass


@dataclass
class Defaults:
    k8s_app_dir: str = "kubernetes/apps"
    template_dir: str = ".templates/fluxit"
    template: str = "app_template"
    log_format: str = "[%(levelname)8s] %(module)s.%(funcName)s:%(lineno)-3d %(message)s"
    ns_kustomize_file: str = "kustomization.yaml"
    log_level: str = "INFO"
    confirm: str = "if_exists"
    deployment_strategy: str = "Recreate"
    replicas: int = 1
    color: bool = True
    service_port: int = 80


defaults = Defaults()
