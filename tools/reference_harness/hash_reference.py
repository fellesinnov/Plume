"""Compute content identities for an immutable reference artifact available on local disk."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def _read_chunks(path: Path):  # type: ignore[no-untyped-def]
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            yield chunk


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    for chunk in _read_chunks(Path(path)):
        digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha_file(path: str | Path) -> str:
    target = Path(path)
    digest = hashlib.sha1()
    digest.update(f"blob {target.stat().st_size}\0".encode("ascii"))
    for chunk in _read_chunks(target):
        digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(f"sha256 {sha256_file(args.path)}  {args.path.as_posix()}")
    print(f"gitblob {git_blob_sha_file(args.path)}  {args.path.as_posix()}")


if __name__ == "__main__":
    main()
