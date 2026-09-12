"""Legacy collector URL guard; private targets require explicit scope."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeCollectorURL(ValueError):
    pass


def validate_collector_url(url: str, *, allow_private: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UnsafeCollectorURL("only absolute HTTP(S) URLs are supported")
    if parsed.username or parsed.password:
        raise UnsafeCollectorURL("URL credentials are not accepted")
    host = parsed.hostname.rstrip(".").lower()
    if not allow_private:
        try:
            addresses = [ipaddress.ip_address(host)]
        except ValueError:
            try:
                addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)]
            except (socket.gaierror, OSError, ValueError) as exc:
                raise UnsafeCollectorURL("hostname could not be safely resolved") from exc
        if any(address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast or str(address) == "169.254.169.254" for address in addresses):
            raise UnsafeCollectorURL("private collector targets require explicit scope")
    return url
