import mimetypes
import warnings
from typing import List, Dict, Optional

import requests

from .config import SignalConfig


class SignalClient:
    """
    Client for sending messages and attachments via signal-cli-rest-api.

    Can be used either with a SignalConfig or with direct credentials.
    Standalone usage with explicit number/api_url is fully supported.
    """

    def __init__(
        self,
        config: Optional[SignalConfig] = None,
        number: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        """
        Create a SignalClient.

        Args:
            config: A SignalConfig instance (provides number, api_url, and named recipients).
            number: Override the sending phone number (E.164 format).
            api_url: Override the signal-cli-rest-api base URL.
        """
        if config is None:
            config = SignalConfig()

        self.config = config
        self._number = number or config.number
        self._api_url = api_url or config.api_url

    @property
    def number(self) -> Optional[str]:
        return self._number

    @property
    def api_url(self) -> str:
        return self._api_url

    # ------------------------------------------------------------------ #
    # Core sending
    # ------------------------------------------------------------------ #
    def send(
        self,
        message: str,
        recipient: Optional[str] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        *,
        # Deprecated alias kept for backward compatibility during transition
        group: Optional[str] = None,
    ) -> dict:
        """
        Send a text message (optionally with attachments) to a recipient.

        The recipient can be:
        - A friendly name saved in config.recipients
        - A raw Signal group ID (group.XXXX...)
        - A phone number in E.164 format (+467...)

        Args:
            message: Text to send.
            recipient: Target (name, group ID, or phone number). Preferred parameter.
            attachments: Optional list of {"filename": , "data": base64} dicts.
            group: Deprecated alias for recipient. Will be removed in 0.3.0.
        """
        if group is not None:
            if recipient is None:
                recipient = group
            else:
                raise ValueError("Specify either 'recipient' or 'group', not both.")
            warnings.warn(
                "The 'group' parameter is deprecated. Use 'recipient' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        if not recipient:
            raise ValueError("recipient is required")

        recipient_id = self.config.resolve_recipient(recipient)

        if not self.number:
            raise RuntimeError(
                "No sending phone number configured. "
                "Run `signal-cli setup` or pass number= to SignalClient()."
            )

        payload: Dict[str, object] = {
            "number": self.number,
            "message": message,
            "recipients": [recipient_id],
        }

        if attachments:
            payload["base64_attachments"] = [
                self._format_attachment(att) for att in attachments
            ]

        response = requests.post(
            f"{self.api_url}/v2/send",
            json=payload,
            timeout=60,
        )

        if not response.ok:
            # Try to extract the real error message from the API response
            try:
                err = response.json().get("error") or response.text
            except Exception:
                err = response.text or str(response.status_code)
            raise RuntimeError(
                f"Failed to send message (HTTP {response.status_code}): {err}"
            )

        return response.json()

    # ------------------------------------------------------------------ #
    # Group discovery (powers `group list --available`)
    # ------------------------------------------------------------------ #
    def list_remote_groups(self) -> List[dict]:
        """
        Fetch the list of Signal groups the linked account is a member of.

        This calls the signal-cli-rest-api endpoint:
            GET /v1/groups/{number}

        Returns the raw list of group objects (containing id, name, members, etc.).
        """
        if not self.number:
            raise RuntimeError(
                "Cannot list groups: no phone number is configured on this client."
            )

        url = f"{self.api_url}/v1/groups/{self.number}"
        resp = requests.get(url, timeout=30)

        if not resp.ok:
            try:
                err = resp.json().get("error") or resp.text
            except Exception:
                err = resp.text or str(resp.status_code)
            raise RuntimeError(
                f"Failed to list groups (HTTP {resp.status_code}): {err}"
            )

        return resp.json()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _format_attachment(attachment: Dict[str, str]) -> str:
        data = attachment["data"]
        if data.startswith("data:"):
            return data

        filename = attachment.get("filename", "attachment.bin")
        mime_type = (
            attachment.get("content_type")
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )
        return f"data:{mime_type};filename={filename};base64,{data}"
