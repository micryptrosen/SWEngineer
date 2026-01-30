from __future__ import annotations

import hashlib
import json
from typing import Any, Dict

from app.validation.schema_validation import compute_payload_sha256, payload_sha_is_accepted


def _sample_body() -> Dict[str, Any]:
    return {"alpha": 1, "beta": {"x": True, "y": "z"}}


def test_canonical_sha_is_accepted() -> None:
    body = _sample_body()
    sha = compute_payload_sha256(body)
    assert payload_sha_is_accepted(body, sha)


def test_empty_sha_is_rejected() -> None:
    body = _sample_body()
    assert not payload_sha_is_accepted(body, "")
    assert not payload_sha_is_accepted(body, "   ")


def test_garbage_sha_is_rejected() -> None:
    body = _sample_body()
    assert not payload_sha_is_accepted(body, "00" * 32)  # unlikely to match any real digest


def test_pretty_json_variants_are_accepted_windowed() -> None:
    body = _sample_body()

    # Pretty + LF
    pretty_lf = json.dumps(body, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    sha_pretty_lf = hashlib.sha256(pretty_lf.encode("utf-8")).hexdigest()
    assert payload_sha_is_accepted(body, sha_pretty_lf)

    # Pretty + CRLF
    pretty_crlf = pretty_lf.replace("\n", "\r\n")
    sha_pretty_crlf = hashlib.sha256(pretty_crlf.encode("utf-8")).hexdigest()
    assert payload_sha_is_accepted(body, sha_pretty_crlf)