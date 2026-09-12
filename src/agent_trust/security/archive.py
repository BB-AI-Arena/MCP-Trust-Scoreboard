"""Bounded ZIP validation; submitted source is never executed."""

from __future__ import annotations

import posixpath
import stat
import zipfile


class UnsafeArchive(ValueError):
    pass


def validate_zip(data: bytes, *, max_members: int = 2_000, max_uncompressed_bytes: int = 50_000_000) -> list[str]:
    if len(data) > max_uncompressed_bytes:
        raise UnsafeArchive("compressed archive exceeds request limit")
    try:
        archive = zipfile.ZipFile(__import__("io").BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UnsafeArchive("invalid ZIP archive") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > max_members:
            raise UnsafeArchive("archive contains too many members")
        total = 0
        names = []
        for info in infos:
            normalized = posixpath.normpath(info.filename)
            if normalized.startswith("../") or normalized == ".." or normalized.startswith("/"):
                raise UnsafeArchive("archive path escapes extraction root")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise UnsafeArchive("symbolic links are not accepted")
            total += info.file_size
            if total > max_uncompressed_bytes:
                raise UnsafeArchive("archive expands beyond resource limit")
            names.append(normalized)
    return names
