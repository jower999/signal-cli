from .config import (
    SignalConfig,
    install_docker_compose,
    get_docker_compose_path,
    get_docker_compose_template,
)
from .signal_client import SignalClient

__version__ = "0.4.0"

__all__ = [
    "SignalClient",
    "SignalConfig",
    "install_docker_compose",
    "get_docker_compose_path",
    "get_docker_compose_template",
    "__version__",
]
