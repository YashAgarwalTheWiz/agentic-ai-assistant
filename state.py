from typing import TypedDict,Literal,List,Dict,Optional,Any,Annotated
import operator

class AgentState(TypedDict):
    messages:Annotated[List[Dict[str,Any]],operator.add]
    chat_id:str
    long_term_memory:str
    thread_id: str
    user_input:str
    response:str
    steps:int
    executed_tools: Annotated[List[str], operator.add]