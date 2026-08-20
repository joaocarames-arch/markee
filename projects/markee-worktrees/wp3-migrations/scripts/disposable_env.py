"""Fixed-identity lifecycle CLI for the disposable WP3 PostgreSQL 16 target.

The mutation scripts import :func:`load_disposable_url`. The CLI creates and
removes only its statically named Docker resources and never emits credentials
or DSNs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence

ENV_PATH = Path(__file__).resolve().parent / "disposable.env"
IDENTITY = {
    "container": "markee-wp3-adoption-db-1",
    "network": "markee-wp3-adoption_net",
    "volume": "markee-wp3-adoption_pgdata",
    "port": 5441,
    "image": "postgres:16-alpine",
}
_LABEL = "markee-project=wp3-adoption-disposable"
_HOST = "127.0.0.1"
_CONTAINER_PORT = 5432
_MOUNT = "/var/lib/postgresql/data"


class LifecycleError(RuntimeError):
    """Raised when the exact disposable lifecycle cannot proceed safely."""


def _load_config() -> dict[str, str]:
    """Load the local disposable configuration without exposing its values."""
    if not ENV_PATH.is_file():
        raise RuntimeError(
            f"disposable.env not found at {ENV_PATH}; WP3 cannot run without it"
        )
    cfg: dict[str, str] = {}
    allowed_keys = {
        "WP3_DATABASE_URL",
        "WP3_DATABASE_URL_SYNC",
        "WP3_CONTAINER",
        "WP3_PORT",
        "WP3_HOST",
        "WP3_USER",
        "WP3_DB",
        "WP3_PASSWORD",
    }
    for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeError("malformed line in disposable.env")
        key, _, value = line.partition("=")
        key = key.strip()
        if key not in allowed_keys:
            raise RuntimeError(f"disallowed key in disposable.env: {key!r}")
        cfg[key] = value.strip()
    required = {
        "WP3_DATABASE_URL",
        "WP3_DATABASE_URL_SYNC",
        "WP3_USER",
        "WP3_DB",
        "WP3_PASSWORD",
    }
    missing = sorted(required - cfg.keys())
    if missing:
        raise RuntimeError("required disposable.env key missing")
    # Lifecycle identities are code-fixed and deliberately do not trust the
    # historical WP3_CONTAINER value in this credential file. DSN routing is
    # still required to use the one loopback port owned by the fixed target.
    fixed = {"WP3_PORT": str(IDENTITY["port"]), "WP3_HOST": _HOST}
    for key, expected in fixed.items():
        if cfg.get(key) != expected:
            raise LifecycleError(f"fixed disposable identity mismatch: {key}")
    return cfg


def load_disposable_url(*, sync: bool = False) -> str:
    """Return the configured disposable DSN for guarded callers."""
    cfg = _load_config()
    return cfg["WP3_DATABASE_URL_SYNC" if sync else "WP3_DATABASE_URL"]


def _docker_binary() -> str:
    candidate = shutil.which("docker")
    if not candidate:
        raise LifecycleError("Docker executable unavailable")
    resolved = Path(candidate).resolve(strict=True)
    if resolved.parent not in {Path("/usr/bin"), Path("/usr/local/bin")}:
        raise LifecycleError("Docker executable outside approved system path")
    return str(resolved)


def _run(argv: list[str], *, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode and not allow_failure:
        raise LifecycleError("exact Docker lifecycle command failed")
    return completed


def _resource_exists(kind: str, name: str) -> bool:
    result = _run([_docker_binary(), kind, "inspect", name], allow_failure=True)
    return result.returncode == 0


def _port_is_free() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((_HOST, int(IDENTITY["port"])))
        except OSError:
            return False
    return True


def _down() -> None:
    docker = _docker_binary()
    container = str(IDENTITY["container"])
    network = str(IDENTITY["network"])
    volume = str(IDENTITY["volume"])
    if _resource_exists("container", container):
        _run([docker, "container", "stop", "--time", "10", container])
        _run([docker, "container", "rm", container])
    if _resource_exists("network", network):
        _run([docker, "network", "rm", network])
    if _resource_exists("volume", volume):
        _run([docker, "volume", "rm", volume])
    if any(
        _resource_exists(kind, name)
        for kind, name in (
            ("container", container),
            ("network", network),
            ("volume", volume),
        )
    ) or not _port_is_free():
        raise LifecycleError("exact disposable teardown verification failed")
    print("state=down resources=0/0/0 port_free=true")


def _inspect_identity() -> dict:
    result = _run([_docker_binary(), "inspect", str(IDENTITY["container"])])
    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError
        return payload[0]
    except (json.JSONDecodeError, TypeError, ValueError):
        raise LifecycleError("disposable Docker identity inspection failed") from None


def _identity_is_exact(item: dict) -> bool:
    try:
        return (
            item["Name"] == f"/{IDENTITY['container']}"
            and item["Config"]["Image"] == IDENTITY["image"]
            and item["Config"]["Labels"].get("markee-project")
            == "wp3-adoption-disposable"
            and set(item["NetworkSettings"]["Networks"])
            == {IDENTITY["network"]}
            and item["NetworkSettings"]["Ports"] == {
                "5432/tcp": [{"HostIp": _HOST, "HostPort": str(IDENTITY["port"])}]
            }
            and len(item["Mounts"]) == 1
            and item["Mounts"][0]["Type"] == "volume"
            and item["Mounts"][0]["Name"] == IDENTITY["volume"]
            and item["Mounts"][0]["Destination"] == _MOUNT
            # The strict adoption guard requires Mode == "rw"; a bare
            # ``-v name:/path`` yields Mode == "" while RW stays True, so the
            # self-check must verify Mode too or ``up`` would report success
            # for an identity the guard later rejects.
            and item["Mounts"][0].get("Mode") == "rw"
            and item["Mounts"][0]["RW"] is True
        )
    except (KeyError, TypeError):
        return False


def _up() -> None:
    cfg = _load_config()
    docker = _docker_binary()
    identities = (
        ("container", str(IDENTITY["container"])),
        ("network", str(IDENTITY["network"])),
        ("volume", str(IDENTITY["volume"])),
    )
    if any(_resource_exists(kind, name) for kind, name in identities):
        raise LifecycleError("disposable resource collision; run exact down first")
    if not _port_is_free():
        raise LifecycleError("disposable port collision")
    if not _resource_exists("image", str(IDENTITY["image"])):
        raise LifecycleError("local PostgreSQL 16 image unavailable; pulling is forbidden")

    _run([docker, "network", "create", "--label", _LABEL, str(IDENTITY["network"])])
    try:
        _run([docker, "volume", "create", "--label", _LABEL, str(IDENTITY["volume"])])
        _run([
            docker,
            "run",
            "--detach",
            "--pull",
            "never",
            "--name",
            str(IDENTITY["container"]),
            "--label",
            _LABEL,
            "--network",
            str(IDENTITY["network"]),
            "--publish",
            f"{_HOST}:{IDENTITY['port']}:{_CONTAINER_PORT}",
            "--volume",
            f"{IDENTITY['volume']}:{_MOUNT}:rw",
            "--env",
            f"POSTGRES_USER={cfg['WP3_USER']}",
            "--env",
            f"POSTGRES_PASSWORD={cfg['WP3_PASSWORD']}",
            "--env",
            f"POSTGRES_DB={cfg['WP3_DB']}",
            "--health-cmd",
            f"pg_isready -U {cfg['WP3_USER']} -d {cfg['WP3_DB']}",
            "--health-interval",
            "1s",
            "--health-timeout",
            "3s",
            "--health-retries",
            "30",
            str(IDENTITY["image"]),
        ])
        deadline = time.monotonic() + 45
        item: dict = {}
        while time.monotonic() < deadline:
            item = _inspect_identity()
            health = ((item.get("State") or {}).get("Health") or {}).get("Status")
            if health == "healthy":
                break
            if (item.get("State") or {}).get("Status") == "exited":
                raise LifecycleError("disposable PostgreSQL exited before healthy")
            time.sleep(0.5)
        else:
            raise LifecycleError("disposable PostgreSQL health timeout")
        if not _identity_is_exact(item):
            raise LifecycleError("created disposable identity differs from fixed contract")
        count = _run([
            docker,
            "exec",
            str(IDENTITY["container"]),
            "psql",
            "-XAt",
            "-U",
            cfg["WP3_USER"],
            "-d",
            cfg["WP3_DB"],
            "-c",
            "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND c.relkind IN ('r','p');",
        ])
        if count.stdout.strip() != "0":
            raise LifecycleError("new disposable PostgreSQL database is not empty")
    except Exception:
        _down()
        raise
    print("state=up healthy=true empty=true image=postgres:16-alpine")


def _status() -> None:
    state = {
        kind: _resource_exists(kind, name)
        for kind, name in (
            ("container", str(IDENTITY["container"])),
            ("network", str(IDENTITY["network"])),
            ("volume", str(IDENTITY["volume"])),
        )
    }
    state.update({"port_free": _port_is_free(), **IDENTITY})
    print(json.dumps(state, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the fixed WP3 PostgreSQL 16 disposable target")
    parser.add_argument("command", choices=("status", "down", "up"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one fixed-identity lifecycle command."""
    args = _parser().parse_args(argv)
    if args.command == "status":
        _status()
    elif args.command == "down":
        _down()
    else:
        _up()
    return 0


__all__ = ["ENV_PATH", "IDENTITY", "LifecycleError", "load_disposable_url", "main"]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LifecycleError as exc:
        print(f"error={exc}", file=sys.stderr)
        raise SystemExit(1) from None
