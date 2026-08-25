from langgraph.store.memory import InMemoryStore
import time

store = InMemoryStore()

async def write_episodes(user_id: str, department:str, summary: str):
    await store.aput(
        namespace=(user_id, department),
        key=f"episode_{time.time()}",
        value={"summary": summary, "timestamp": time.time()},
    )
    
async def get_relevant_episodes(user_id: str, department: str, query: str, limit: int = 3):
    results = await store.asearch(
        namespace=(user_id, department),
        query=query,
        limit = limit,
    )
    
    return [r.value["summary"] for r in results]