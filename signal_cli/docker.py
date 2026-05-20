"""Docker helpers for managing the user's normal signal service and
an ephemeral 'link-only' container (MODE=native) used exclusively during
the device linking flow.

The goal is that the user's long-term MODE choice (json-rpc, json-rpc-native, etc.)
is never altered just to perform linking. Instead we temporarily take over
the port + data directory with a throwaway container that is guaranteed to be
cleaned up even on Ctrl-C, exceptions, or process death.
"""

from __future__ import annotations

import atexit
import os
import signal
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .config import (
    SignalConfig,
    get_docker_compose_path,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

LINK_CONTAINER_NAME = "signal-cli-link"
DEFAULT_LINK_API_URL = "http://localhost:8080"

# The image we trust for reliable linking.
# Using :latest is consistent with the packaged compose files.
LINK_IMAGE = "bbernhard/signal-cli-rest-api:latest"

# How long we are willing to wait for the ephemeral container to become healthy.
LINK_HEALTH_TIMEOUT_SECONDS = 60


# --------------------------------------------------------------------------- #
# Small state used by the cleanup machinery
# --------------------------------------------------------------------------- #

_cleanup_state: dict[str, object] = {
    "user_compose_file": None,      # Path | None
    "stopped_user_service": False,
    "link_container_started": False,
}


def _reset_cleanup_state() -> None:
    """Reset the module-level cleanup tracking state."""
    _cleanup_state.update({
        "user_compose_file": None,
        "stopped_user_service": False,
        "link_container_started": False,
    })


def _get_user_compose_file() -> Optional[Path]:
    """Return the compose file we are managing, if any."""
    return _cleanup_state.get("user_compose_file")  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Low-level docker helpers
# --------------------------------------------------------------------------- #

def is_docker_available() -> bool:
    """Return True if the docker CLI is present and the daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except Exception:
        return False


def _run_docker(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a docker command and return the CompletedProcess (never raises)."""
    try:
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:
        # Return a fake failed process so callers can treat it uniformly.
        return subprocess.CompletedProcess(["docker", *args], 1, "", "exception")


def is_container_running(name: str) -> bool:
    """Return True if a container with the given name is currently running."""
    proc = _run_docker(["ps", "--filter", f"name={name}", "--format", "{{.Names}}"], timeout=5)
    return name in (proc.stdout or "")


def stop_container(name: str, timeout: int = 10) -> bool:
    """Best-effort stop + rm of a container by name. Returns True on success."""
    # Try graceful stop first
    stop = _run_docker(["stop", name], timeout=timeout)
    # Always try rm (it may already be stopped or --rm handled it)
    rm = _run_docker(["rm", "-f", name], timeout=5)
    return stop.returncode == 0 or rm.returncode == 0


def get_container_logs(name: str, tail: int = 80) -> str:
    """Return recent logs for a container (best effort)."""
    proc = _run_docker(["logs", "--tail", str(tail), "--no-color", name], timeout=5)
    return (proc.stdout or "") + (proc.stderr or "")


# --------------------------------------------------------------------------- #
# User's normal service (the one defined by their docker-compose.yml)
# --------------------------------------------------------------------------- #

def has_standard_local_compose() -> bool:
    """True if the standard ~/.signal-cli/docker-compose.yml exists."""
    return get_docker_compose_path().exists()


def _get_user_compose_args(compose_file: Optional[Path] = None) -> list[str]:
    path = compose_file or get_docker_compose_path()
    return ["-f", str(path)]


def stop_user_service(compose_file: Optional[Path] = None) -> bool:
    """Stop the user's normal signal service using their compose file.

    Returns True if we actually stopped something (or it was already down).
    """
    if not is_docker_available():
        return False

    args = ["compose", *_get_user_compose_args(compose_file), "down", "--remove-orphans"]
    proc = _run_docker(args, timeout=20)
    # We consider "down" successful even if the compose file had nothing running.
    return proc.returncode == 0


def start_user_service(compose_file: Optional[Path] = None) -> bool:
    """Start the user's normal signal service using their compose file."""
    if not is_docker_available():
        return False

    args = [
        "compose",
        *_get_user_compose_args(compose_file),
        "up",
        "-d",
        "--quiet-pull",
    ]
    proc = _run_docker(args, timeout=60)
    return proc.returncode == 0


# --------------------------------------------------------------------------- #
# Ephemeral link-only container (MODE=native)
# --------------------------------------------------------------------------- #

def _build_link_run_args() -> list[str]:
    """Return the argv for the `docker run` that starts the link container."""
    home = Path.home()
    data_dir = home / ".signal-cli" / "signal-data"

    # We deliberately bind only to localhost for safety.
    return [
        "run",
        "-d",
        "--name", LINK_CONTAINER_NAME,
        "--rm",
        "-e", "MODE=native",
        "-p", "127.0.0.1:8080:8080",
        "-v", f"{data_dir}:/home/.local/share/signal-cli",
        LINK_IMAGE,
    ]


def start_ephemeral_link_container() -> bool:
    """Start the dedicated MODE=native link container.

    The caller is responsible for ensuring the normal service is already down
    (otherwise we will have a port conflict).
    """
    if not is_docker_available():
        return False

    # Make sure any stale container is gone
    if is_container_running(LINK_CONTAINER_NAME):
        stop_container(LINK_CONTAINER_NAME)

    # Ensure the data directory exists (docker will create it, but nice to have)
    data_dir = Path.home() / ".signal-cli" / "signal-data"
    data_dir.mkdir(parents=True, exist_ok=True)

    proc = _run_docker(_build_link_run_args(), timeout=60)
    if proc.returncode != 0:
        return False

    _cleanup_state["link_container_started"] = True
    return True


def wait_for_link_container_healthy(timeout: int = LINK_HEALTH_TIMEOUT_SECONDS) -> bool:
    """Poll the link container's health endpoint until it responds or we time out."""
    deadline = time.time() + timeout
    url = f"{DEFAULT_LINK_API_URL}/v1/about"

    while time.time() < deadline:
        try:
            # We use a plain curl inside the container or a quick HTTP request.
            # Using the host's curl keeps it simple and doesn't require requests.
            proc = _run_docker(
                ["exec", LINK_CONTAINER_NAME, "curl", "-sf", "http://localhost:8080/v1/about"],
                timeout=3,
            )
            if proc.returncode == 0:
                return True
        except Exception:
            pass

        # Also accept a direct host-side check in case exec is slow
        try:
            proc = _run_docker(
                ["run", "--rm", "--network", "host", "curlimages/curl", "-sf", url],
                timeout=3,
            )
            if proc.returncode == 0:
                return True
        except Exception:
            pass

        time.sleep(1.5)

    return False


def stop_ephemeral_link_container() -> bool:
    """Stop and remove the ephemeral link container. Safe to call repeatedly."""
    if not is_docker_available():
        return False

    success = stop_container(LINK_CONTAINER_NAME)
    if success:
        _cleanup_state["link_container_started"] = False
    return success


# --------------------------------------------------------------------------- #
# Bulletproof cleanup
# --------------------------------------------------------------------------- #

def _perform_cleanup() -> None:
    """Idempotent cleanup function called from finally / atexit / signal handlers."""
    try:
        # 1. Always try to stop the link container if we started it (or if it exists).
        if _cleanup_state.get("link_container_started") or is_container_running(LINK_CONTAINER_NAME):
            stop_ephemeral_link_container()

        # 2. If we were the ones who stopped the user's normal service, bring it back.
        if _cleanup_state.get("stopped_user_service"):
            compose = _get_user_compose_file()
            start_user_service(compose)
    except Exception:
        # Never let cleanup itself raise and mask the original exception.
        pass
    finally:
        _reset_cleanup_state()


def _register_cleanup_handlers() -> None:
    """Register atexit and signal handlers so cleanup runs even on Ctrl-C or kill."""
    # atexit is the most reliable for normal Python exits.
    atexit.register(_perform_cleanup)

    # Handle common signals that can kill the process during an interactive link.
    def _signal_handler(signum, frame):
        _perform_cleanup()
        # Re-raise the default handler so the process actually exits.
        if signum == signal.SIGINT:
            raise KeyboardInterrupt
        # For other signals we just exit after cleanup.
        os._exit(128 + signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _signal_handler)
        except Exception:
            # Some environments (e.g. threads, certain Windows builds) may not allow this.
            pass


# --------------------------------------------------------------------------- #
# Public context manager – the main API
# --------------------------------------------------------------------------- #

@contextmanager
def ephemeral_link_container(
    *,
    manage_user_service: bool = True,
    compose_file: Optional[Path] = None,
) -> Iterator[bool]:
    """Context manager that provides a temporary MODE=native link container.

    Usage:

        with ephemeral_link_container() as ready:
            if ready:
                # do the actual linking against http://localhost:8080
                ...
            else:
                # docker not available or start failed – caller can fall back

    On exit (including exceptions and KeyboardInterrupt) the context manager
    guarantees:
      - the ephemeral `signal-cli-link` container is stopped/removed
      - the user's normal service (from their compose file) is restarted if we
        stopped it on entry.

    Args:
        manage_user_service: If True (default), we will stop the user's normal
            service on entry (if it is running) and restart it on exit.
        compose_file: Override the compose file used to manage the user's service.
            Defaults to the standard ~/.signal-cli/docker-compose.yml.
    """
    if not is_docker_available():
        yield False
        return

    user_compose = compose_file or get_docker_compose_path()
    _reset_cleanup_state()
    _cleanup_state["user_compose_file"] = user_compose

    started_link = False
    stopped_user = False

    try:
        # Optionally stop the user's normal service so we can take over port 8080
        # and the shared data directory safely.
        if manage_user_service and has_standard_local_compose():
            if is_container_running("signal-cli"):  # the name used in our compose files
                stop_user_service(user_compose)
                stopped_user = True
            _cleanup_state["stopped_user_service"] = stopped_user

        # Start the dedicated link container
        if not start_ephemeral_link_container():
            yield False
            return

        started_link = True

        # Wait until the REST API inside it is healthy
        if not wait_for_link_container_healthy():
            # Clean up immediately; the caller will see False
            stop_ephemeral_link_container()
            yield False
            return

        # Everything is ready for the caller to perform linking.
        _register_cleanup_handlers()
        yield True

    except Exception:
        # Any unexpected error still triggers cleanup
        raise
    finally:
        # The atexit / signal handlers will also call _perform_cleanup,
        # but calling it here is safe and gives deterministic behavior
        # for the normal "with" exit path.
        _perform_cleanup()


# --------------------------------------------------------------------------- #
# Convenience helper used by the CLI
# --------------------------------------------------------------------------- #

def should_auto_manage_for_linking(config: Optional[SignalConfig] = None) -> bool:
    """Return True if we believe we should automatically manage an ephemeral
    link container for the current configuration.

    Heuristic:
      - Docker is available
      - The standard local compose file exists
      - The configured API URL looks like our local default (localhost:8080)
    """
    if not is_docker_available():
        return False
    if not has_standard_local_compose():
        return False

    cfg = config or SignalConfig()
    url = (cfg.api_url or "").lower()
    return url.startswith("http://localhost:8080") or url.startswith("http://127.0.0.1:8080")