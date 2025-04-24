# utils/state_machine.py
"""
State machine implementation for managing system state.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Callable
import threading
import time
from datetime import datetime

from config.scraper_config import STATES, EVENTS
from utils.event_bus import EventBus

logger = logging.getLogger(__name__)

class StateMachine:
    """
    State machine for managing system state transitions.
    
    Enforces valid state transitions and publishes events when state changes.
    """
    
    def __init__(self, initial_state: str = STATES["INACTIVE"]):
        """
        Initialize the state machine.
        
        Args:
            initial_state: Initial state of the system
        """
        self.current_state = initial_state
        self.state_history = []
        self.state_data = {}
        self.lock = threading.Lock()
        self.event_bus = EventBus.get_instance()
        
        # Define valid state transitions
        self.valid_transitions = {
            STATES["INACTIVE"]: {
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                STATES["ERROR"]
            },
            STATES["WAITING_FOR_ACTIVE_HOURS"]: {
                STATES["PLANNING_NEXT_SESSION"],
                STATES["INACTIVE"],
                STATES["ERROR"]
            },
            STATES["PLANNING_NEXT_SESSION"]: {
                STATES["SESSION_STARTING"],
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                STATES["INACTIVE"],
                STATES["ERROR"]
            },
            STATES["SESSION_STARTING"]: {
                STATES["FEED_BROWSING"],
                STATES["INACTIVE"],
                STATES["ERROR"]
            },
            STATES["FEED_BROWSING"]: {
                STATES["PROFILE_SCRAPING"],
                STATES["SESSION_ENDING"],
                STATES["ERROR"]
            },
            STATES["PROFILE_SCRAPING"]: {
                STATES["PROFILE_SCRAPING"],  # Can stay in this state for multiple profiles
                STATES["SESSION_ENDING"],
                STATES["ERROR"]
            },
            STATES["SESSION_ENDING"]: {
                STATES["COOLDOWN_PERIOD"],
                STATES["INACTIVE"],
                STATES["ERROR"]
            },
            STATES["COOLDOWN_PERIOD"]: {
                STATES["PLANNING_NEXT_SESSION"],
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                STATES["INACTIVE"],
                STATES["ERROR"]
            },
            STATES["ERROR"]: {
                STATES["INACTIVE"],
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                STATES["PLANNING_NEXT_SESSION"]
            }
        }
        
        # Record initial state
        self._record_state_change(initial_state, None, "Initialization")
    
    def transition(self, new_state: str, reason: str = "", data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: State to transition to
            reason: Reason for the transition
            data: Additional data related to the state change
            
        Returns:
            True if transition was successful, False otherwise
        """
        with self.lock:
            if new_state not in self.valid_transitions.get(self.current_state, set()):
                logger.error(
                    f"Invalid state transition from {self.current_state} to {new_state}. "
                    f"Valid transitions: {self.valid_transitions.get(self.current_state, set())}"
                )
                return False
            
            old_state = self.current_state
            self.current_state = new_state
            
            # Update state data
            if data:
                self.state_data = data
            
            # Record the state change
            self._record_state_change(new_state, old_state, reason)
            
            # Publish event
            self.event_bus.publish(EVENTS["SYSTEM_STATE_CHANGED"], {
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"System state changed from {old_state} to {new_state}: {reason}")
            return True
    
    def _record_state_change(self, new_state: str, old_state: Optional[str], reason: str) -> None:
        """
        Record a state change in history.
        
        Args:
            new_state: New state
            old_state: Previous state
            reason: Reason for the change
        """
        self.state_history.append({
            "timestamp": datetime.now().isoformat(),
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason
        })
        
        # Limit history size
        if len(self.state_history) > 100:
            self.state_history = self.state_history[-100:]
    
    def get_current_state(self) -> str:
        """
        Get the current system state.
        
        Returns:
            Current state
        """
        with self.lock:
            return self.current_state
    
    def get_state_data(self) -> Dict[str, Any]:
        """
        Get current state data.
        
        Returns:
            State data dictionary
        """
        with self.lock:
            return self.state_data.copy()
    
    def can_transition(self, state: str) -> bool:
        """
        Check if a transition to the given state is valid.
        
        Args:
            state: State to check
            
        Returns:
            True if transition is valid, False otherwise
        """
        with self.lock:
            return state in self.valid_transitions.get(self.current_state, set())
    
    def get_history(self, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Get state transition history.
        
        Args:
            limit: Maximum number of history entries to return (0 for all)
            
        Returns:
            List of state transition records
        """
        with self.lock:
            if limit > 0:
                return self.state_history[-limit:]
            return self.state_history.copy()