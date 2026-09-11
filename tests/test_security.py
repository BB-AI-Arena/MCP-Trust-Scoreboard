import io
import zipfile

import pytest

from agent_trust.security.archive import UnsafeArchive, validate_zip
from agent_trust.security.egress import UnsafeURL, validate_url


def test_private_and_credential_urls_are_rejected():
    with pytest.raises(UnsafeURL):
        validate_url("http://127.0.0.1:8080/manifest")
    with pytest.raises(UnsafeURL):
        validate_url("https://user:pass@example.com/manifest", allow_private=True)


def test_zip_traversal_and_symlink_are_rejected():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("../../outside.txt", "bad")
    with pytest.raises(UnsafeArchive):
        validate_zip(stream.getvalue())


def test_safe_zip_is_bounded():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("src/main.py", "print('ok')")
    assert validate_zip(stream.getvalue()) == ["src/main.py"]
