"""Compute a SHA-256 digest for an immutable reference artifact available on local disk."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    print(f"{sha256_file(args.path)}  {args.path.as_posix()}")


if __name__ == "__main__":
    main()
