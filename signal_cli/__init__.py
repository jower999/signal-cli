from .config import (
    SignalConfig,
    install_docker_compose,
    get_docker_compose_path,
    get_docker_compose_template,
)
from .docker import (
    LINK_CONTAINER_NAME,
    ephemeral_link_container,
    should_auto_manage_for_linking,
)
from .signal_client import SignalClient

__version__ = "0.6.0"

__all__ = [
    "SignalClient",
    "SignalConfig",
    "install_docker_compose",
    "get_docker_compose_path",
    "get_docker_compose_template",
    "LINK_CONTAINER_NAME",
    "ephemeral_link_container",
    "should_auto_manage_for_linking",
    "__version__",
]
