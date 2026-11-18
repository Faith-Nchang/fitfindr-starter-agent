"""
Calling an MCP tool from your agent. ← UNIT 4

This is the plumbing, and it's given to you. Connecting over stdio and turning
the protocol's response back into a Python value is fiddly and it isn't the
lesson. What *is* the lesson is on the other side, in `mcp_server.py`: writing
a tool description and typed inputs that something other than your own code can
read.

Use it like this, in `run_agent()`:

    from mcp_client import call_tool

    results = call_tool("search_listings", {
        "description": "graphic tee",
        "max_price": 30,
    })

`results` comes back as the same list of dicts `search_listings` returned when
you called it directly. **That's the promise: the call changes shape, the
return value does not.** If it does change, that difference is information —
usually it means your tool was returning something you hadn't noticed.

Every call starts the server, asks, and stops it again. That's slower than
holding a connection open and it is much easier to reason about, which is the
right trade for one unit.
"""

import asyncio
import contextlib
import json
import os
import sys
import threading
from pathlib import Path

SERVER = Path(__file__).parent / "mcp_server.py"


class MCPError(RuntimeError):
    """The server couldn't be reached, or it refused the call."""


def call_tool(name: str, arguments: dict):
    """
    Call one tool on your MCP server and return what it returns.

    Args:
        name:      the tool name, exactly as registered in mcp_server.py.
        arguments: a dict of the tool's inputs. The names and types have to
                   match the registration — that's your Tool Inventory, now
                   being enforced by something other than you.

    Returns:
        Whatever the tool returns, unwrapped back to its native Python shape.
        A tool returning a list of dicts gives you a list of dicts.

    Raises:
        MCPError, with something readable in it.
    """
    try:
        if _shared is not None:
            return _shared.call(name, arguments)
        return asyncio.run(_call(name, arguments))
    except MCPError:
        raise
    except BaseExceptionGroup as group:
        # The connection runs inside a task group, which wraps anything raised
        # in it as "unhandled errors in a TaskGroup". Unwrap it so the real
        # message (e.g. "Couldn't reach the model: ...") reaches the caller.
        leaf = _first_leaf(group)
        if isinstance(leaf, MCPError):
            raise leaf from None
        raise MCPError(f"Couldn't call '{name}' over MCP: {leaf}") from leaf
    except Exception as exc:  # noqa: BLE001 — re-raised readably below
        raise MCPError(
            f"Couldn't call '{name}' over MCP: {exc}\n"
            f"Check that mcp_server.py runs on its own first:\n"
            f"    python mcp_server.py\n"
            f"If it exits immediately with an error, fix that before coming back here."
        ) from exc


def _first_leaf(exc: BaseException) -> BaseException:
    """The innermost real exception inside (possibly nested) exception groups."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def _server_params():
    from mcp import StdioServerParameters

    import config

    # The MCP client hands the server only a few safe variables by default, so
    # the server would never see this process's key or its cache setting.
    # run_eval.py turns the cache off in-process; without passing that on, the
    # server would keep answering from cache and five tries would be one answer.
    env = {**os.environ, "AI201_CACHE": "1" if config.CACHE_ENABLED else "0"}
    return StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)


async def _invoke(session, name: str, arguments: dict):
    """One tool call on an already-open session."""
    available = {t.name for t in (await session.list_tools()).tools}
    if name not in available:
        raise MCPError(
            f"The server doesn't offer a tool called '{name}'.\n"
            f"It offers: {', '.join(sorted(available)) or '(nothing yet)'}\n"
            f"Register your tool in mcp_server.py — that's Milestone 1."
        )

    result = await session.call_tool(name, arguments)

    if getattr(result, "isError", False):
        raise MCPError(f"The tool '{name}' returned an error: {_text(result)}")

    return _unwrap(result)


async def _call(name: str, arguments: dict):
    """One tool call on its own server: start it, ask, stop it."""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await _invoke(session, name, arguments)


# ── one server for a whole run (capstone) ────────────────────────────────────
#
# Starting the server costs about 2 s, nearly all of it importing the `mcp`
# package, and a run makes two MCP calls. shared_session() starts the server
# once and keeps it open for every call_tool() inside the `with` block.
#
# The server lives on its own thread with its own event loop, so call_tool()
# stays an ordinary blocking function and still works from code that is not
# async. The server is started when the block is entered, so it inherits the
# environment at that moment (including AI201_RUN_ID, which agent.run_agent
# sets just before). If it can't start, call_tool() falls back to one server
# per call and the error surfaces there as it always did.

_shared = None


class _SharedSession:
    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._session = None
        self._stop = None
        self._holder = None

    def start(self) -> None:
        self._thread.start()
        asyncio.run_coroutine_threadsafe(self._open(), self._loop).result()

    async def _open(self) -> None:
        self._stop = asyncio.Event()
        ready = self._loop.create_future()
        self._holder = asyncio.ensure_future(self._hold(ready))
        await ready

    async def _hold(self, ready) -> None:
        # The context managers are entered and left in this one task, which is
        # what the stdio client requires.
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client

        try:
            async with stdio_client(_server_params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    ready.set_result(None)
                    await self._stop.wait()
        except BaseException as exc:  # noqa: BLE001 — reported to start()
            if not ready.done():
                ready.set_exception(exc)

    def call(self, name: str, arguments: dict):
        return asyncio.run_coroutine_threadsafe(
            _invoke(self._session, name, arguments), self._loop
        ).result()

    def close(self) -> None:
        if self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
            with contextlib.suppress(Exception):
                asyncio.run_coroutine_threadsafe(
                    asyncio.wait_for(asyncio.shield(self._holder), 10), self._loop
                ).result(15)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


@contextlib.contextmanager
def shared_session():
    """Keep one MCP server open for every call_tool() in this block."""
    global _shared
    session = _SharedSession()
    try:
        session.start()
        _shared = session
    except BaseException:  # noqa: BLE001 — fall back to one server per call
        with contextlib.suppress(Exception):
            session.close()
        session = None
    try:
        yield
    finally:
        _shared = None
        if session is not None:
            session.close()


def _unwrap(result):
    """
    Turn an MCP response back into the value the tool actually returned.

    MCP hands back content blocks rather than Python objects, so a tool that
    returned a list of dicts arrives as text containing JSON. This puts it
    back. Without this step your agent would start seeing strings where it used
    to see lists, and every downstream branch would quietly stop working.
    """
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP wraps a bare (non-dict) return value under "result".
        if set(structured) == {"result"}:
            return structured["result"]
        return structured

    text = _text(result)
    if text == "":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _type_of(spec: dict) -> str:
    """Read a type out of a JSON schema entry, including optional ones."""
    if "type" in spec:
        return spec["type"]
    options = spec.get("anyOf") or spec.get("oneOf") or []
    names = [o.get("type") for o in options if o.get("type") and o.get("type") != "null"]
    return " or ".join(names) if names else "?"


def _text(result) -> str:
    parts = []
    for block in getattr(result, "content", []) or []:
        value = getattr(block, "text", None)
        if value:
            parts.append(value)
    return "\n".join(parts).strip()


# ── check it works ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Asking mcp_server.py what it offers…\n")

    async def _list():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return (await session.list_tools()).tools

    try:
        tools = asyncio.run(_list())
    except Exception as exc:  # noqa: BLE001
        print(f"Couldn't reach the server: {exc}")
        sys.exit(1)

    if not tools:
        print("The server is running but offers no tools yet.")
        print("Register one in mcp_server.py — that's Milestone 1.")
        sys.exit(0)

    for tool in tools:
        print(f"  {tool.name}")
        print(f"    {tool.description or '(no description — write one)'}")
        schema = tool.inputSchema or {}
        required = set(schema.get("required", []))
        for key, spec in schema.get("properties", {}).items():
            kind = _type_of(spec)
            mark = "" if key in required else "  (optional)"
            print(f"    - {key}: {kind}{mark}")
        print()
