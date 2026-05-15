from typing import TypedDict,Literal,List,Dict,Optional

class AgentState(TypedDict):
    messages:List[Dict[str,str]]
    chat_id:str
    long_term_memory:str
    query_type:Literal['chat','search','rag','structured']
    user_input:str
    response:str
    tool_result:Optional[str]
    structured_output: Optional[list]