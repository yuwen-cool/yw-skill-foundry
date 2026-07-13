#!/usr/bin/env python3
"""Build deterministic YW SkillFoundry tar.gz and zip release archives."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import os
import re
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePath

from privacy_lint import scan_record


RELEASE_FILES = {
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "PRIVACY.md",
    "README.md",
    "SECURITY.md",
    "SKILL.md",
    "SUPPORT.md",
    "VERSION",
    "log.md.example",
    "requirements.txt",
    "evals/README.md",
    "evals/trigger_cases.example.jsonl",
    "evals/routing-2026-07-13-v3/README.md",
    "evals/routing-2026-07-13-v3/description-after.md",
    "evals/routing-2026-07-13-v3/description-before.md",
    "evals/routing-2026-07-13-v3/fixture.jsonl",
    "evals/routing-2026-07-13-v3/judgments-after.jsonl",
    "evals/routing-2026-07-13-v3/judgments-before.jsonl",
    "examples/run-compare-bug-report.md",
    "examples/run-compare-pr-describe.md",
    "examples/worked-example.md",
    "references/anti-patterns.md",
    "references/architecture.md",
    "references/behavior-control.md",
    "references/craft-and-voice.md",
    "references/description-and-triggering.md",
    "references/evidence-schema.md",
    "references/invariants.md",
    "references/iteration.md",
    "references/prompt-patterns.md",
    "references/quality-assurance.md",
    "scripts/citation_lint.py",
    "scripts/contract_eval.py",
    "scripts/ensure-log.sh",
    "scripts/evidence.py",
    "scripts/frontmatter.py",
    "scripts/package-release.py",
    "scripts/privacy_lint.py",
    "scripts/regress.sh",
    "scripts/self-check.sh",
    "scripts/skill_library_audit.py",
    "scripts/trigger_eval.py",
    "scripts/validate-skill.sh",
    "templates/scaffold-starter.md",
    "templates/skill-starter.md",
}
RELEASE_SCAN_DIRS = {"evals", "examples", "references", "scripts", "templates"}
RELEASE_ROOT_FILES = {name for name in RELEASE_FILES if "/" not in name}
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
VERSION_RX = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class PackageError(ValueError):
    pass


@dataclass(frozen=True)
class ArchiveEntry:
    relative: str
    data: bytes
    mode: int


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def valid_file(path: Path) -> bool:
    return (
        path.is_file()
        and not path.is_symlink()
        and not any(part in EXCLUDED_PARTS for part in path.parts)
        and path.name != ".DS_Store"
        and path.suffix not in EXCLUDED_SUFFIXES
    )


def allowed_relative(relative: str) -> bool:
    path = Path(relative)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and not any(part in EXCLUDED_PARTS for part in path.parts)
        and path.name != ".DS_Store"
        and path.suffix not in EXCLUDED_SUFFIXES
    )


def tracked_entries(root: Path) -> list[ArchiveEntry]:
    try:
        raw = subprocess.check_output(
            ["git", "ls-tree", "-rz", "--full-tree", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PackageError(f"cannot enumerate committed files: {exc}") from exc
    entries: list[ArchiveEntry] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode_bytes, object_type, object_id = metadata.split()
        relative = os.fsdecode(raw_path)
        if not allowed_relative(relative):
            raise PackageError(f"committed release input is excluded or unsafe: {relative}")
        if object_type != b"blob" or mode_bytes not in {b"100644", b"100755"}:
            raise PackageError(
                f"committed release input must be a regular file: {relative} "
                f"({mode_bytes.decode()} {object_type.decode()})"
            )
        try:
            data = subprocess.check_output(
                ["git", "cat-file", "blob", object_id.decode("ascii")],
                cwd=root,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise PackageError(f"cannot read committed blob for {relative}: {exc}") from exc
        entries.append(
            ArchiveEntry(
                relative=relative,
                data=data,
                mode=0o755 if mode_bytes == b"100755" else 0o644,
            )
        )
    return sorted(entries, key=lambda entry: entry.relative)


def read_worktree_entry(root: Path, path: Path) -> ArchiveEntry:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise PackageError(f"cannot open release input without following links: {path}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise PackageError(f"release input is not a regular file: {path}")
        chunks: list[bytes] = []
        while chunk := os.read(fd, 1024 * 1024):
            chunks.append(chunk)
    finally:
        os.close(fd)
    return ArchiveEntry(
        relative=path.relative_to(root).as_posix(),
        data=b"".join(chunks),
        mode=0o755 if info.st_mode & 0o111 else 0o644,
    )


def working_tree_entries(root: Path) -> list[ArchiveEntry]:
    try:
        raw = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
        paths = [root / os.fsdecode(name) for name in raw.split(b"\0") if name]
    except (OSError, subprocess.CalledProcessError):
        paths = list(root.rglob("*"))
    return [
        read_worktree_entry(root, path)
        for path in sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())
        if valid_file(path)
    ]


def select_release_entries(entries: list[ArchiveEntry]) -> list[ArchiveEntry]:
    selected: list[ArchiveEntry] = []
    included = {entry.relative for entry in entries}
    missing = sorted(RELEASE_FILES - included)
    if missing:
        raise PackageError(
            f"release input lacks allowlisted file(s): {', '.join(missing)}"
        )

    for entry in entries:
        path = PurePath(entry.relative)
        in_release_scope = (
            entry.relative in RELEASE_ROOT_FILES
            or bool(path.parts and path.parts[0] in RELEASE_SCAN_DIRS)
        )
        if in_release_scope:
            findings = scan_record(
                f"release input:{entry.relative}", entry.relative, entry.data
            )
            if findings:
                rules = ", ".join(sorted({finding.rule for finding in findings}))
                raise PackageError(
                    f"privacy policy rejected release input {entry.relative}: {rules}"
                )
        if entry.relative in RELEASE_FILES:
            selected.append(entry)
    return sorted(selected, key=lambda entry: entry.relative)


def release_version(entries: list[ArchiveEntry]) -> str:
    version_entries = [entry for entry in entries if entry.relative == "VERSION"]
    if len(version_entries) != 1:
        raise PackageError(
            f"selected release input must contain exactly one VERSION, "
            f"found {len(version_entries)}"
        )
    try:
        version = version_entries[0].data.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise PackageError("selected VERSION is not valid UTF-8") from exc
    if not VERSION_RX.fullmatch(version):
        raise PackageError(f"selected VERSION must be X.Y.Z, got {version!r}")
    return version


def load_release(root: Path, source_mode: str) -> tuple[list[ArchiveEntry], str]:
    repository_entries = (
        tracked_entries(root)
        if source_mode == "tracked"
        else working_tree_entries(root)
    )
    entries = select_release_entries(repository_entries)
    if not entries:
        raise PackageError("release input is empty")
    return entries, release_version(entries)


def tar_bytes(entries: list[ArchiveEntry], prefix: str) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT) as tar:
            for entry in entries:
                info = tarfile.TarInfo(f"{prefix}/{entry.relative}")
                info.size = len(entry.data)
                info.mode = entry.mode
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                tar.addfile(info, io.BytesIO(entry.data))
    return raw.getvalue()


def zip_bytes(entries: list[ArchiveEntry], prefix: str) -> bytes:
    raw = io.BytesIO()
    with zipfile.ZipFile(
        raw, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for entry in entries:
            info = zipfile.ZipInfo(
                f"{prefix}/{entry.relative}", (1980, 1, 1, 0, 0, 0)
            )
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100000 | entry.mode) << 16
            archive.writestr(info, entry.data, compresslevel=9)
    return raw.getvalue()


def archive_payloads(entries: list[ArchiveEntry], version: str) -> dict[str, bytes]:
    prefix = f"yw-skill-foundry-{version}"
    return {
        f"{prefix}.tar.gz": tar_bytes(entries, prefix),
        f"{prefix}.zip": zip_bytes(entries, prefix),
    }


def write_new(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise PackageError(f"output must not be a symlink: {path}")
    if path.exists():
        raise PackageError(f"output already exists; refusing to overwrite: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fchmod(handle.fileno(), 0o644)
            os.fsync(handle.fileno())
        try:
            os.link(temp_name, path)
        except FileExistsError as exc:
            raise PackageError(
                f"output appeared during creation; refusing to overwrite: {path}"
            ) from exc
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-mode",
        choices=("tracked", "working-tree"),
        default="tracked",
        help="package Git-tracked files (release) or the public working tree (local smoke test)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    if output_dir.is_symlink():
        parser.error(f"output directory must not be a symlink: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve(strict=True)

    try:
        entries, version = load_release(root, args.source_mode)
        archives = archive_payloads(entries, version)
        for name, data in archives.items():
            write_new(output_dir / name, data)
        sums = "".join(
            f"{digest(data)}  {name}\n" for name, data in sorted(archives.items())
        ).encode("ascii")
        write_new(output_dir / "SHA256SUMS", sums)
    except (OSError, PackageError, tarfile.TarError) as exc:
        parser.error(str(exc))

    print(f"PASS  built deterministic YW SkillFoundry {version} archives in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
