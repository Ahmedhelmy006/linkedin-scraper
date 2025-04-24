# services/brain.py
"""
Brain module for LinkedIn scraper system.

The Brain is the central decision-making component that manages scheduling,
queue prioritization, and session execution based on human-like patterns.
"""

import json
import os
import logging
import threading
import time
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import traceback

from config.scraper_config import (
    MEMORY_PATH, STATES, EVENTS, SESSION_TYPES, 
    ACTIVE_HOURS, SESSIONS_PER_HOUR, MINIMUM_SESSION_SPACING
)
from utils.event_bus import EventBus
from utils.state_machine import StateMachine
from services.linked_navigator.queue_manager import QueueManager

logger = logging.getLogger(__name__)

class Brain:
    """
    Brain for the LinkedIn scraper system.
    
    Handles scheduling decisions, session management, and coordinates
    the overall scraping process based on human-like behavior patterns.
    """
    
    def __init__(self, memory_path: str = MEMORY_PATH):
        """
        Initialize the Brain.
        
        Args:
            memory_path: Path to the memory file
        """
        self.memory_path = memory_path
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        
        # Initialize components
        self.event_bus = EventBus.get_instance()
        self.state_machine = StateMachine(STATES["INACTIVE"])
        self.queue_manager = QueueManager()
        
        # Special hours configuration
        self._configure_special_hours()
        
        # Session planning
        self.next_sessions = []
        self.current_session = None
        
        # Initialize memory if needed
        if not os.path.exists(memory_path):
            self._initialize_memory()
        
        # Register event handlers
        self._register_event_handlers()
    
    def _register_event_handlers(self) -> None:
        """Register handlers for system events."""
        self.event_bus.subscribe(EVENTS["QUEUE_UPDATED"], self._handle_queue_updated)
        self.event_bus.subscribe(EVENTS["PROFILE_SCRAPED"], self._handle_profile_scraped)
        self.event_bus.subscribe(EVENTS["PROFILE_FAILED"], self._handle_profile_failed)
    
    def _handle_queue_updated(self, data: Dict[str, Any]) -> None:
        """
        Handle queue updated event.
        
        Args:
            data: Event data
        """
        if self.state_machine.get_current_state() == STATES["INACTIVE"]:
            # If system is inactive but we have queued profiles, start planning
            queue_stats = self.queue_manager.get_queue_stats()
            if queue_stats["pending"] > 0:
                self._check_and_activate()
    
    def _handle_profile_scraped(self, data: Dict[str, Any]) -> None:
        """
        Handle profile scraped event.
        
        Args:
            data: Event data
        """
        if self.current_session:
            # Update session metrics
            self.current_session["profiles_completed"] = self.current_session.get("profiles_completed", 0) + 1
            self.current_session["last_activity"] = datetime.now().isoformat()
            
            # Record in memory
            self._update_memory_with_profile(data["url"], "completed", data.get("metadata", {}))
    
    def _handle_profile_failed(self, data: Dict[str, Any]) -> None:
        """
        Handle profile failed event.
        
        Args:
            data: Event data
        """
        if self.current_session:
            # Update session metrics
            self.current_session["profiles_failed"] = self.current_session.get("profiles_failed", 0) + 1
            self.current_session["last_activity"] = datetime.now().isoformat()
            
            # Record in memory
            self._update_memory_with_profile(data["url"], "failed", data.get("metadata", {}))
    
    def _check_and_activate(self) -> None:
        """Check conditions and activate the system if appropriate."""
        current_state = self.state_machine.get_current_state()
        
        if current_state == STATES["INACTIVE"]:
            # Check if we have pending profiles
            queue_stats = self.queue_manager.get_queue_stats()
            if queue_stats["pending"] > 0:
                # Transition to waiting for active hours
                self.state_machine.transition(
                    STATES["WAITING_FOR_ACTIVE_HOURS"],
                    "System activated due to pending profiles"
                )
                
                # Start the main loop if needed
                if not self.running:
                    self.start()
    
    def _configure_special_hours(self) -> None:
        """Configure special hours for today."""
        today = datetime.now().date()
        
        # Random hour with 3 sessions
        self.three_session_hour = random.randint(10, 19)  # Random hour between 10 AM and 7 PM
        
        # Two random hours with 1 session only
        available_hours = list(set(range(10, 20)) - {self.three_session_hour})
        self.one_session_hours = random.sample(available_hours, 2)
        
        logger.info(f"Special hours for {today}: "
                   f"Three sessions at {self.three_session_hour}, "
                   f"One session at {self.one_session_hours}")
    
    def _initialize_memory(self) -> None:
        """Initialize the memory file with empty structure."""
        memory_dir = os.path.dirname(self.memory_path)
        os.makedirs(memory_dir, exist_ok=True)
        
        # Create basic memory structure
        memory = {
            "last_updated": datetime.now().isoformat(),
            "days": {},
            "profiles": {},
            "statistics": {
                "total_sessions": 0,
                "total_profiles_scraped": 0,
                "total_profiles_failed": 0
            }
        }
        
        with open(self.memory_path, 'w') as f:
            json.dump(memory, f, indent=2)
    
    def _read_memory(self) -> Dict[str, Any]:
        """
        Read memory from file.
        
        Returns:
            Memory data
        """
        try:
            with open(self.memory_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Memory file at {self.memory_path} not found or invalid. Initializing.")
            self._initialize_memory()
            return self._read_memory()
    
    def _write_memory(self, memory: Dict[str, Any]) -> None:
        """
        Write memory to file.
        
        Args:
            memory: Memory data to write
        """
        memory["last_updated"] = datetime.now().isoformat()
        
        with open(self.memory_path, 'w') as f:
            json.dump(memory, f, indent=2)
    
    def _update_memory_with_session(self, session_data: Dict[str, Any]) -> None:
        """
        Update memory with session data.
        
        Args:
            session_data: Session data to record
        """
        with self.lock:
            memory = self._read_memory()
            
            # Get date and hour
            session_time = datetime.fromisoformat(session_data["start_time"])
            date_str = session_time.date().isoformat()
            hour = session_time.hour
            
            # Initialize structures if needed
            if date_str not in memory["days"]:
                memory["days"][date_str] = {}
            
            if str(hour) not in memory["days"][date_str]:
                memory["days"][date_str][str(hour)] = {
                    "sessions": []
                }
            
            # Add session data
            memory["days"][date_str][str(hour)]["sessions"].append(session_data)
            
            # Update statistics
            memory["statistics"]["total_sessions"] += 1
            memory["statistics"]["total_profiles_scraped"] += session_data.get("profiles_completed", 0)
            memory["statistics"]["total_profiles_failed"] += session_data.get("profiles_failed", 0)
            
            self._write_memory(memory)
    
    def _update_memory_with_profile(self, profile_url: str, status: str, metadata: Dict[str, Any]) -> None:
        """
        Update memory with profile data.
        
        Args:
            profile_url: Profile URL
            status: Profile status
            metadata: Additional metadata
        """
        with self.lock:
            memory = self._read_memory()
            
            # Initialize if needed
            if "profiles" not in memory:
                memory["profiles"] = {}
            
            # Add or update profile data
            if profile_url in memory["profiles"]:
                memory["profiles"][profile_url]["history"].append({
                    "timestamp": datetime.now().isoformat(),
                    "status": status,
                    "metadata": metadata
                })
                memory["profiles"][profile_url]["last_status"] = status
                memory["profiles"][profile_url]["last_updated"] = datetime.now().isoformat()
            else:
                memory["profiles"][profile_url] = {
                    "first_seen": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat(),
                    "last_status": status,
                    "history": [{
                        "timestamp": datetime.now().isoformat(),
                        "status": status,
                        "metadata": metadata
                    }]
                }
            
            self._write_memory(memory)
    
    def start(self) -> bool:
        """
        Start the Brain's main processing loop.
        
        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Brain is already running")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._main_loop)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("Brain started")
        return True
    
    def stop(self) -> bool:
        """
        Stop the Brain's processing loop.
        
        Returns:
            True if stopped successfully
        """
        if not self.running:
            logger.warning("Brain is not running")
            return False
        
        logger.info("Stopping Brain...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        # Reset state to inactive
        if self.state_machine.get_current_state() != STATES["INACTIVE"]:
            self.state_machine.transition(STATES["INACTIVE"], "Brain stopped")
        
        logger.info("Brain stopped")
        return True
    
    def _main_loop(self) -> None:
        """Main processing loop for the Brain."""
        try:
            while self.running:
                try:
                    current_state = self.state_machine.get_current_state()
                    
                    if current_state == STATES["WAITING_FOR_ACTIVE_HOURS"]:
                        self._handle_waiting_for_active_hours()
                    elif current_state == STATES["PLANNING_NEXT_SESSION"]:
                        self._handle_planning_next_session()
                    elif current_state == STATES["COOLDOWN_PERIOD"]:
                        self._handle_cooldown_period()
                    elif current_state == STATES["ERROR"]:
                        self._handle_error_state()
                    # ADD THIS BLOCK HERE
                    elif current_state == STATES["SESSION_STARTING"]:
                        # Check if it's time to start the session
                        state_data = self.state_machine.get_state_data()
                        session_plan = state_data.get("session_plan", {})
                        
                        if session_plan:
                            planned_start_time = datetime.fromisoformat(session_plan.get("planned_start_time", ""))
                            
                            if datetime.now() >= planned_start_time:
                                # Start the session
                                logger.info(f"Starting planned session {session_plan['id']}")
                                self.session_started(session_plan['id'])
                                
                                # Transition to FEED_BROWSING state
                                self.state_machine.transition(
                                    STATES["FEED_BROWSING"],
                                    f"Starting session {session_plan['id']}",
                                    {"session_id": session_plan['id']}
                                )
                    
                    # Short sleep to prevent CPU hogging
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error in Brain main loop: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Transition to error state
                    self.state_machine.transition(
                        STATES["ERROR"],
                        f"Error in main loop: {str(e)}",
                        {"error": str(e), "traceback": traceback.format_exc()}
                    )
                    
                    # Safety sleep to prevent error loops
                    time.sleep(10)
        except Exception as e:
            logger.critical(f"Fatal error in Brain: {str(e)}")
            logger.critical(traceback.format_exc())
            self.running = False
    
    def _handle_waiting_for_active_hours(self) -> None:
        """Handle the WAITING_FOR_ACTIVE_HOURS state."""
        current_hour = datetime.now().hour
        
        if current_hour in ACTIVE_HOURS:
            # We're in active hours, start planning
            self.state_machine.transition(
                STATES["PLANNING_NEXT_SESSION"],
                f"Entered active hours (current hour: {current_hour})"
            )
        else:
            # Calculate time until next active hour
            now = datetime.now()
            next_active_hour = None
            
            for hour in sorted(ACTIVE_HOURS):
                if hour > current_hour:
                    next_active_hour = hour
                    break
            
            if next_active_hour is None:
                # No more active hours today, wait until tomorrow
                next_active_hour = min(ACTIVE_HOURS)
                next_time = now.replace(hour=next_active_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
            else:
                next_time = now.replace(hour=next_active_hour, minute=0, second=0, microsecond=0)
            
            wait_seconds = (next_time - now).total_seconds()
            
            logger.info(f"Outside active hours. Waiting until {next_time.strftime('%H:%M:%S')} "
                       f"({wait_seconds/60:.1f} minutes)")
            
            # Long sleep to prevent frequent checks
            time.sleep(min(wait_seconds, 300))  # Sleep at most 5 minutes
    
    def _handle_planning_next_session(self) -> None:
        """Handle the PLANNING_NEXT_SESSION state."""
        # Check if we have pending profiles
        queue_stats = self.queue_manager.get_queue_stats()
        if queue_stats["pending"] == 0:
            # No profiles to process, go back to waiting
            self.state_machine.transition(
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                "No pending profiles in queue"
            )
            return
        
        # Calculate when the next session should start
        next_session_time = self._calculate_next_session_time()
        
        # Select session type
        session_type = self._select_session_type()
        
        # Calculate session parameters
        min_duration, max_duration = session_type["duration"]
        session_duration = random.uniform(min_duration, max_duration) * 60  # Convert to seconds
        max_profiles = session_type["max_profiles"]
        
        # Get profiles for the session
        profiles = self.queue_manager.get_next_profiles(max_profiles)
        
        if not profiles:
            # This shouldn't happen based on our earlier check, but just in case
            self.state_machine.transition(
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                "Failed to get profiles for session"
            )
            return
        
        # Plan the session
        session_plan = {
            "id": f"session_{int(time.time())}",
            "type": session_type["name"],
            "planned_start_time": next_session_time.isoformat(),
            "planned_duration": session_duration,
            "max_profiles": max_profiles,
            "profiles": profiles
        }
        
        # Store the plan
        self.next_sessions.append(session_plan)
        
        # Publish session planned event
        self.event_bus.publish(EVENTS["SESSION_PLANNED"], session_plan)
        
        logger.info(f"Planned {session_type['name']} session for {next_session_time.strftime('%H:%M:%S')}: "
                   f"{len(profiles)} profiles, {session_duration/60:.1f} minutes duration")
        
        # Update state data
        self.state_machine.transition(
            STATES["SESSION_STARTING"],
            f"Session planned for {next_session_time.strftime('%H:%M:%S')}",
            {"session_plan": session_plan}
        )
        
        # Wait until the session should start
        wait_seconds = (next_session_time - datetime.now()).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
    
    def _handle_cooldown_period(self) -> None:
        """Handle the COOLDOWN_PERIOD state."""
        # Check if we're in active hours
        current_hour = datetime.now().hour
        if current_hour not in ACTIVE_HOURS:
            # Outside active hours, transition to waiting
            self.state_machine.transition(
                STATES["WAITING_FOR_ACTIVE_HOURS"],
                f"Cooldown ended outside active hours (current hour: {current_hour})"
            )
            return
        
        # Get cooldown duration from state data
        state_data = self.state_machine.get_state_data()
        cooldown_end = datetime.fromisoformat(state_data.get("cooldown_end", datetime.now().isoformat()))
        
        if datetime.now() >= cooldown_end:
            # Cooldown period finished, plan next session
            self.state_machine.transition(
                STATES["PLANNING_NEXT_SESSION"],
                "Cooldown period ended"
            )
        else:
            # Still in cooldown, wait a bit
            wait_seconds = (cooldown_end - datetime.now()).total_seconds()
            logger.info(f"In cooldown period. {wait_seconds/60:.1f} minutes remaining.")
            time.sleep(min(wait_seconds, 60))  # Wait at most 1 minute
    
    def _handle_error_state(self) -> None:
        """Handle the ERROR state."""
        # Simple recovery: wait a bit and try to restart
        logger.info("In error state. Attempting recovery...")
        time.sleep(30)  # Wait 30 seconds
        
        # Try to restart by going back to planning
        self.state_machine.transition(
            STATES["WAITING_FOR_ACTIVE_HOURS"],
            "Recovering from error state"
        )
    
    def _calculate_next_session_time(self) -> datetime:
        """
        Calculate when the next session should start.
        
        Returns:
            Planned start time for the next session
        """
        now = datetime.now()
        current_hour = now.hour
        
        # Check how many sessions we've already had in this hour
        memory = self._read_memory()
        date_str = now.date().isoformat()
        
        sessions_this_hour = 0
        if date_str in memory["days"] and str(current_hour) in memory["days"][date_str]:
            sessions_this_hour = len(memory["days"][date_str][str(current_hour)]["sessions"])
        
        # Determine how many sessions we should have in this hour
        if current_hour == self.three_session_hour:
            target_sessions = 3
        elif current_hour in self.one_session_hours:
            target_sessions = 1
        else:
            target_sessions = SESSIONS_PER_HOUR
        
        if sessions_this_hour >= target_sessions:
            # We've reached our session limit for this hour, plan for next hour
            next_hour = current_hour + 1
            if next_hour not in ACTIVE_HOURS:
                # Find next active hour
                next_active_hour = None
                for hour in sorted(ACTIVE_HOURS):
                    if hour > current_hour:
                        next_active_hour = hour
                        break
                
                if next_active_hour is None:
                    # No more active hours today, use first hour tomorrow
                    next_active_hour = min(ACTIVE_HOURS)
                    next_time = now.replace(hour=next_active_hour, minute=0, second=0, microsecond=0) + timedelta(days=1)
                else:
                    next_time = now.replace(hour=next_active_hour, minute=0, second=0, microsecond=0)
            else:
                # Plan for next hour
                next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
            
            # Add random offset in first 15 minutes
            random_offset = random.randint(1, 15 * 60)
            next_time = next_time + timedelta(seconds=random_offset)
        else:
            # We can still have a session this hour
            # Check when the last session ended
            last_session_end = None
            if self.current_session and "end_time" in self.current_session:
                last_session_end = datetime.fromisoformat(self.current_session["end_time"])
            elif date_str in memory["days"] and str(current_hour) in memory["days"][date_str]:
                hour_sessions = memory["days"][date_str][str(current_hour)]["sessions"]
                if hour_sessions:
                    last_session = hour_sessions[-1]
                    if "end_time" in last_session:
                        last_session_end = datetime.fromisoformat(last_session["end_time"])
            
            if last_session_end:
                # Ensure minimum spacing between sessions
                minimum_next_time = last_session_end + timedelta(seconds=MINIMUM_SESSION_SPACING)
                if minimum_next_time > now:
                    next_time = minimum_next_time
                else:
                    # We can start soon, add a small random delay
                    next_time = now + timedelta(seconds=random.randint(30, 300))  # 30 sec to 5 min
            else:
                # No previous session, we can start soon
                next_time = now + timedelta(seconds=random.randint(30, 300))  # 30 sec to 5 min
        
        return next_time
    
    def _select_session_type(self) -> Dict[str, Any]:
        """
        Select a session type based on probability distribution.
        
        Returns:
            Selected session type
        """
        rand = random.random()
        cumulative_prob = 0
        
        for session_type in SESSION_TYPES:
            cumulative_prob += session_type["probability"]
            if rand <= cumulative_prob:
                return session_type
        
        # Default to first session type if something goes wrong
        return SESSION_TYPES[0]
    

    def session_started(self, session_id: str) -> None:
        """
        Notify the Brain that a session has started.
        
        Args:
            session_id: ID of the started session
        """
        # Find the session plan
        session_plan = None
        for plan in self.next_sessions:
            if plan["id"] == session_id:
                session_plan = plan
                break
        
        if not session_plan:
            logger.error(f"Session {session_id} not found in planned sessions")
            return
        
        # Remove from next sessions
        self.next_sessions = [s for s in self.next_sessions if s["id"] != session_id]
        
        # Create current session tracking
        self.current_session = {
            **session_plan,
            "start_time": datetime.now().isoformat(),
            "profiles_started": 0,
            "profiles_completed": 0,
            "profiles_failed": 0
        }
        
        # ADD THIS LOG
        logger.info(f"Publishing SESSION_STARTED event for session {session_id}")
        # Publish event
        self.event_bus.publish(EVENTS["SESSION_STARTED"], self.current_session)
        
        logger.info(f"Session {session_id} started")
    
    def session_ended(self, session_id: str, stats: Dict[str, Any]) -> None:
        """
        Notify the Brain that a session has ended.
        
        Args:
            session_id: ID of the ended session
            stats: Statistics about the session
        """
        if not self.current_session or self.current_session["id"] != session_id:
            logger.error(f"Session {session_id} not found in current session")
            return
        
        # Update session record
        self.current_session.update({
            "end_time": datetime.now().isoformat(),
            "actual_duration": (datetime.now() - datetime.fromisoformat(self.current_session["start_time"])).total_seconds(),
            **stats
        })
        
        # Record in memory
        self._update_memory_with_session(self.current_session)
        
        # Publish event
        self.event_bus.publish(EVENTS["SESSION_ENDED"], self.current_session)
        
        # Calculate cooldown period
        cooldown_minutes = random.randint(10, 30)
        cooldown_end = datetime.now() + timedelta(minutes=cooldown_minutes)
        
        # Transition to cooldown
        self.state_machine.transition(
            STATES["COOLDOWN_PERIOD"],
            f"Session ended, cooldown for {cooldown_minutes} minutes",
            {
                "session": self.current_session,
                "cooldown_minutes": cooldown_minutes,
                "cooldown_end": cooldown_end.isoformat()
            }
        )
        
        # Clear current session
        completed_session = self.current_session
        self.current_session = None
        
        logger.info(f"Session {session_id} ended. Scraped {completed_session['profiles_completed']} profiles "
                   f"in {completed_session['actual_duration']/60:.1f} minutes.")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the Brain.
        
        Returns:
            Dictionary with current status
        """
        return {
            "running": self.running,
            "state": self.state_machine.get_current_state(),
            "state_data": self.state_machine.get_state_data(),
            "current_session": self.current_session,
            "next_sessions": self.next_sessions,
            "queue_stats": self.queue_manager.get_queue_stats(),
            "special_hours": {
                "three_session_hour": self.three_session_hour,
                "one_session_hours": self.one_session_hours
            }
        }