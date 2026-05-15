from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import fsspec  # type: ignore

from ..error import Error


def infer_format(path: Path, *, raise_missing: bool = False):
    format = Path(path).suffix[1:]
    if format == "yml":
        format = "yaml"
    elif format == "rdf":
        format = "xml"
    if not format and raise_missing:
        raise Error(f"Cannot infer format from path: {path}")
    return format


def infer_basepath(path: Path) -> str:
    basepath = str(Path(path).parent)
    if is_file_protocol_path(path):
        if not Path(basepath).is_absolute():
            basepath = str(Path(path).resolve().parent)
    return basepath


def ensure_basepath(path: Path, basepath: Optional[Path] ) -> Tuple[str, str]:
    if basepath:
        path = Path(join_basepath(path, basepath))
    else:
        basepath = Path(infer_basepath(path))
    return str(path), str(basepath)


def join_basepath(path:  Path, basepath: Optional[Path] = None) -> str:
    if not basepath:
        return str(path)
    if not is_file_protocol_path(path):
        return str(path)
    if not is_file_protocol_path(basepath):
        return f"{basepath}/{path}"
    return str(Path(basepath) / path)


def is_file_protocol_path(path: Path) -> bool:
    info = fsspec.utils.infer_storage_options(path)  # type: ignore
    return info.get("protocol") == "file"  # type: ignore


def is_http_or_ftp_protocol_path(path: Path) -> bool:
    info = fsspec.utils.infer_storage_options(path)  # type: ignore
    return info.get("protocol") in ["http", "https", "ftp", "ftps"]  # type: ignore


def assert_safe_path(path: Path, *, basepath: Optional[str] = None):
    """Assert that the path (untrusted) is not outside the basepath (trusted)"""
    if is_file_protocol_path(path):
        try:
            root = (Path(basepath) if basepath else Path.cwd()).resolve()
            item = root.joinpath(path).resolve()
            item.relative_to(root)
        except Exception:
            raise Error(f"Path is not safe: {path}")
