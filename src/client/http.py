from __future__ import annotations

import json
import subprocess
from typing import Any

REQUEST_TIMEOUT = 15
_call_count = 0


class CurlResponse:
    """Lightweight response object matching requests.Response interface."""

    def __init__(self, status_code: int, body: str, headers: dict[str, str]) -> None:
        self.status_code = status_code
        self.text = body
        self.headers = headers
        self.content = body.encode()

    def json(self) -> Any:
        if not self.text.strip():
            return None
        return json.loads(self.text)


def _reset_call_count() -> None:
    global _call_count
    _call_count = 0


def _curl(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    auth: tuple[str, str] | None = None,
    json_payload: Any | None = None,
    data: str | None = None,
    timeout: int = REQUEST_TIMEOUT,
) -> CurlResponse:
    global _call_count
    _call_count += 1
    cmd = [
        "curl", "-s",
        "-X", method,
        "-w", "\n%{http_code}\n%{content_type}",
        "--max-time", str(timeout),
    ]
    if auth:
        cmd += ["-u", f"{auth[0]}:{auth[1]}"]
    all_headers = {"Connection": "close"}
    if headers:
        all_headers.update(headers)
    for k, v in all_headers.items():
        cmd += ["-H", f"{k}: {v}"]
    if json_payload is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(json_payload)]
    elif data is not None:
        cmd += ["-d", data]
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
    parts = result.stdout.rsplit("\n", 2)
    if len(parts) >= 3:
        body, status_str, content_type = parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        body, status_str = parts[0], parts[1]
        content_type = ""
    else:
        body, status_str, content_type = result.stdout, "0", ""
    status_code = int(status_str) if status_str.strip().isdigit() else 0
    resp_headers = {}
    if content_type:
        resp_headers["Content-Type"] = content_type
    return CurlResponse(status_code, body, resp_headers)
