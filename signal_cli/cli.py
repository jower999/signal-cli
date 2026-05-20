import typer
import base64
import json
import sys
import webbrowser
import urllib.parse
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from .config import (
    SignalConfig,
    install_docker_compose,
    get_docker_compose_path,
)
from .docker import (
    ephemeral_link_container,
    should_auto_manage_for_linking,
    LINK_CONTAINER_NAME,
)
from .signal_client import SignalClient

app = typer.Typer(help="Signal messaging client (send to groups and individuals)")


def get_config() -> SignalConfig:
    return SignalConfig.load()


@app.command()
def setup():
    """Interactive setup for Signal integration."""
    config = get_config()

    number = typer.prompt("Your Signal phone number (e.g. +491234567890)")
    api_url = typer.prompt("signal-cli-rest-api URL", default="http://localhost:8080")

    config.number = number
    config.api_url = api_url
    config.save()

    # Ensure the recommended docker-compose.yml exists (with MODE=json-rpc by default)
    wrote_compose = install_docker_compose()
    compose_path = get_docker_compose_path()

    typer.echo("✅ Basic configuration saved.")
    if wrote_compose:
        typer.echo(f"✅ Installed recommended docker-compose.yml at {compose_path}")
        typer.echo("   (Using MODE=json-rpc for best performance.)")
        typer.echo(
            "   Start it with: docker compose -f ~/.signal-cli/docker-compose.yml up -d"
        )
    elif compose_path.exists():
        typer.echo(f"ℹ️  Using existing docker-compose at {compose_path}")


@app.command("group-add")
def group_add(name: str, recipient: str):
    """Add or update a named recipient (can be a group ID or a phone number)."""
    config = get_config()
    config.recipients[name] = recipient
    config.save()
    typer.echo(f"✅ Recipient '{name}' saved.")


@app.command("group-list")
def group_list(
    available: bool = typer.Option(
        False,
        "--available",
        "--remote",
        help="List groups the linked Signal account is actually a member of (live from the service).",
    )
):
    """List saved named recipients, or live groups from Signal with --available."""
    config = get_config()

    if available:
        try:
            client = SignalClient(config)
            groups = client.list_remote_groups()
        except Exception as e:
            typer.echo(f"Failed to fetch groups from Signal: {e}")
            raise typer.Exit(1)

        if not groups:
            typer.echo(
                "No groups found for this account (or the account is not yet linked)."
            )
            return

        typer.echo("\nAvailable groups from your linked Signal account:\n")
        for i, g in enumerate(groups, 1):
            gid = g.get("id") or g.get("groupId") or g.get("internal_id", "unknown")
            name = g.get("name") or g.get("title") or "(no name)"
            members = g.get("members", [])
            is_admin = g.get("isAdmin", False)
            typer.echo(f"  {i}. {name}")
            typer.echo(f"     ID: {gid}")
            typer.echo(
                f"     Members: {len(members)}  |  Admin: {'yes' if is_admin else 'no'}"
            )
            typer.echo()

        # Interactive picker to save groups with friendly names
        if typer.confirm(
            "Would you like to save any of these groups with a friendly name?",
            default=False,
        ):
            for g in groups:
                gid = g.get("id") or g.get("groupId") or g.get("internal_id")
                if not gid:
                    continue
                default_name = g.get("name") or g.get("title") or ""
                if typer.confirm(
                    f"Save group '{default_name or gid}' ?", default=False
                ):
                    friendly = typer.prompt(
                        "Enter a friendly name for this group", default=default_name
                    )
                    if friendly:
                        config.recipients[friendly] = gid
                        config.save()
                        typer.echo(f"✅ Saved as '{friendly}'")
            typer.echo(
                "\nDone. Use 'group-list' (without --available) to see your saved names."
            )
        return

    # Default: list saved named recipients
    if not config.recipients:
        typer.echo(
            "No recipients configured yet. Use 'group-add <name> <id-or-phone>' or 'group-list --available' to discover groups."
        )
        return

    typer.echo("Saved recipients (groups and individuals):\n")
    for name, rid in config.recipients.items():
        typer.echo(f"  {name}: {rid}")


@app.command("group-remove")
def group_remove(name: str):
    """Remove a saved named recipient."""
    config = get_config()
    if name in config.recipients:
        del config.recipients[name]
        config.save()
        typer.echo(f"✅ Removed recipient '{name}'")
    else:
        typer.echo(f"Recipient '{name}' not found.")


@app.command()
def send(
    recipient: Optional[str] = typer.Option(
        None,
        "--recipient",
        "-r",
        help="Recipient name, group ID, or phone number (+467...). Use 'group-list --available' to discover groups.",
    ),
    group: Optional[str] = typer.Option(
        None,
        "--group",
        "-g",
        help="Deprecated alias for --recipient (kept for compatibility with --share).",
    ),
    message: Optional[str] = typer.Argument(
        None, help="Message text (not needed if --json is used)"
    ),
    images: Optional[List[Path]] = typer.Option(None, "--image", "-i"),
    json_input: bool = typer.Option(False, "--json"),
):
    """Send a message (with optional images) to a Signal recipient (group or individual)."""
    config = get_config()

    if not config.number:
        typer.echo("Please run `signal-cli setup` first.")
        raise typer.Exit(1)

    # Support both --recipient (new) and --group (legacy alias)
    target = recipient or group

    attachments = []

    if json_input:
        data = json.load(sys.stdin)
        message = data.get("message") or message
        target = data.get("recipient") or data.get("group") or target
        attachments = data.get("attachments", [])
    else:
        if images:
            for img_path in images:
                if str(img_path) in ("-", "/dev/stdin"):
                    raw = sys.stdin.buffer.read()
                    if not raw:
                        typer.echo(
                            "Error: No image data received on stdin for --image -"
                        )
                        raise typer.Exit(1)
                    b64 = base64.b64encode(raw).decode("utf-8")
                    attachments.append({"filename": "image.png", "data": b64})
                elif not img_path.exists():
                    typer.echo(f"Image not found: {img_path}")
                    raise typer.Exit(1)
                else:
                    with open(img_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                        attachments.append({"filename": img_path.name, "data": data})

    if not target:
        typer.echo(
            "Missing recipient. Use --recipient / -r (or the legacy --group / -g)."
        )
        raise typer.Exit(1)

    if not message and not attachments:
        typer.echo(
            "Error: MESSAGE is required (or provide attachments via --json or --image)"
        )
        raise typer.Exit(1)

    client = SignalClient(config)
    result = client.send(message, recipient=target, attachments=attachments)
    typer.echo(f"✅ Message sent. Timestamp: {result.get('timestamp')}")


def _perform_link_request(config: SignalConfig, device_name: str) -> None:
    """Core logic that talks to /v1/qrcodelink and presents the QR code.

    Extracted so it can be called from inside or outside the ephemeral container
    context manager.
    """
    if not config.api_url:
        typer.echo("No API URL configured. Please run 'signal-cli setup' first.")
        raise typer.Exit(1)

    url = f"{config.api_url}/v1/qrcodelink?device_name={device_name}"

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        is_png = "image" in content_type or response.content[:8] == b"\x89PNG\r\n\x1a\n"

        typer.echo("\n✅ Linking QR code generated!")

        if is_png:
            png_path = Path(tempfile.gettempdir()) / "signal-cli-link-qr.png"
            png_path.write_bytes(response.content)

            typer.echo(f"\nQR code saved as PNG: {png_path}")
            typer.echo("Opening image viewer...")

            try:
                subprocess.run(["open", str(png_path)], check=False)
                typer.echo("→ QR code image opened in your default image viewer.")
            except Exception:
                typer.echo("→ Could not auto-open the image.")
                typer.echo(f"   Please open this file manually:\n   {png_path}")

            linking_uri = "(binary PNG QR code returned by API)"

        else:
            linking_uri = response.text.strip()

            typer.echo(f"\nLinking URI:\n{linking_uri}\n")

            encoded_uri = urllib.parse.quote(linking_uri, safe="")
            qr_url = f"https://quickchart.io/qr?text={encoded_uri}&size=300"

            try:
                webbrowser.open(qr_url)
                typer.echo("→ A QR code has been opened in your browser.")
            except Exception:
                typer.echo("→ Could not open browser automatically.")
                typer.echo(
                    f"   Open this link manually to see the QR code:\n   {qr_url}"
                )

        typer.echo("\nNext steps:")
        typer.echo("1. Open the Signal app on your **phone**")
        typer.echo("2. Go to Profile → Linked Devices → 'Link New Device'")
        typer.echo("3. Scan the QR code")
        typer.echo("\nAfter scanning, wait 10–20 seconds, then run:")
        typer.echo("  signal-cli status")

    except requests.exceptions.RequestException as e:
        typer.echo(f"Failed to generate linking URI: {e}")
        typer.echo(
            "Make sure the signal-cli-rest-api is running on the configured URL."
        )
        compose_path = get_docker_compose_path()
        typer.echo(
            "If linking fails with UnsupportedOperationException or similar errors, "
            "the `link` command normally starts a temporary dedicated container "
            "using MODE=native. If that also fails, you can try stopping any running "
            "signal container and running the link command again."
        )
        typer.echo(f"Compose file location: {compose_path}")
        raise typer.Exit(1)


@app.command()
def link(device_name: str = "signal-cli"):
    """Generate a linking QR code and open it in your browser.

    When a standard local docker-compose.yml is present, `signal-cli link`
    automatically manages a short-lived container (MODE=native) that is
    optimized for reliable device linking. Your normal service (whatever
    MODE you have configured) is left untouched and is restarted afterwards.
    """
    config = get_config()

    if should_auto_manage_for_linking(config):
        # Use the ephemeral MODE=native container for the duration of linking.
        # The context manager guarantees cleanup + restart of the user's normal
        # service even on Ctrl-C, exceptions, or process termination.
        with ephemeral_link_container() as ready:
            if not ready:
                typer.echo(
                    "Could not start the dedicated linking container. "
                    "Falling back to direct call against the configured API URL."
                )
                _perform_link_request(config, device_name)
                return

            typer.echo("Using temporary dedicated linking service (MODE=native)...")
            _perform_link_request(config, device_name)
            # The context manager will clean up and restart the normal service.
        return

    # Remote / custom setup – just talk to whatever the user configured.
    _perform_link_request(config, device_name)


if __name__ == "__main__":
    app()
