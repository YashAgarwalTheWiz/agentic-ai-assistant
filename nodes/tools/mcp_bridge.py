"""Bridge to remote MCP servers.

Connects to a configured MCP server, asks it what tools it has, and
registers each one through the same @tool decorator every hand-written
tool uses. From tool_node's point of view, an MCP-backed tool is
indistinguishable from save_note or web_search -- it's a name in TOOLS
that takes a dict of arguments and returns a string.

Read/write classification does NOT trust the server. A tool is only
treated as read-only if the server explicitly says readOnlyHint is
True -- the exact boolean, not a truthy string or a missing field.
Confirmed necessary: DeepWiki, a server that genuinely is read-only,
sends no annotations at all.
"""

import asyncio
import threading

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from nodes.tools.registry import tool

# One server for now. Add more entries here later.
MCP_SERVERS = {
    "deepwiki": "https://mcp.deepwiki.com/mcp",
}


def run_async(coro):
    """Run an async coroutine from sync code, whether or not the calling
    thread already has an event loop running.

    Needed because tool registration turned out to happen inside a live
    loop under uvicorn --reload -- plain asyncio.run() raises there.
    Rather than special-case that one caller, every async entry point in
    this file goes through here, since it's evidence our assumption
    ("nothing is ever running a loop at this point") can be wrong in
    places we didn't predict.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # The common case: no loop on this thread. Just run it.
        return asyncio.run(coro)

    # A loop IS already running here (e.g. reload machinery). Run the
    # coroutine on its own fresh loop in a separate thread instead.
    result = {}

    def _runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as e:
            result["error"] = e

    thread = threading.Thread(target=_runner)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]
    return result["value"]


def _is_read_only(annotations) -> bool:
    """True only if the server explicitly, correctly says so."""
    if annotations is None:
        return False
    hint = getattr(annotations, "readOnlyHint", None)
    return hint is True  # exact type check -- a truthy string doesn't count


def _extract_text(result) -> str:
    """MCP results are a list of content blocks. Join the text ones."""
    parts = [b.text for b in result.content if hasattr(b, "text")]
    return "\n".join(parts) if parts else str(result.content)


async def _call_remote(server_url, tool_name, args):
    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, args)
            return _extract_text(result)


def _make_caller(server_url, tool_name):
    """Build the sync function tool_node will actually call.

    Must be its own function, not written inline inside the loop below --
    a closure created directly in a for-loop captures the loop VARIABLE,
    not its value at that moment. Every registered tool would end up
    silently calling whichever tool_name was left over after the loop
    finished. Passing it in as an argument here freezes the value instead.
    """
    def caller(**kwargs) -> str:
        return run_async(_call_remote(server_url, tool_name, kwargs))
    return caller


async def _discover(server_url):
    async with streamablehttp_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


def register_mcp_server(label: str, server_url: str):
    """Fetch this server's tools once, at import time, and register each."""
    discovered = run_async(_discover(server_url))

    for t in discovered:
        registered_name = f"{label}_{t.name}"
        is_write = not _is_read_only(t.annotations)

        tool(
            name=registered_name,
            description=f"[{label}] {t.description}",
            parameters=t.inputSchema,
            write=is_write,
        )(_make_caller(server_url, t.name))

    print(f"[MCP] registered {len(discovered)} tools from '{label}'")


for _label, _url in MCP_SERVERS.items():
    try:
        register_mcp_server(_label, _url)
    except Exception as e:
        print(f"[MCP] could not register '{_label}' ({_url}): {e}")