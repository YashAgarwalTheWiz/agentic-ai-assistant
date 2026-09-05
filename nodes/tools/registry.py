"""Single source of truth for tools.

A tool is a plain Python function plus a JSON schema the model can read.
Register with @tool; nothing else in the codebase changes when you add one.
"""

TOOLS = {}          # name -> callable
TOOL_SCHEMAS = []   # OpenAI-format schemas sent to the model
READ_TOOLS = set()   # names that run immediately
WRITE_TOOLS = set()  # names that require approval

def is_write_tool(name: str) -> bool:
    return name in WRITE_TOOLS

def tool(name: str, description: str, parameters: dict, write: bool = False):
    """Register a function as a model-callable tool.

    write=True marks an action that changes the outside world (posting,
    sending, deleting). Nothing uses this flag yet; Phase 3 will gate
    these behind a human approval step.
    """
    def decorator(fn):
        TOOLS[name] = fn
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })
        if write:
            WRITE_TOOLS.add(name)
        else:
            READ_TOOLS.add(name)
        fn.is_write_tool = write
        return fn
    return decorator

def get_schema(name: str) -> dict:
    """The parameters schema for a tool, or {} if unknown."""
    for s in TOOL_SCHEMAS:
        if s["function"]["name"] == name:
            return s["function"].get("parameters", {})
    return {}


def missing_required(name: str, args: dict) -> list:
    """Required properties absent or blank in args."""
    required = get_schema(name).get("required", [])
    return [r for r in required
            if r not in args or args[r] in (None, "")]