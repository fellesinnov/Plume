"""Read-only, exact Git-blob identity checks for reference worktree artifacts.

A Windows clone created before References/** -text may still contain CRLF
working copies of original LF text blobs. The canonical candidate below is
constructed in memory *only* and must match both exact pinned byte size and
full Git SHA-1 blob identity. This never edits or relaxes the Git evidence.
"""

from __future__ import annotations

import hashlib


class ReferenceIdentityError(ValueError):
    """Worktree content does not correspond to the pinned original Git blob."""


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def check_pinned_worktree(
    data: bytes,
    *,
    size_bytes: int,
    git_sha: str,
    tolerate_windows_crlf: bool = False,
) -> bool:
    """Verify exact pinned Git content; return whether worktree is byte exact.

    Return True only for exact worktree bytes. Return False only when a pure
    CRLF-to-LF reconstruction in memory matches the original pinned Git blob
    identically, byte size AND SHA. The caller must permit this *only* for
    known text fixtures on Windows. No file is modified or normalized in place.
    """
    if len(data) == size_bytes and git_blob_sha(data) == git_sha:
        return True
    if tolerate_windows_crlf and b"\r\n" in data:
        original_candidate = data.replace(b"\r\n", b"\n")
        if (len(original_candidate) == size_bytes
                and git_blob_sha(original_candidate) == git_sha):
            return False
    raise ReferenceIdentityError(
        f"worktree size {len(data)} / Git blob {git_blob_sha(data)} "
        f"does not match pinned size {size_bytes} / Git blob {git_sha}; "
        "content is neither exact nor a proven checkout-only CRLF conversion"
    )
