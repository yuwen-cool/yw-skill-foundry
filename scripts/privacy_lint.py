#!/usr/bin/env python3
"""Reject private identifiers, sensitive files, and credential-shaped content."""

from __future__ import annotations

import argparse
import io
import os
import re
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    source: str
    rule: str
    line: int | None = None


HOME_PATH_RX = re.compile(
    r"(?:"
    + re.escape("/")
    + r"Users/[^/\s]+"
    + "|"
    + re.escape("/")
    + r"home/[^/\s]+"
    + r"|[A-Za-z]:[\\/](?:Users|Documents[ ]and[ ]Settings)[\\/][^\\/\s]+"
    + ")"
)
EMAIL_RX = re.compile(
    r"(?<![\w.+\[\]-])[\w.+\[\]-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"
)
UUID_RX = re.compile(
    r"(?i)(?<![0-9a-f])"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}(?![0-9a-f])"
)
RAW_ID_TOKEN_RX = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])"
    r"(?:provider|sess|session|run|judge|agent)_"
    r"[A-Za-z0-9][A-Za-z0-9_-]{5,}(?![A-Za-z0-9_-])"
)
STRUCTURED_RAW_ID_PATTERNS = (
    re.compile(
        r"""(?imx)
        ["'](?:provider|sess(?:ion)?|run|judge|agent)[_-]?id["']
        \s*:\s*["']?([A-Za-z0-9][A-Za-z0-9._:-]{5,})["']?
        """
    ),
    re.compile(
        r"""(?imx)
        ^[ \t]*(?:provider|sess(?:ion)?|run|judge|agent)[_-]?id
        [ \t]*:[ \t]*["']?([A-Za-z0-9][A-Za-z0-9._:-]{5,})["']?
        """
    ),
    re.compile(
        r"""(?mx)
        ^[ \t]*(?:export[ \t]+)?
        (?:PROVIDER|SESS(?:ION)?|RUN|JUDGE|AGENT)[_-]?ID
        [ \t]*=[ \t]*["']?([A-Za-z0-9][A-Za-z0-9._:-]{5,})["']?
        """
    ),
)
PUBLIC_RELEASE_ID_RX = re.compile(r"(?i)^(?:run|judge)-[a-z][0-9]+$")
SECRET_PATTERNS = (
    (
        "AWS access-key-shaped value",
        re.compile(r"\bA(?:K|S)IA[0-9A-Z]{16}\b"),
    ),
    (
        "GitHub token-shaped value",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    ),
    (
        "API token-shaped value",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    (
        "Slack token-shaped value",
        re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    ),
    (
        "private-key material",
        re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "assigned secret-shaped value",
        re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|token|
            password|passwd|client[_-]?secret)\s*[:=]\s*
            (?:
                ["'][^"'\r\n]{8,}["']
                |
                [A-Za-z0-9_~+/=-]{8,}
            )
            """
        ),
    ),
    (
        "bearer token-shaped value",
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]{20,}\b"),
    ),
    (
        "JWT-shaped value",
        re.compile(
            r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{5,}\."
            r"[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{10,}(?![A-Za-z0-9_-])"
        ),
    ),
)

PROHIBITED_DIRS = {
    ".agent",
    ".cache",
    ".claude",
    ".codex",
    ".cursor",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".vscode",
    "__pycache__",
    "cache",
    "caches",
    "logs",
    "memory",
    "notes",
    "private",
    "transcripts",
    "agent-transcripts",
    "chat-exports",
    "conversation-exports",
    "workspaces",
}
PROHIBITED_EXACT_FILES = {
    "handoff.md",
    "log.md",
    "credentials",
    "credentials.json",
    "credentials.yaml",
    "credentials.yml",
    "secrets",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "private.key",
    "conversations.json",
    "chat.json",
    "transcript.json",
}
LOCAL_DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
PRIVATE_KEY_SUFFIXES = {".key", ".p12", ".pem", ".pfx"}
SENSITIVE_FILE_RX = re.compile(
    r"""(?ix)
    ^(?:
        (?:private[._-]?key|id_(?:rsa|dsa|ecdsa|ed25519))(?:[._-].*)?
        |
        (?:provider|session|run|judge|agent)[._-]
        (?:metadata|meta|ids?|records?|state)(?:[._-].*)?
        |
        (?:chat|conversation|transcript)s?
        (?:[._-](?:export|dump|history|log))?(?:\.(?:jsonl?|txt|md|zip|html))?
    )$
    """
)


def generic_email_allowlist() -> set[str]:
    return {
        "project" + "@" + "example.com",
        "maintainer" + "@" + "example.org",
        "security" + "@" + "example.invalid",
        "support" + "@" + "github.com",
    }


def email_allowed(value: str) -> bool:
    lowered = value.lower()
    if lowered in generic_email_allowlist():
        return True
    local, _, domain = lowered.rpartition("@")
    if not local:
        return False
    # GitHub system addresses are public platform metadata, not personal contacts.
    if domain == "github.com" and local in {"noreply", "support"}:
        return True
    # Only the id-prefixed GitHub noreply form is allowed, including Dependabot
    # addresses such as 12345+dependabot[bot]@users.noreply.github.com.
    return domain == "users.noreply.github.com" and bool(
        re.fullmatch(r"[0-9]+\+[A-Za-z0-9][\w.\[\]-]{0,64}", local)
    )


def prohibited_path_reason(name: str) -> str | None:
    normalized = name.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    path = PurePosixPath(normalized)
    lowered = [part.lower() for part in path.parts]
    if any(part in PROHIBITED_DIRS for part in lowered[:-1]):
        return "prohibited private/cache/host-state directory"
    if not lowered:
        return None
    basename = lowered[-1]
    if basename.startswith(".env"):
        return "prohibited environment file"
    if basename.endswith(".log") or basename in PROHIBITED_EXACT_FILES:
        return "prohibited log/credential/private-note file"
    if re.match(r"^(?:credentials?|secrets?)(?:[._-]|$)", basename):
        return "prohibited credential/secret file"
    if SENSITIVE_FILE_RX.fullmatch(basename):
        return "prohibited private-key or provider metadata/export file"
    if PurePosixPath(basename).suffix in PRIVATE_KEY_SUFFIXES:
        return "prohibited private-key file"
    if PurePosixPath(basename).suffix in LOCAL_DB_SUFFIXES:
        return "prohibited local database"
    return None


def unsafe_archive_member_reason(name: str) -> str | None:
    if not name:
        return "empty archive member path"
    if name.startswith(("/", "\\")):
        return "absolute archive member path"
    if re.match(r"^[A-Za-z]:", name):
        return "drive-qualified archive member path"
    normalized = name.replace("\\", "/")
    if ".." in PurePosixPath(normalized).parts:
        return "archive member path traversal"
    return None


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def scan_record(source: str, name: str, data: bytes) -> list[Finding]:
    findings: list[Finding] = []
    path_reason = prohibited_path_reason(name)
    if path_reason:
        findings.append(Finding(source, path_reason))

    text = data.decode("utf-8", errors="replace")
    for match in HOME_PATH_RX.finditer(text):
        findings.append(
            Finding(source, "absolute personal home path", line_number(text, match.start()))
        )
    for match in EMAIL_RX.finditer(text):
        if not email_allowed(match.group(0)):
            findings.append(
                Finding(source, "personal email address", line_number(text, match.start()))
            )
    for match in UUID_RX.finditer(text):
        findings.append(
            Finding(source, "raw UUID-shaped identifier", line_number(text, match.start()))
        )
    for match in RAW_ID_TOKEN_RX.finditer(text):
        token = match.group(0)
        suffix = token.partition("_")[2]
        if any(character.isdigit() for character in suffix):
            findings.append(
                Finding(
                    source,
                    "raw provider/session/run/judge/agent identifier",
                    line_number(text, match.start()),
                )
            )
    for pattern in STRUCTURED_RAW_ID_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1)
            if not PUBLIC_RELEASE_ID_RX.fullmatch(value):
                findings.append(
                    Finding(
                        source,
                        "raw identifier in structured field",
                        line_number(text, match.start()),
                    )
                )
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(Finding(source, label, line_number(text, match.start())))
    return findings


def git_output(root: Path, args: list[str], *, input_data: bytes | None = None) -> bytes:
    return subprocess.check_output(
        ["git", *args],
        cwd=root,
        input=input_data,
        stderr=subprocess.DEVNULL,
    )


def is_git_repository(root: Path) -> bool:
    try:
        return git_output(root, ["rev-parse", "--is-inside-work-tree"]).strip() == b"true"
    except (OSError, subprocess.CalledProcessError):
        return False


def working_tree_records(root: Path) -> Iterable[tuple[str, str, bytes]]:
    if is_git_repository(root):
        raw = git_output(
            root, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"]
        )
        names = [os.fsdecode(item) for item in raw.split(b"\0") if item]
    else:
        names = [
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if ".git" not in path.parts
        ]
    for name in sorted(set(names)):
        path = root / name
        if not path.exists():
            continue
        if path.is_symlink():
            yield (f"working tree:{name}", name, b"")
            continue
        if path.is_file():
            yield (f"working tree:{name}", name, path.read_bytes())


def history_records(root: Path) -> Iterable[tuple[str, str, bytes]]:
    log_format = "%H%x00%ae%x00%ce%x00%B%x00"
    metadata = git_output(root, ["log", "--all", f"--format={log_format}"])
    yield ("Git commit metadata", "commit-metadata", metadata)

    tag_refs = git_output(root, ["for-each-ref", "--format=%(refname)", "refs/tags"])
    for raw_ref in tag_refs.splitlines():
        ref = os.fsdecode(raw_ref)
        if not ref:
            continue
        data = git_output(root, ["cat-file", "-p", ref])
        yield (f"Git tag metadata:{ref}", "tag-metadata", data)

    object_lines = git_output(root, ["rev-list", "--objects", "--all"]).splitlines()
    seen: set[str] = set()
    for raw_line in object_lines:
        object_id, _, raw_name = raw_line.partition(b" ")
        oid = object_id.decode("ascii")
        if oid in seen:
            continue
        seen.add(oid)
        if git_output(root, ["cat-file", "-t", oid]).strip() != b"blob":
            continue
        name = os.fsdecode(raw_name) if raw_name else "<unattributed-blob>"
        data = git_output(root, ["cat-file", "blob", oid])
        yield (f"Git blob:{oid[:12]}:{name}", name, data)


def archive_records(path: Path) -> Iterable[tuple[str, str, bytes]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                unsafe_reason = unsafe_archive_member_reason(info.filename)
                if unsafe_reason:
                    raise ValueError(
                        f"{path.name}: {unsafe_reason}: {info.filename!r}"
                    )
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise ValueError(
                        f"{path.name}: ZIP symlink member is prohibited: "
                        f"{info.filename!r}"
                    )
                if info.is_dir():
                    continue
                yield (f"archive:{path.name}:{info.filename}", info.filename, archive.read(info))
        return
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                unsafe_reason = unsafe_archive_member_reason(member.name)
                if unsafe_reason:
                    raise ValueError(
                        f"{path.name}: {unsafe_reason}: {member.name!r}"
                    )
                if member.issym() or member.islnk():
                    link_kind = "symlink" if member.issym() else "hardlink"
                    raise ValueError(
                        f"{path.name}: tar {link_kind} member is prohibited: "
                        f"{member.name!r}"
                    )
                if not member.isfile():
                    continue
                handle = archive.extractfile(member)
                if handle is not None:
                    yield (f"archive:{path.name}:{member.name}", member.name, handle.read())
        return
    raise ValueError(f"unsupported archive format: {path}")


def scan_records(records: Iterable[tuple[str, str, bytes]]) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    count = 0
    for source, name, data in records:
        count += 1
        findings.extend(scan_record(source, name, data))
    return findings, count


def self_test() -> int:
    failures: list[str] = []
    cases: list[tuple[str, str, bytes, str]] = [
        ("environment filename", ".env.local", b"", "prohibited environment file"),
        (
            "private key filename",
            "private" + ".key",
            b"",
            "prohibited log/credential/private-note file",
        ),
        (
            "private key suffix filename",
            "server" + ".key",
            b"",
            "prohibited private-key file",
        ),
    ]
    cases.extend(
        (
            f"{kind} metadata filename",
            kind + "-metadata.json",
            b"",
            "prohibited private-key or provider metadata/export file",
        )
        for kind in ("provider", "session", "run", "judge", "agent")
    )
    cases.extend(
        (
            f"{kind} export filename",
            kind + "-export.json",
            b"",
            "prohibited private-key or provider metadata/export file",
        )
        for kind in ("chat", "conversation", "transcript")
    )
    home_paths = (
        "/" + "Users" + "/" + "sample-user",
        "/" + "Users" + "/" + "sample-user" + "/project",
        "/" + "home" + "/" + "sample-user",
        "/" + "home" + "/" + "sample-user" + "/",
        "C:" + "\\" + "Users" + "\\" + "sample-user",
        "D:" + "/" + "Users" + "/" + "sample-user" + "/project",
    )
    cases.extend(
        (
            f"home path {index}",
            "README.md",
            value.encode(),
            "absolute personal home path",
        )
        for index, value in enumerate(home_paths, start=1)
    )
    private_mail = "person" + "@" + "personal.test"
    cases.append(
        ("personal email", "README.md", private_mail.encode(), "personal email address")
    )
    disallowed_noreply = "project" + "@" + "users.noreply.github.com"
    cases.append(
        (
            "non-generated GitHub noreply",
            "README.md",
            disallowed_noreply.encode(),
            "personal email address",
        )
    )
    for version in range(1, 9):
        raw_uuid = "-".join(
            ("12345678", "1234", f"{version}abc", "8def", "1234567890ab")
        )
        cases.append(
            (
                f"UUID v{version}",
                "README.md",
                raw_uuid.encode(),
                "raw UUID-shaped identifier",
            )
        )
    raw_tokens = (
        "provider" + "_" + "abc123456",
        "sess" + "_" + "abc123456",
        "run" + "_" + "abc123456",
        "judge" + "_" + "abc123456",
        "agent" + "_" + "abc123456",
    )
    cases.extend(
        (
            f"raw ID token {index}",
            "README.md",
            token.encode(),
            "raw provider/session/run/judge/agent identifier",
        )
        for index, token in enumerate(raw_tokens, start=1)
    )
    cases.extend(
        (
            f"structured {kind} ID",
            "record.json",
            ('"' + kind + '_id": "' + "abcdefghi" + '"').encode(),
            "raw identifier in structured field",
        )
        for kind in ("provider", "session", "run", "judge", "agent")
    )
    secret_values = (
        (
            "AWS access key",
            "AK" + "IA" + ("A" * 16),
            "AWS access-key-shaped value",
        ),
        (
            "GitHub fine-grained token",
            "github" + "_pat_" + ("A1" * 15),
            "GitHub token-shaped value",
        ),
        (
            "JWT",
            "eyJ" + ("a" * 8) + "." + ("b" * 8) + "." + ("c" * 16),
            "JWT-shaped value",
        ),
        (
            "unquoted API key assignment",
            "api" + "_key=" + ("z9" * 8),
            "assigned secret-shaped value",
        ),
        (
            "unquoted password assignment",
            "pass" + "word=" + ("q7" * 8),
            "assigned secret-shaped value",
        ),
        (
            "unquoted secret assignment",
            "sec" + "ret=" + ("r8" * 8),
            "assigned secret-shaped value",
        ),
        (
            "unquoted token assignment",
            "tok" + "en=" + ("t6" * 8),
            "assigned secret-shaped value",
        ),
        (
            "private key material",
            "-----BEGIN " + "PRIVATE" + " KEY-----",
            "private-key material",
        ),
    )
    cases.extend(
        (label, "README.md", value.encode(), expected)
        for label, value, expected in secret_values
    )

    for label, name, data, expected in cases:
        rules = {finding.rule for finding in scan_record(label, name, data)}
        if expected not in rules:
            failures.append(f"{label} bite did not trigger {expected!r}")

    good_mail = "project" + "@" + "example.com"
    github_mail = "noreply" + "@" + "github.com"
    github_support_mail = "support" + "@" + "github.com"
    github_user_mail = "12345+project" + "@" + "users.noreply.github.com"
    github_bot_mail = "49699333+dependabot[bot]" + "@" + "users.noreply.github.com"
    clean = scan_record(
        "clean",
        "README.md",
        (
            f"Public fixture contacts: {good_mail}, {github_mail}, "
            f"{github_support_mail}, {github_user_mail}, {github_bot_mail}. "
            "A run and judge can inspect an agent session. "
            "Release labels run-a1 and judge-b1 are public. "
            + ('"' + "run_id" + '": "' + "run-a1" + '", ')
            + ('"' + "judge_id" + '": "' + "judge-b1" + '"')
        ).encode(),
    )
    if clean:
        failures.append(f"clean positive path produced {len(clean)} finding(s)")

    def archive_rejected(path: Path) -> bool:
        try:
            list(archive_records(path))
        except ValueError:
            return True
        return False

    with tempfile.TemporaryDirectory(prefix="privacy-lint-self-test-") as raw_tmp:
        tmp = Path(raw_tmp)
        tar_bites = (
            ("tar symlink", "safe/link", tarfile.SYMTYPE, "target"),
            ("tar hardlink", "safe/link", tarfile.LNKTYPE, "target"),
            ("tar absolute path", "/absolute.txt", tarfile.REGTYPE, ""),
            ("tar drive path", "C:/private.txt", tarfile.REGTYPE, ""),
            ("tar traversal", "safe/../escape.txt", tarfile.REGTYPE, ""),
        )
        for index, (label, name, member_type, linkname) in enumerate(tar_bites):
            path = tmp / f"bite-{index}.tar"
            with tarfile.open(path, "w") as archive:
                member = tarfile.TarInfo(name)
                member.type = member_type
                member.linkname = linkname
                if member_type == tarfile.REGTYPE:
                    member.size = 1
                    archive.addfile(member, io.BytesIO(b"x"))
                else:
                    archive.addfile(member)
            if not archive_rejected(path):
                failures.append(f"{label} bite was accepted")

        zip_bites = (
            ("ZIP absolute path", "/absolute.txt"),
            ("ZIP drive path", "C:\\private.txt"),
            ("ZIP traversal", "safe/../escape.txt"),
        )
        for index, (label, name) in enumerate(zip_bites):
            path = tmp / f"bite-{index}.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(name, b"x")
            if not archive_rejected(path):
                failures.append(f"{label} bite was accepted")

        zip_link = tmp / "zip-link.zip"
        with zipfile.ZipFile(zip_link, "w") as archive:
            info = zipfile.ZipInfo("safe/link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "target")
        if not archive_rejected(zip_link):
            failures.append("ZIP symlink mode bite was accepted")

        def create_commit(
            repository: Path,
            *,
            author_email: str,
            committer_email: str,
            message: str,
        ) -> None:
            subprocess.run(
                ["git", "init", "-q"],
                cwd=repository,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            (repository / "fixture.txt").write_text("public fixture\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "fixture.txt"],
                cwd=repository,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            env = os.environ.copy()
            env.update(
                {
                    "GIT_AUTHOR_NAME": "Fixture Author",
                    "GIT_AUTHOR_EMAIL": author_email,
                    "GIT_COMMITTER_NAME": "Fixture Committer",
                    "GIT_COMMITTER_EMAIL": committer_email,
                }
            )
            subprocess.run(
                ["git", "commit", "-q", "-m", message],
                cwd=repository,
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        author_repo = tmp / "author-repo"
        author_repo.mkdir()
        create_commit(
            author_repo,
            author_email="author" + "@" + "private.test",
            committer_email=good_mail,
            message="public fixture",
        )
        author_findings, _ = scan_records(history_records(author_repo))
        if "personal email address" not in {item.rule for item in author_findings}:
            failures.append("private Git author email was accepted")

        committer_repo = tmp / "committer-repo"
        committer_repo.mkdir()
        message_id = "agent" + "_" + "message123456"
        create_commit(
            committer_repo,
            author_email=good_mail,
            committer_email="committer" + "@" + "private.test",
            message=f"private metadata {message_id}",
        )
        committer_findings, _ = scan_records(history_records(committer_repo))
        committer_rules = {item.rule for item in committer_findings}
        if "personal email address" not in committer_rules:
            failures.append("private Git committer email was accepted")
        if "raw provider/session/run/judge/agent identifier" not in committer_rules:
            failures.append("private Git commit message was accepted")

    if failures:
        for failure in failures:
            print(f"FAIL  {failure}", file=sys.stderr)
        return 1
    print("PASS  privacy lint self-test accepted clean data and rejected every bite")
    return 0


def report(findings: list[Finding], scanned: int) -> int:
    if not findings:
        print(f"PASS  privacy lint scanned {scanned} public record(s)")
        return 0
    print(
        f"FAIL  privacy lint found {len(findings)} issue(s) in {scanned} record(s):",
        file=sys.stderr,
    )
    for finding in findings:
        location = f":{finding.line}" if finding.line is not None else ""
        print(f"  {finding.source}{location}: {finding.rule}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--working-tree-only",
        action="store_true",
        help="scan current public files but intentionally skip reachable Git history",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        action="append",
        default=[],
        help="scan an archive instead of the repository; may be repeated",
    )
    parser.add_argument("--self-test", action="store_true", help="run positive and bite tests")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.archive:
        records = (
            record
            for archive in args.archive
            for record in archive_records(archive.resolve(strict=True))
        )
        findings, scanned = scan_records(records)
        return report(findings, scanned)

    root = Path(__file__).resolve().parent.parent
    records: list[tuple[str, str, bytes]] = list(working_tree_records(root))
    if not args.working_tree_only and is_git_repository(root):
        records.extend(history_records(root))
    findings, scanned = scan_records(records)
    return report(findings, scanned)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, tarfile.TarError, ValueError) as exc:
        print(f"ERROR  privacy lint could not complete: {exc}", file=sys.stderr)
        raise SystemExit(2)
