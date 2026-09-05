from langgraph.graph import StateGraph, START, END

from state import AgentState
from nodes.memory_retrieval import memory_retrieval
from nodes.llm_call import llm_call
from nodes.tool_node import tool_node
from nodes.memory_writer import memory_writer
import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

MAX_STEPS = 8


def should_continue(state: AgentState) -> str:
    """The conditional edge. This is what makes the graph an agent."""
    last = state['messages'][-1]
    if last.get("tool_calls"):
        if state.get("steps", 0) >= MAX_STEPS:
            return "end"          # circuit breaker
        return "tools"
    return "end"


graph = StateGraph(AgentState)

graph.add_node('memory_retrieval', memory_retrieval)
graph.add_node('llm_call', llm_call)
graph.add_node('tool_node', tool_node)
graph.add_node('memory_writer', memory_writer)

graph.add_edge(START, 'memory_retrieval')
graph.add_edge('memory_retrieval', 'llm_call')
graph.add_conditional_edges(
    'llm_call',
    should_continue,
    {"tools": "tool_node", "end": "memory_writer"},
)
graph.add_edge('tool_node', 'llm_call')   # <-- the cycle
graph.add_edge('memory_writer', END)

CHECKPOINT_DB = os.environ.get('CHECKPOINT_DB', 'checkpoints.db')

_conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
checkpointer = SqliteSaver(_conn)

workflow = graph.compile(checkpointer=checkpointer)