from ddgs import DDGS

def search(query:str)->str:
    result=DDGS().text(query, max_results=5)
    output = ""
    for i, r in enumerate(result):
        output += f'''Result {i+1}: {r['title']}
                    URL : {r['href']}
                    summary: {r['body']}'''
    return output