"""Fail-closed target guard for Markee WP3 disposable database operations.

The WP3 contract forbids any mutation of the live Markee PostgreSQL database
(``markee_db_1`` / docker-compose project ``markee``) and any reuse of the
real connection string. Every script that may run Alembic, restore a dump or
rebuild the disposable database must call :func:`assert_disposable_target`
first; the guard verifies host, port, database name, user and Alembic
project label against a strict allow-list and aborts on any mismatch.

The guard is intentionally side-effect free: it never opens a connection, it
only inspects the environment. This keeps it usable in unit tests and in the
deterministic ``RED`` tests that prove the rejection logic before any real
container exists.
"""
from __future__ import annotations

import os
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import shutil
import stat
import subprocess
from typing import Any, Mapping
from urllib.parse import urlparse


# Disposable container label we stamp on the PostgreSQL container we create
# for migration dry-runs. Any container without this label is rejected.
ALLOWED_LABEL = "markee-project=wp3-adoption-disposable"

# The full set of attributes that uniquely identify the disposable target.
# Any match outside this tuple fails closed.
ALLOWED_HOST = "127.0.0.1"
ALLOWED_PORT = 5441
ALLOWED_USER = "markee_wp3"
ALLOWED_DATABASE = "markee_wp3_disposable"

DOCKER_INSPECT_TIMEOUT_SECONDS = 5
APPROVED_DOCKER_DIRECTORIES = (Path("/usr/bin"), Path("/usr/local/bin"))


@dataclass(frozen=True)
class DockerIdentity:
    """Immutable Docker facts required for the mutable WP3 adoption target."""

    container: str
    label_key: str
    label_value: str
    image: str
    network: str
    volume: str
    mount_destination: str
    container_port: int
    host_ip: str
    host_port: int


WP3_DOCKER_IDENTITY = DockerIdentity(
    container="markee-wp3-adoption-db-1",
    label_key="markee-project",
    label_value="wp3-adoption-disposable",
    image="postgres:16-alpine",
    network="markee-wp3-adoption_net",
    volume="markee-wp3-adoption_pgdata",
    mount_destination="/var/lib/postgresql/data",
    container_port=5432,
    host_ip=ALLOWED_HOST,
    host_port=ALLOWED_PORT,
)

# Block-list: anything that smells like the real Markee deployment is rejected
# even if it sneaks past the allow-list. The block-list is deliberately
# over-broad — false positives are safe here. Each entry is checked as a
# whole substring of the URL's *host*, *user* or *database* (not the path
# string we compose), so ``markee_wp3`` cannot accidentally trigger
# ``markee``.
BLOCKED_PATTERNS: tuple[tuple[str, str, str], ...] = (
    # (substring, where, why)
    ("markee_db_1", "any", "real Markee container name"),
    ("markee-db-1", "any", "real Markee container name"),
    ("markee/prod", "any", "prod env reference"),
    ("prod/markee", "any", "prod env reference"),
)
# Hostnames / usernames / database names that are obviously real-DB.
BLOCKED_HOSTS: frozenset[str] = frozenset({"db", "markee_db", "markee-db"})
BLOCKED_USERS: frozenset[str] = frozenset({"markee"})
BLOCKED_DATABASES: frozenset[str] = frozenset({"markee"})


@dataclass(frozen=True)
class TargetSpec:
    """Normalised identity of a database target (parseable from a DSN)."""

    scheme: str
    host: str
    port: int
    user: str
    database: str
    identity_verified: bool = False
    identity_fingerprint: str | None = None

    @classmethod
    def from_dsn(cls, dsn: str) -> "TargetSpec":
        """Parse ``dsn`` and return a normalised :class:`TargetSpec`.

        Accepts both ``postgresql+asyncpg://`` URLs and plain
        ``postgresql://`` URLs. The scheme is preserved for caller-side
        diagnostics but is not part of the allow-list check.
        """
        if not dsn or not isinstance(dsn, str):
            raise GuardError("empty or non-string DATABASE_URL")
        parsed = urlparse(dsn)
        if parsed.scheme not in ("postgresql", "postgresql+asyncpg", "postgres"):
            raise GuardError(f"unsupported scheme: {parsed.scheme!r}")
        if not parsed.hostname or not parsed.username or not parsed.path:
            raise GuardError(
                "DATABASE_URL must include host, user and database "
                f"(got host={parsed.hostname!r}, user={parsed.username!r}, "
                f"path={parsed.path!r})"
            )
        db = parsed.path.lstrip("/")
        if not db:
            raise GuardError("DATABASE_URL database name is empty")
        return cls(
            scheme=parsed.scheme,
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            database=db,
        )

    @property
    def loopback_only(self) -> bool:
        """True when the host is the loopback address ``127.0.0.1`` exactly.

        Mutation tooling must connect through ``127.0.0.1:5441`` (the Docker
        port-forward on the host) so that the disposable database never
        receives a connection from a non-allow-listed interface. Any other
        resolution — including Docker bridge IPs (172.16/12), other loopback
        aliases or public addresses — is rejected: bridge IPs are accepted
        only by accident, not by design, and we want a clean error when
        something tries to short-circuit the allow-list via container-internal
        DNS.
        """
        return self.host == "127.0.0.1"


class GuardError(RuntimeError):
    """Raised when a target identity fails the disposable allow-list."""


def check_target(spec: TargetSpec) -> None:
    """Fail closed if ``spec`` does not match the disposable allow-list.

    Order matters: explicit block-list first (cheapest reject for the obvious
    real-DB case), then exact tuple match. The ``loopback_only`` check is
    last because we still want a clean error message when the URL is wrong.
    """
    haystack = (
        f"{spec.scheme}://{spec.user}@{spec.host}:{spec.port}/{spec.database}"
    ).lower()
    for token, where, why in BLOCKED_PATTERNS:
        if token.lower() in haystack:
            raise GuardError(
                f"refusing target that matches blocked token {token!r} ({why}): "
                f"{spec.host}:{spec.port}/{spec.database} as {spec.user}"
            )

    if spec.host in BLOCKED_HOSTS:
        raise GuardError(
            f"host {spec.host!r} is on the real-Markee block-list"
        )
    if spec.user in BLOCKED_USERS:
        raise GuardError(
            f"user {spec.user!r} is on the real-Markee block-list"
        )
    if spec.database in BLOCKED_DATABASES:
        raise GuardError(
            f"database {spec.database!r} is on the real-Markee block-list"
        )

    if spec.host != ALLOWED_HOST:
        raise GuardError(
            f"host {spec.host!r} != allowed {ALLOWED_HOST!r}"
        )
    if spec.port != ALLOWED_PORT:
        raise GuardError(
            f"port {spec.port} != allowed {ALLOWED_PORT}"
        )
    if spec.user != ALLOWED_USER:
        raise GuardError(
            f"user {spec.user!r} != allowed {ALLOWED_USER!r}"
        )
    if spec.database != ALLOWED_DATABASE:
        raise GuardError(
            f"database {spec.database!r} != allowed {ALLOWED_DATABASE!r}"
        )

    if not spec.loopback_only:
        raise GuardError(
            f"host {spec.host!r} resolves outside loopback/Docker bridge"
        )


def assert_disposable_target(database_url: str) -> TargetSpec:
    """Parse ``database_url`` and reject anything that is not the disposable.

    Returns the parsed :class:`TargetSpec` on success so the caller can log it.
    Raises :class:`GuardError` on any mismatch.
    """
    spec = TargetSpec.from_dsn(database_url)
    check_target(spec)
    return spec


def _resolve_docker_binary() -> Path:
    """Resolve Docker to a root-owned executable in an approved system tree."""
    candidate = shutil.which("docker")
    if not candidate:
        raise GuardError("Docker executable rejected")
    try:
        resolved = Path(candidate).resolve(strict=True)
        metadata = resolved.stat()
    except (OSError, RuntimeError):
        raise GuardError("Docker executable rejected") from None
    approved = any(
        resolved.parent == directory or resolved.is_relative_to(directory)
        for directory in APPROVED_DOCKER_DIRECTORIES
    )
    executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    if (
        not approved
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or not metadata.st_mode & executable_bits
    ):
        raise GuardError("Docker executable rejected")
    return resolved


def _identity_facts(payload: Any, expected: DockerIdentity) -> Mapping[str, Any]:
    """Validate an inspect payload and return only non-secret identity facts."""
    try:
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError
        item = payload[0]
        if not isinstance(item, dict):
            raise ValueError
        state = item["State"]
        config = item["Config"]
        network_settings = item["NetworkSettings"]
        labels = config["Labels"]
        networks = network_settings["Networks"]
        ports = network_settings["Ports"]
        mounts = item["Mounts"]
        port_key = f"{expected.container_port}/tcp"
        expected_binding = [{
            "HostIp": expected.host_ip,
            "HostPort": str(expected.host_port),
        }]
        if (
            item["Name"] != f"/{expected.container}"
            or state.get("Running") is not True
            or state.get("Status") != "running"
            or config["Image"] != expected.image
            or not isinstance(labels, dict)
            or labels.get(expected.label_key) != expected.label_value
            or not isinstance(networks, dict)
            or set(networks) != {expected.network}
            or not isinstance(ports, dict)
            or ports != {port_key: expected_binding}
            or not isinstance(mounts, list)
            or len(mounts) != 1
        ):
            raise ValueError
        mount = mounts[0]
        if (
            not isinstance(mount, dict)
            or mount.get("Type") != "volume"
            or mount.get("Name") != expected.volume
            or mount.get("Destination") != expected.mount_destination
            or mount.get("Mode") != "rw"
            or mount.get("RW") is not True
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise GuardError("Docker identity rejected") from None
    return asdict(expected)


def assert_wp3_adoption_target(database_url: str) -> TargetSpec:
    """Attest the exact disposable Docker identity after textual DSN checks."""
    spec = assert_disposable_target(database_url)
    docker = _resolve_docker_binary()
    try:
        completed = subprocess.run(
            [str(docker), "inspect", "--type", "container", WP3_DOCKER_IDENTITY.container],
            capture_output=True,
            text=True,
            timeout=DOCKER_INSPECT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        raise GuardError("Docker inspection failed") from None
    if completed.returncode != 0:
        raise GuardError("Docker inspection failed")
    try:
        payload = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        raise GuardError("Docker inspection failed") from None
    facts = _identity_facts(payload, WP3_DOCKER_IDENTITY)
    canonical = json.dumps(facts, sort_keys=True, separators=(",", ":")).encode()
    fingerprint = "sha256:" + hashlib.sha256(canonical).hexdigest()
    return replace(spec, identity_verified=True, identity_fingerprint=fingerprint)


def disposable_database_url() -> str:
    """Return the canonical disposable DSN, honouring ``MARKEE_WP3_DB_URL``.

    The environment override exists for the test harness; production use of
    this module always passes through :func:`assert_disposable_target`, so the
    override is also vetted by the guard.
    """
    return os.environ.get(
        "MARKEE_WP3_DB_URL",
        f"postgresql+asyncpg://{ALLOWED_USER}:markee_wp3_local_only"
        f"@{ALLOWED_HOST}:{ALLOWED_PORT}/{ALLOWED_DATABASE}",
    )


__all__ = [
    "ALLOWED_HOST",
    "ALLOWED_PORT",
    "ALLOWED_USER",
    "ALLOWED_DATABASE",
    "ALLOWED_LABEL",
    "APPROVED_DOCKER_DIRECTORIES",
    "DOCKER_INSPECT_TIMEOUT_SECONDS",
    "DockerIdentity",
    "WP3_DOCKER_IDENTITY",
    "GuardError",
    "TargetSpec",
    "assert_disposable_target",
    "assert_wp3_adoption_target",
    "check_target",
    "disposable_database_url",
]
