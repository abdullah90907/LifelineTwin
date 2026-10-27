"""Run local regressions with real HTTP transports blocked; no provider access.

MockTransport and ASGI test clients still work. Spawned agent test workers run
controlled test providers or locally cached analytical tools only.
"""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    import httpx
    import requests
    os.environ["HF_HOME"] = str(ROOT / ".runtime/huggingface")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    blocked = []

    def reject(*args, **kwargs):
        blocked.append("external_http_transport")
        raise AssertionError("Real HTTP transport forbidden in offline regressions")

    def reject_requests(*args, **kwargs):
        blocked.append("requests_transport")
        raise requests.ConnectionError("Offline regression HTTP guard")

    with patch.object(httpx.HTTPTransport,"handle_request",reject), \
         patch.object(httpx.AsyncHTTPTransport,"handle_async_request",reject), \
         patch.object(requests.sessions.Session,"request",reject_requests):
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({"real_http_transports_blocked": True, "blocked_request_attempts":len(blocked),
                      "tests_run":result.testsRun,"successful":result.wasSuccessful()}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
