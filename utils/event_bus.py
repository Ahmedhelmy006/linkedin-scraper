# utils/event_bus.py
"""
Event bus implementation for decoupled component communication.
"""

import logging
from typing import Dict, List, Callable, Any
import threading
import time

logger = logging.getLogger(__name__)

class EventBus:
    """
    Simple event bus implementation to facilitate event-based communication.
    
    This allows components to publish events without knowing who's listening,
    and to subscribe to events without knowing who's publishing.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
    def __init__(self):
        """Initialize the event bus."""
        self.subscribers = {}
        self.history = {}
        self.max_history = 100
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        
        if callback not in self.subscribers[event_type]:
            self.subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to event: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to remove from subscribers
        """
        if event_type in self.subscribers and callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from event: {event_type}")
    
    def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publish an event.
        
        Args:
            event_type: Type of event to publish
            data: Data associated with the event
        """
        # Store in history
        if event_type not in self.history:
            self.history[event_type] = []
        
        self.history[event_type].append({
            "timestamp": time.time(),
            "data": data
        })
        
        # Trim history if needed
        if len(self.history[event_type]) > self.max_history:
            self.history[event_type] = self.history[event_type][-self.max_history:]
        
        # Notify subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type][:]:  # Copy to avoid modification during iteration
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {str(e)}")
        
        logger.debug(f"Published event: {event_type}")
    
    def get_history(self, event_type: str = None) -> Dict:
        """
        Get event history.
        
        Args:
            event_type: Optional event type to filter history
            
        Returns:
            Dictionary of event history
        """
        if event_type:
            return self.history.get(event_type, [])
        return self.history