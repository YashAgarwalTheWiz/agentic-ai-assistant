from langgraph.graph import StateGraph,START,END
from state import AgentState
from nodes.memory_retrieval import memory_retrieval
from nodes.router import router
from nodes.llm_call import llm_call
from nodes.memory_writer import memory_writer

graph=StateGraph(AgentState)

graph.add_node('memory_retrieval',memory_retrieval)
graph.add_node('router',router)
graph.add_node('llm_call',llm_call)
graph.add_node('memory_writer',memory_writer)

graph.add_edge(START,'memory_retrieval')
graph.add_edge('memory_retrieval','router')
graph.add_edge('router','llm_call')
graph.add_edge('llm_call','memory_writer')
graph.add_edge('memory_writer',END)

workflow=graph.compile()
