from ddgs import DDGS
from nodes.tools.registry import tool


@tool(
    name="web_search",
    description=(
        '''
        "Search the web for current, real-time, or recent information that you "
        "do not already know: news, prices, live events, weather, anything after "
        "your training cutoff. Do NOT use this for general knowledge you already "
        "have, for greetings, or for questions about the user's uploaded documents."
        You do NOT know anything that happened after your training cutoff. Assume
        your knowledge of recent events, sports results, prices, and current
        office-holders is STALE and must be verified. If a question involves
        "latest", "last", "current", "recent", or "now", search first — do not
        answer from memory.'''
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "A short, focused search query of 3-8 words, phrased the way "
                    "you would type it into a search engine. NOT the user's full "
                    "message. Example: user asks 'hey can you find out who won the "
                    "cricket match between india and australia yesterday' -> query "
                    "should be 'India Australia cricket result'."
                ),
            }
        },
        "required": ["query"],
    },
    write=False,
)
def web_search(query: str) -> str:
    results = DDGS().text(query, max_results=5)
    if not results:
        return "No results found. Try rephrasing with different keywords."
    output = ""
    for r in results:
        output += f"{r['title']}\n{r['body']}\nSource: {r['href']}\n\n"
    return output