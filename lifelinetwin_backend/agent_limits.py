"""Killable subprocess boundaries for SDK and analytical calls on Windows."""
import multiprocessing as mp
from .agent_failures import ProviderFailure, classify_exception


class ExecutionLimit(RuntimeError):
    pass


def _worker(connection, function, args):
    try:
        value = function(*args)
        connection.send({"ok": True, "value": value})
    except BaseException as exc:
        # Exception messages can contain credentials, URLs, or external input.
        connection.send({"ok": False, "failure": classify_exception(exc).model_dump()})
    finally:
        connection.close()


def bounded_call(function, args, timeout):
    context = mp.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(send, function, args), daemon=True)
    process.start()
    send.close()
    try:
        if not receive.poll(max(0.01, timeout)):
            raise ExecutionLimit("Execution deadline exceeded; worker terminated")
        try:
            result = receive.recv()
        except EOFError as exc:
            from .agent_failures import FailureMetadata
            raise ProviderFailure(FailureMetadata(category="worker_failure", stage="provider_worker")) from exc
        if not result["ok"]:
            raise ProviderFailure(result["failure"])
        return result["value"]
    finally:
        receive.close()
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)


def provider_call(provider, messages, tools, timeout):
    return provider.complete(messages, tools, timeout)


def analytical_call(settings, operation, payload):
    from .services import Tools
    from .schemas import EnvironmentRequest, GeographicRequest
    adapter = Tools(settings)
    if operation == "geographic":
        return adapter.geographic(GeographicRequest.model_validate(payload)).model_dump(mode="json")
    if operation == "environment":
        return adapter.environment(EnvironmentRequest.model_validate(payload)).model_dump(mode="json")
    raise ValueError("Operation not permitted")
