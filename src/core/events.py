"""
Event System for Component Communication

This module implements a publish-subscribe event system that allows
decoupled communication between different parts of the application.
Components can publish events when state changes occur, and other
components can subscribe to receive notifications.

The event system enables loose coupling between UI components and
business logic services, making the codebase more maintainable
and easier to test.

Classes:
    EventType: Enumeration of all available event types
    Event: Data structure for event information
    EventBus: Central event dispatcher and subscription manager
"""
from typing import Any, Callable
from enum import Enum, auto
from dataclasses import dataclass
from utils.logging_config import get_logger


class EventType(Enum):
    """Enumeration of all application events."""
    # Experiment events
    EXPERIMENT_CHANGED = auto()
    EXPERIMENT_LOADED = auto()
    EXPERIMENT_REFRESHED = auto()
    
    # Image events
    IMAGE_SELECTED = auto()
    IMAGE_POOL_CHANGED = auto()
    
    # Mask events
    MASK_CREATED = auto()
    MASK_CLEARED = auto()
    MASK_SAVED = auto()
    
    # Tool events
    TOOL_CHANGED = auto()  # brush, marker, etc.
    AUTO_SAM_TOGGLED = auto()  # Auto SAM checkbox toggled
    SAM_MARKER_ADDED = auto()  # SAM marker placed on canvas
    SAM_MARKER_REMOVED = auto()  # SAM marker removed from canvas
    
    # Folder events
    FOLDER_REFRESH_REQUESTED = auto()
    
    # UI events
    STATUS_UPDATE = auto()

@dataclass
class Event:
    """Base event class containing event data."""
    event_type: EventType
    data: Any = None
    source: str = None

class EventBus:
    """
    Central event bus for application-wide communication.
    Implements singleton pattern to ensure single instance.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = {}
            cls._instance.logger = get_logger(__name__)
        return cls._instance
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type with a callback function."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass  # Callback not found
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # Log error but continue processing other callbacks
                    self.logger.error(f"Error in event callback for {event.event_type}: {e}", exc_info=True)
    
    def clear_all(self) -> None:
        """Clear all subscribers (useful for testing)."""
        self._subscribers.clear()

# Global event bus instance
event_bus = EventBus()