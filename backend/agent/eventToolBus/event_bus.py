import asyncio
import logging
from collections import defaultdict

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
    
    def subscribe(self, event_type: str, handler) -> None:
        self._subscribers[event_type].append(handler)
    
    async def publish(self, event) -> None:
        event_type = event.event_type.values
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.warning("no subscribers for: %s", event_type)  
            return
        await asyncio.gather(*(h(event) for h in handlers))  
    