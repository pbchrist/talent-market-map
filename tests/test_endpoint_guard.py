"""The browser's endpoint resolver, run from the suite Patrick actually runs.

The guard lives in docs/app.js, so the real assertions are in
tests/js/endpoint_guard.test.js. This drags them into pytest, because a test
that needs a second command to remember is a test that does not get run -- and
not running it is how this app spent two weeks pointed at a dead host.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

SUITE = Path(__file__).parent / "js" / "endpoint_guard.test.js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_endpoint_resolver_refuses_ephemeral_hosts():
    r = subprocess.run(["node", str(SUITE)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
