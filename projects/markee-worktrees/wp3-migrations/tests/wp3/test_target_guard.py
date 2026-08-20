"""RED→GREEN tests for the WP3 target guard.

The guard is the single failure boundary between any mutation script and the
real Markee PostgreSQL deployment. Each test asserts one rejection rule and
one positive case; the suite is deterministic (no Docker, no network) so it
runs in every CI loop and in the canonical ``pytest`` run.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

import scripts.target_guard as guard
from scripts.target_guard import (
    ALLOWED_DATABASE,
    ALLOWED_HOST,
    ALLOWED_LABEL,
    ALLOWED_PORT,
    ALLOWED_USER,
    BLOCKED_DATABASES,
    BLOCKED_HOSTS,
    BLOCKED_PATTERNS,
    BLOCKED_USERS,
    GuardError,
    TargetSpec,
    WP3_DOCKER_IDENTITY,
    assert_disposable_target,
    assert_wp3_adoption_target,
    check_target,
    disposable_database_url,
)


# --- Happy path -------------------------------------------------------------


def test_disposable_dsn_default_matches_allow_list():
    """The hard-coded default DSN passes the guard without overrides."""
    spec = assert_disposable_target(disposable_database_url())
    assert spec.host == ALLOWED_HOST
    assert spec.port == ALLOWED_PORT
    assert spec.user == ALLOWED_USER
    assert spec.database == ALLOWED_DATABASE
    assert spec.identity_verified is False
    assert spec.identity_fingerprint is None


def test_check_target_passes_for_exact_allow_list():
    """A spec matching every allow-list attribute is accepted."""
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host=ALLOWED_HOST,
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    # Must not raise.
    check_target(spec)


def test_target_spec_from_dsn_strips_leading_slash():
    """``urlparse`` keeps the leading ``/``; the spec strips it for display."""
    spec = TargetSpec.from_dsn(
        f"postgresql://{ALLOWED_USER}:x@{ALLOWED_HOST}:{ALLOWED_PORT}/{ALLOWED_DATABASE}"
    )
    assert spec.database == ALLOWED_DATABASE
    assert spec.port == ALLOWED_PORT


# --- Host / port / user / database rejections -------------------------------


def test_check_target_rejects_wrong_host():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host="10.0.0.5",
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="host"):
        check_target(spec)


def test_check_target_rejects_wrong_port():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host=ALLOWED_HOST,
        port=5432,  # the real Markee port
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="port"):
        check_target(spec)


def test_check_target_rejects_wrong_user():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host=ALLOWED_HOST,
        port=ALLOWED_PORT,
        user="markee",  # real user
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="user"):
        check_target(spec)


def test_check_target_rejects_wrong_database():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host=ALLOWED_HOST,
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database="markee",  # real DB
    )
    with pytest.raises(GuardError, match="database"):
        check_target(spec)


# --- Blocked tokens ---------------------------------------------------------


@pytest.mark.parametrize("token", [t[0] for t in BLOCKED_PATTERNS])
def test_blocked_tokens_force_rejection(token):
    """Every blocked substring, embedded in a DSN, must abort."""
    # Build a DSN that contains the token somewhere on the path or user side.
    if "prod" in token:
        # prod/markee and markee/prod are pathological — force into user.
        dsn = (
            f"postgresql://x:{token}@{ALLOWED_HOST}:{ALLOWED_PORT}/{ALLOWED_DATABASE}"
        )
    else:
        # Container-name style: embed in database segment.
        dsn = (
            f"postgresql://x:x@{ALLOWED_HOST}:5432/{token}"
        )
    with pytest.raises(GuardError):
        assert_disposable_target(dsn)


def test_blocked_host_real_db_alias_is_rejected():
    """The legacy ``db`` hostname (used inside docker-compose) is blocked."""
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host="db",
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="block-list"):
        check_target(spec)


def test_blocked_user_markee_is_rejected():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host=ALLOWED_HOST,
        port=ALLOWED_PORT,
        user="markee",
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="block-list"):
        check_target(spec)


def test_blocked_database_markee_is_rejected():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host=ALLOWED_HOST,
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database="markee",
    )
    with pytest.raises(GuardError, match="block-list"):
        check_target(spec)


def test_real_markee_live_dsn_is_rejected():
    """The exact DSN shape used by the live Markee stack must be rejected.

    ``postgresql+asyncpg://markee:markee_dev@db:5432/markee`` is the
    alembic.ini default; even when it points at loopback, it is rejected
    because of the user / database tuple. We do not attempt DNS on ``db``.
    """
    dsn = "postgresql+asyncpg://markee:markee_dev@127.0.0.1:5432/markee"
    with pytest.raises(GuardError):
        assert_disposable_target(dsn)


def test_empty_dsn_is_rejected():
    with pytest.raises(GuardError, match="empty"):
        assert_disposable_target("")


def test_unsupported_scheme_is_rejected():
    dsn = f"mysql://{ALLOWED_USER}:x@{ALLOWED_HOST}:{ALLOWED_PORT}/{ALLOWED_DATABASE}"
    with pytest.raises(GuardError, match="scheme"):
        assert_disposable_target(dsn)


def test_env_override_is_also_vetted(monkeypatch):
    """``MARKEE_WP3_DB_URL`` is allowed only when it satisfies the guard."""
    monkeypatch.setenv(
        "MARKEE_WP3_DB_URL",
        f"postgresql+asyncpg://markee:x@127.0.0.1:5432/markee",
    )
    with pytest.raises(GuardError):
        assert_disposable_target(disposable_database_url())


# --- Loopback-only enforcement ---------------------------------------------


def test_loopback_only_rejects_public_ip():
    """A target whose textual host is a public IP is rejected."""
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host="203.0.113.5",
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="loopback|host"):
        check_target(spec)


def test_loopback_only_rejects_docker_bridge():
    """A Docker bridge IP (172.16/12) is rejected — the previous version
    accepted it by accident. Mutation tooling must use the host-side
    loopback port-forward ``127.0.0.1:5441`` only.
    """
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host="172.21.0.7",
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    with pytest.raises(GuardError, match="loopback|host"):
        check_target(spec)


def test_loopback_only_rejects_other_loopback_alias():
    """Only ``127.0.0.1`` is allowed; ``localhost``/``::1``/``127.0.0.2`` are not."""
    for host in ("localhost", "::1", "127.0.0.2"):
        spec = TargetSpec(
            scheme="postgresql+asyncpg",
            host=host,
            port=ALLOWED_PORT,
            user=ALLOWED_USER,
            database=ALLOWED_DATABASE,
        )
        with pytest.raises(GuardError, match="loopback|host"):
            check_target(spec)


def test_loopback_only_accepts_exact_loopback():
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host="127.0.0.1",
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    check_target(spec)  # no raise


# --- Constants exposed for the dry-run --------------------------------------


def test_loopback_only_property_is_strict():
    """The ``loopback_only`` property rejects every host that is not exactly
    ``127.0.0.1``, including the Docker bridge and other loopback aliases.
    This is a pure unit assertion of the property — no monkeypatching.
    """
    spec = TargetSpec(
        scheme="postgresql+asyncpg",
        host="127.0.0.1",
        port=ALLOWED_PORT,
        user=ALLOWED_USER,
        database=ALLOWED_DATABASE,
    )
    assert spec.loopback_only is True
    for bad in ("172.21.0.7", "::1", "localhost", "203.0.113.5", "127.0.0.2"):
        spec_bad = TargetSpec(
            scheme="postgresql+asyncpg",
            host=bad,
            port=ALLOWED_PORT,
            user=ALLOWED_USER,
            database=ALLOWED_DATABASE,
        )
        assert spec_bad.loopback_only is False, bad


def test_allowed_label_is_project_scoped():
    """The label used to identify disposable containers is exposed."""
    assert ALLOWED_LABEL.startswith("markee-project=")
    assert "wp3" in ALLOWED_LABEL


def _docker_inspect_payload() -> list[dict]:
    identity = WP3_DOCKER_IDENTITY
    return [{
        "Name": f"/{identity.container}",
        "State": {"Status": "running", "Running": True},
        "Config": {
            "Image": identity.image,
            "Labels": {identity.label_key: identity.label_value},
        },
        "NetworkSettings": {
            "Networks": {identity.network: {"NetworkID": "sanitised"}},
            "Ports": {
                f"{identity.container_port}/tcp": [{
                    "HostIp": identity.host_ip,
                    "HostPort": str(identity.host_port),
                }],
            },
        },
        "Mounts": [{
            "Type": "volume",
            "Name": identity.volume,
            "Destination": identity.mount_destination,
            "Mode": "rw",
            "RW": True,
        }],
    }]


def _install_inspect(monkeypatch, payload):
    calls = []
    monkeypatch.setattr(guard, "_resolve_docker_binary", lambda: Path("/usr/bin/docker"))

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(guard.subprocess, "run", run)
    return calls


def test_wp3_attestation_uses_safe_exact_inspect_command(monkeypatch):
    calls = _install_inspect(monkeypatch, _docker_inspect_payload())
    spec = assert_wp3_adoption_target(disposable_database_url())
    assert spec.identity_verified is True
    assert spec.identity_fingerprint.startswith("sha256:")
    assert len(spec.identity_fingerprint) == len("sha256:") + 64
    assert calls == [(
        ["/usr/bin/docker", "inspect", "--type", "container", WP3_DOCKER_IDENTITY.container],
        {"capture_output": True, "text": True,
         "timeout": guard.DOCKER_INSPECT_TIMEOUT_SECONDS, "check": False},
    )]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p[0].__setitem__("Name", "/lookalike"),
        lambda p: p[0]["State"].__setitem__("Running", False),
        lambda p: p[0]["State"].__setitem__("Status", "exited"),
        lambda p: p[0]["Config"].__setitem__("Image", "postgres:16"),
        lambda p: p[0]["Config"]["Labels"].__setitem__("markee-project", "markee"),
        lambda p: p[0]["NetworkSettings"].__setitem__("Networks", {"wrong": {}}),
        lambda p: p[0]["NetworkSettings"]["Networks"].__setitem__("unexpected", {}),
        lambda p: p[0]["NetworkSettings"]["Ports"]["5432/tcp"][0].__setitem__("HostIp", "0.0.0.0"),
        lambda p: p[0]["NetworkSettings"]["Ports"]["5432/tcp"][0].__setitem__("HostPort", "5432"),
        lambda p: p[0]["NetworkSettings"]["Ports"]["5432/tcp"].append({"HostIp": "127.0.0.1", "HostPort": "9999"}),
        lambda p: p[0]["NetworkSettings"]["Ports"].__setitem__("15432/tcp", []),
        lambda p: p[0]["Mounts"][0].__setitem__("Name", "real-data"),
        lambda p: p[0]["Mounts"][0].__setitem__("Destination", "/tmp/data"),
        lambda p: p[0]["Mounts"][0].__setitem__("Type", "bind"),
        lambda p: p[0]["Mounts"][0].__setitem__("Mode", "ro"),
        lambda p: p[0]["Mounts"][0].__setitem__("Mode", ""),
        lambda p: p[0]["Mounts"][0].__setitem__("RW", False),
        lambda p: p[0]["Mounts"].append(deepcopy(p[0]["Mounts"][0])),
    ],
)
def test_wp3_attestation_rejects_every_identity_mismatch(monkeypatch, mutation):
    payload = _docker_inspect_payload()
    mutation(payload)
    _install_inspect(monkeypatch, payload)
    with pytest.raises(GuardError, match="Docker identity rejected"):
        assert_wp3_adoption_target(disposable_database_url())


@pytest.mark.parametrize("payload", [[], [{}, {}], {}, "not-a-list", [{"Name": "/x"}]])
def test_wp3_attestation_rejects_absent_multiple_or_malformed_inspect(monkeypatch, payload):
    _install_inspect(monkeypatch, payload)
    with pytest.raises(GuardError):
        assert_wp3_adoption_target(disposable_database_url())


def test_wp3_attestation_rejects_timeout_without_leaking_output(monkeypatch):
    monkeypatch.setattr(guard, "_resolve_docker_binary", lambda: Path("/usr/bin/docker"))

    def timeout(*_args, **_kwargs):
        raise guard.subprocess.TimeoutExpired("secret-bearing-command", 5, output="secret")

    monkeypatch.setattr(guard.subprocess, "run", timeout)
    with pytest.raises(GuardError) as raised:
        assert_wp3_adoption_target(disposable_database_url())
    assert "secret" not in str(raised.value)
    assert disposable_database_url() not in str(raised.value)


def test_wp3_attestation_rejects_nonzero_and_invalid_json_without_leaking_output(monkeypatch):
    monkeypatch.setattr(guard, "_resolve_docker_binary", lambda: Path("/usr/bin/docker"))
    for completed in (
        SimpleNamespace(returncode=1, stdout="dsn-secret", stderr="daemon-secret"),
        SimpleNamespace(returncode=0, stdout="not-json-secret", stderr=""),
    ):
        monkeypatch.setattr(guard.subprocess, "run", lambda *_a, **_k: completed)
        with pytest.raises(GuardError) as raised:
            assert_wp3_adoption_target(disposable_database_url())
        assert "secret" not in str(raised.value)


def test_docker_binary_must_resolve_to_root_owned_system_executable(monkeypatch, tmp_path):
    candidate = tmp_path / "docker"
    candidate.write_text("fake")
    candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(guard.shutil, "which", lambda _name: str(candidate))
    with pytest.raises(GuardError, match="Docker executable rejected"):
        guard._resolve_docker_binary()


def test_docker_binary_accepts_resolved_root_owned_system_executable(monkeypatch):
    resolved = Path("/usr/bin/docker")
    metadata = SimpleNamespace(
        st_mode=stat.S_IFREG | stat.S_IRUSR | stat.S_IXUSR,
        st_uid=0,
    )
    monkeypatch.setattr(guard.shutil, "which", lambda _name: "/usr/local/bin/docker-link")
    monkeypatch.setattr(Path, "resolve", lambda self, strict=False: resolved)
    monkeypatch.setattr(Path, "stat", lambda self: metadata)

    assert guard._resolve_docker_binary() == resolved


def test_matching_dsn_cannot_attest_a_wrong_port_mapping(monkeypatch):
    payload = _docker_inspect_payload()
    payload[0]["NetworkSettings"]["Ports"]["5432/tcp"] = [
        {"HostIp": "127.0.0.1", "HostPort": "6543"}
    ]
    _install_inspect(monkeypatch, payload)
    with pytest.raises(GuardError):
        assert_wp3_adoption_target(disposable_database_url())
