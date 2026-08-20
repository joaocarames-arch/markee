"""Focused tests for the fixed-identity disposable PostgreSQL 16 CLI."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.disposable_env as disposable
import scripts.target_guard as guard


def test_shape_helpers_match_guard_strictly():
    """RED regression: the helper's fixed identity must equal the guard's.

    Both modules declare the same container, image, label, network, volume,
    mount destination, container port, host IP and host port. If anyone
    drifts the helper away from the guard (or vice-versa) the real
    ``assert_wp3_adoption_target`` will fail at apply time — exactly the
    blocker documented in the WP3 report. This test pins both sides.
    """
    helper = disposable.IDENTITY
    expected = guard.WP3_DOCKER_IDENTITY
    assert helper["container"] == expected.container
    assert helper["image"] == expected.image
    assert f"{expected.label_key}={expected.label_value}" == (
        "markee-project=wp3-adoption-disposable"
    )
    assert helper["network"] == expected.network
    assert helper["volume"] == expected.volume
    assert helper["port"] == expected.host_port
    # Container-side values the helper does not expose directly but
    # _identity_is_exact enforces at run time.
    assert 5432 == expected.container_port
    assert "/var/lib/postgresql/data" == expected.mount_destination
    assert "127.0.0.1" == expected.host_ip


def _build_inspect_payload(*, extra_networks=(), extra_mounts=()):
    identity = guard.WP3_DOCKER_IDENTITY
    networks = {identity.network: {"NetworkID": "sanitised"}}
    for n in extra_networks:
        networks[n] = {"NetworkID": "extra"}
    mounts = [{
        "Type": "volume",
        "Name": identity.volume,
        "Destination": identity.mount_destination,
        "Mode": "rw",
        "RW": True,
    }]
    for m in extra_mounts:
        mounts.append(m)
    return [{
        "Name": f"/{identity.container}",
        "State": {"Status": "running", "Running": True},
        "Config": {
            "Image": identity.image,
            "Labels": {identity.label_key: identity.label_value},
        },
        "NetworkSettings": {
            "Networks": networks,
            "Ports": {
                f"{identity.container_port}/tcp": [{
                    "HostIp": identity.host_ip,
                    "HostPort": str(identity.host_port),
                }],
            },
        },
        "Mounts": mounts,
    }]


def _patch_inspect(monkeypatch, payload):
    monkeypatch.setattr(guard, "_resolve_docker_binary", lambda: Path("/usr/bin/docker"))

    def run(argv, **_kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(guard.subprocess, "run", run)


def test_helper_identity_passes_real_adoption_guard(monkeypatch):
    """GREEN: the exact inspect shape produced by a fresh ``up`` is accepted."""
    _patch_inspect(monkeypatch, _build_inspect_payload())
    spec = guard.assert_wp3_adoption_target(guard.disposable_database_url())
    assert spec.identity_verified is True
    assert spec.identity_fingerprint.startswith("sha256:")
    assert len(spec.identity_fingerprint) == len("sha256:") + 64


def test_helper_identity_rejected_when_extra_bridge_network_attached(monkeypatch):
    """RED: a near-miss (Docker default ``bridge`` is auto-attached unless
    ``--network`` is the *only* one) is rejected by the strict guard.
    The fix in this WP3 worktree is to never let the helper create a
    container with the default bridge; this test pins the contract.
    """
    payload = _build_inspect_payload(extra_networks=("bridge",))
    _patch_inspect(monkeypatch, payload)
    with pytest.raises(guard.GuardError, match="Docker identity rejected"):
        guard.assert_wp3_adoption_target(guard.disposable_database_url())


def test_helper_identity_rejected_when_second_volume_is_mounted(monkeypatch):
    """RED: a near-miss where a second bind mount is attached must abort."""
    extra = {
        "Type": "bind",
        "Name": "extra",
        "Destination": "/extra",
        "Mode": "rw",
        "RW": True,
    }
    payload = _build_inspect_payload(extra_mounts=(extra,))
    _patch_inspect(monkeypatch, payload)
    with pytest.raises(guard.GuardError, match="Docker identity rejected"):
        guard.assert_wp3_adoption_target(guard.disposable_database_url())


def test_helper_identity_rejected_when_label_value_wrong(monkeypatch):
    """RED: a near-miss where a different project label is stamped fails."""
    payload = _build_inspect_payload()
    payload[0]["Config"]["Labels"]["markee-project"] = "markee"
    _patch_inspect(monkeypatch, payload)
    with pytest.raises(guard.GuardError, match="Docker identity rejected"):
        guard.assert_wp3_adoption_target(guard.disposable_database_url())


def test_identity_is_exact_requires_rw_mount_mode():
    """RED->GREEN: the helper self-check must reject a bare-volume mount.

    A ``-v name:/path`` created without an explicit ``:rw`` mode yields
    ``Mode == ""`` while ``RW`` stays ``True``. The strict adoption guard
    requires ``Mode == "rw"`` (target_guard._identity_facts), so an ``up``
    that self-verifies only ``RW`` would report success for an identity the
    guard rejects at apply time — the exact stale WP3 blocker. This pins the
    helper self-check to the guard's Mode contract.
    """
    item = _build_inspect_payload()[0]
    assert disposable._identity_is_exact(item) is True  # sanity: rw is accepted
    item["Mounts"][0]["Mode"] = ""
    assert disposable._identity_is_exact(item) is False
    item["Mounts"][0]["Mode"] = "ro"
    assert disposable._identity_is_exact(item) is False


def test_helper_identity_rejected_when_mount_mode_not_rw(monkeypatch):
    """RED: the real adoption guard rejects a bare-volume (Mode "") identity.

    This is the precise historical mismatch: the helper produced the volume
    without ``:rw`` so Docker reported ``Mode == ""``; the guard demands
    ``Mode == "rw"``. Pinning it in the helper suite keeps helper and guard
    in lock-step.
    """
    payload = _build_inspect_payload()
    payload[0]["Mounts"][0]["Mode"] = ""
    _patch_inspect(monkeypatch, payload)
    with pytest.raises(guard.GuardError, match="Docker identity rejected"):
        guard.assert_wp3_adoption_target(guard.disposable_database_url())


EXPECTED = {
    "container": "markee-wp3-adoption-db-1",
    "network": "markee-wp3-adoption_net",
    "volume": "markee-wp3-adoption_pgdata",
    "port": 5441,
    "image": "postgres:16-alpine",
}


def _completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_parser_exposes_help_status_down_and_up(capsys):
    with pytest.raises(SystemExit) as raised:
        disposable.main(["--help"])
    assert raised.value.code == 0
    help_text = capsys.readouterr().out
    for command in ("status", "down", "up"):
        assert command in help_text


def test_unknown_command_is_nonzero(capsys):
    with pytest.raises(SystemExit) as raised:
        disposable.main(["destroy-everything"])
    assert raised.value.code != 0
    assert "destroy-everything" not in capsys.readouterr().out


def test_fixed_disposable_identity_matches_adoption_guard():
    assert disposable.IDENTITY == EXPECTED
    assert disposable.IDENTITY["container"] != "markee-db-1"
    assert disposable.IDENTITY["network"] != "markee_default"
    assert disposable.IDENTITY["volume"] != "markee_pgdata"


def test_down_removes_only_exact_container_network_and_volume(monkeypatch, capsys):
    calls: list[list[str]] = []
    present = {"container": True, "network": True, "volume": True}

    def run(argv, **kwargs):
        calls.append(list(argv))
        if len(argv) >= 3 and argv[2] == "inspect" and argv[1] in present:
            return _completed(stdout="[]") if present[argv[1]] else _completed(returncode=1)
        if argv[1:3] == ["container", "rm"]:
            present["container"] = False
        elif argv[1:3] == ["network", "rm"]:
            present["network"] = False
        elif argv[1:3] == ["volume", "rm"]:
            present["volume"] = False
        return _completed()

    monkeypatch.setattr(disposable, "_docker_binary", lambda: "/usr/bin/docker")
    monkeypatch.setattr(disposable.subprocess, "run", run)
    assert disposable.main(["down"]) == 0
    assert calls[:7] == [
        ["/usr/bin/docker", "container", "inspect", EXPECTED["container"]],
        ["/usr/bin/docker", "container", "stop", "--time", "10", EXPECTED["container"]],
        ["/usr/bin/docker", "container", "rm", EXPECTED["container"]],
        ["/usr/bin/docker", "network", "inspect", EXPECTED["network"]],
        ["/usr/bin/docker", "network", "rm", EXPECTED["network"]],
        ["/usr/bin/docker", "volume", "inspect", EXPECTED["volume"]],
        ["/usr/bin/docker", "volume", "rm", EXPECTED["volume"]],
    ]
    assert calls[7:] == [
        ["/usr/bin/docker", "container", "inspect", EXPECTED["container"]],
        ["/usr/bin/docker", "network", "inspect", EXPECTED["network"]],
        ["/usr/bin/docker", "volume", "inspect", EXPECTED["volume"]],
    ]
    assert "password" not in capsys.readouterr().out.lower()


def test_up_uses_local_pg16_fixed_resources_and_waits_healthy(monkeypatch, capsys):
    calls: list[list[str]] = []
    inspect_payload = [{
        "Name": f"/{EXPECTED['container']}",
        "Config": {
            "Image": EXPECTED["image"],
            "Labels": {"markee-project": "wp3-adoption-disposable"},
        },
        "State": {"Status": "running", "Running": True, "Health": {"Status": "healthy"}},
        "NetworkSettings": {
            "Networks": {EXPECTED["network"]: {}},
            "Ports": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "5441"}]},
        },
        "Mounts": [{"Type": "volume", "Name": EXPECTED["volume"], "Destination": "/var/lib/postgresql/data", "Mode": "rw", "RW": True}],
    }]

    def run(argv, **kwargs):
        calls.append(list(argv))
        if argv[1:3] in (["container", "inspect"], ["network", "inspect"], ["volume", "inspect"]):
            return _completed(returncode=1)
        if argv[1:3] == ["image", "inspect"]:
            return _completed(stdout="[]")
        if argv[1] == "inspect":
            return _completed(stdout=json.dumps(inspect_payload))
        if argv[1:3] == ["exec", EXPECTED["container"]]:
            return _completed(stdout="0\n")
        return _completed()

    monkeypatch.setattr(disposable, "_docker_binary", lambda: "/usr/bin/docker")
    monkeypatch.setattr(disposable.subprocess, "run", run)
    monkeypatch.setattr(disposable.time, "sleep", lambda _seconds: None)
    assert disposable.main(["up"]) == 0
    create = next(call for call in calls if len(call) > 1 and call[1] == "run")
    assert "--pull" in create and create[create.index("--pull") + 1] == "never"
    assert EXPECTED["image"] == create[-1]
    assert EXPECTED["container"] in create
    assert EXPECTED["network"] in create
    assert EXPECTED["volume"] in " ".join(create)
    volume_arg = create[create.index("--volume") + 1]
    assert volume_arg == f"{EXPECTED['volume']}:/var/lib/postgresql/data:rw"
    assert "127.0.0.1:5441:5432" in create
    assert not any("postgresql://" in part for call in calls for part in call)
    output = capsys.readouterr().out.lower()
    assert "password" not in output
    assert "postgresql://" not in output


def test_up_refuses_any_collision_before_create(monkeypatch):
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(list(argv))
        if argv[1:3] == ["container", "inspect"]:
            return _completed(stdout="[]")
        return _completed(returncode=1)

    monkeypatch.setattr(disposable, "_docker_binary", lambda: "/usr/bin/docker")
    monkeypatch.setattr(disposable.subprocess, "run", run)
    with pytest.raises(disposable.LifecycleError, match="collision"):
        disposable.main(["up"])
    assert not any(len(call) > 1 and call[1] == "run" for call in calls)


def test_status_is_sanitized(monkeypatch, capsys):
    monkeypatch.setattr(disposable, "_resource_exists", lambda *_args: False)
    monkeypatch.setattr(disposable, "_port_is_free", lambda: True)
    assert disposable.main(["status"]) == 0
    output = capsys.readouterr().out
    assert "password" not in output.lower()
    assert "postgresql://" not in output
    assert EXPECTED["container"] in output
