"""Conservative URL validation for collectors and provider endpoints."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURL(ValueError):
    pass


def validate_url(url: str, *, allowed_hosts: set[str] | None = None, allow_private: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeURL("only absolute HTTP(S) URLs are supported")
    if parsed.username or parsed.password:
        raise UnsafeURL("userinfo in URLs is not allowed")
    host = parsed.hostname.rstrip(".").lower()
    if allowed_hosts is not None and host not in {item.lower() for item in allowed_hosts}:
        raise UnsafeURL("host is not in the configured allowlist")
    if not allow_private:
        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            try:
                addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)]
            except (socket.gaierror, OSError, ValueError):
                raise UnsafeURL("hostname could not be safely resolved")
        if any(address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast or str(address) == "169.254.169.254" for address in addresses):
            raise UnsafeURL("private, loopback, link-local, reserved, or metadata targets require explicit collector scope")
    return url
