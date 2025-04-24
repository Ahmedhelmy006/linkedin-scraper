# services/batch_processor.py
"""
Batch processor for LinkedIn profile scraping.

Handles batch processing of profile scraping requests by coordinating
with the Brain for scheduling and execution.
"""

import logging
import threading
import time
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import traceback

from config.scraper_config import EVENTS, STATES
from utils.event_bus import EventBus
from utils.state_machine import StateMachine
from services.linked_navigator.queue_manager import QueueManager
from services.linked_navigator.brain import Brain

logger = logging.getLogger(__name__)

class BatchProcessor:
    """
    Processes batches of LinkedIn profiles for scraping.
    
    This component handles the coordination between external requests
    and the Brain to manage and execute profile scraping tasks.
    """
    
    def __init__(self, brain: Brain, queue_manager: QueueManager):
        """
        Initialize the batch processor.
        
        Args:
            brain: Brain instance for decision making
            queue_manager: Queue manager for profile queue operations
        """
        self.brain = brain
        self.queue_manager = queue_manager
        self.event_bus = EventBus.get_instance()
        self.state_machine = StateMachine()  # Using shared state machine
        
        self.processing_lock = threading.Lock()
        self.session_callback = None
        
        # Register event handlers
        self._register_event_handlers()
    
    def _register_event_handlers(self) -> None:
        """Register handlers for system events."""
        # ADD THIS LOG
        logger.info("Registering BatchProcessor event handlers")
        self.event_bus.subscribe(EVENTS["SESSION_STARTED"], self._handle_session_started)
        self.event_bus.subscribe(EVENTS["SESSION_ENDED"], self._handle_session_ended)
        # ADD THIS LOG
        logger.info("BatchProcessor event handlers registered")
    
    def add_profiles(self, profile_urls: List[str], urgent: bool = False, initiator: str = "") -> Dict[str, Any]:
        """
        Add profiles to the processing queue.
        
        Args:
            profile_urls: List of profile URLs to add
            urgent: Whether these profiles should be processed urgently
            initiator: Who/what initiated this request
            
        Returns:
            Dictionary with results of the operation
        """
        results = {
            "success": True,
            "added": [],
            "failed": [],
            "already_queued": []
        }
        
        for url in profile_urls:
            try:
                # Clean URL
                clean_url = self._clean_profile_url(url)
                
                # Get current queue status
                queue_before = self.queue_manager.get_queue_stats()
                
                # Add to queue
                success = self.queue_manager.add_profile(clean_url, urgent, initiator)
                
                # Get updated queue status
                queue_after = self.queue_manager.get_queue_stats()
                
                if success:
                    # Check if it was a new addition or already queued
                    if queue_after["total"] > queue_before["total"]:
                        results["added"].append(clean_url)
                    else:
                        results["already_queued"].append(clean_url)
                else:
                    results["failed"].append(clean_url)
                    results["success"] = False
                    
            except Exception as e:
                logger.error(f"Error adding profile {url}: {str(e)}")
                results["failed"].append(url)
                results["success"] = False
        
        # Activate the brain if needed
        if results["added"] and self.state_machine.get_current_state() == STATES["INACTIVE"]:
            self.brain._check_and_activate()
        
        return results
    
    def register_session_callback(self, callback: Callable) -> None:
        """
        Register a callback to be called when a session is ready.
        
        The callback will receive the session plan and should handle
        the actual profile scraping during the session.
        
        Args:
            callback: Function to call for session execution
        """
        self.session_callback = callback
    
    def _handle_session_started(self, data: Dict[str, Any]) -> None:
        """
        Handle session started event.
        
        Args:
            data: Session data
        """
        # ADD THIS LOG
        logger.info(f"BatchProcessor received session_started event: {data.get('id')}")
        
        if not self.session_callback:
            logger.error("No session callback registered")
            return
        
        # ADD THIS LOG
        logger.info("Starting session processing thread")
        # Start a thread to process the session
        threading.Thread(target=self._process_session, args=(data,)).start()
    
    def _process_session(self, session_data: Dict[str, Any]) -> None:
        """
        Process a session.
        
        Args:
            session_data: Session data
        """
        session_id = session_data["id"]
        profiles = session_data.get("profiles", [])
        
        logger.info(f"Processing session {session_id} with {len(profiles)} profiles")
        
        stats = {
            "profiles_started": 0,
            "profiles_completed": 0,
            "profiles_failed": 0
        }
        
        try:
            # Lock to prevent concurrent session processing
            with self.processing_lock:
                # Execute the session callback
                if self.session_callback:
                    results = self.session_callback(session_data)
                    
                    # Update stats
                    if results and isinstance(results, dict):
                        stats.update(results)
                    
                    logger.info(f"Session {session_id} processing completed")
                else:
                    logger.error("No session callback registered")
        
        except Exception as e:
            logger.error(f"Error processing session {session_id}: {str(e)}")
            logger.error(traceback.format_exc())
            stats["error"] = str(e)
        
        finally:
            # Notify brain that session has ended
            self.brain.session_ended(session_id, stats)
    
    def _handle_session_ended(self, data: Dict[str, Any]) -> None:
        """
        Handle session ended event.
        
        Args:
            data: Session data
        """
        # This is handled by the Brain, but we could add custom logic here if needed
        pass
    
    def _clean_profile_url(self, url: str) -> str:
        """
        Clean a profile URL to a standard format.
        
        Args:
            url: Profile URL to clean
            
        Returns:
            Cleaned profile URL
        """
        # Basic URL cleanup
        url = url.strip()
        
        # Ensure it's a LinkedIn profile URL
        if "linkedin.com/in/" not in url:
            raise ValueError(f"Not a valid LinkedIn profile URL: {url}")
        
        # Extract the base profile URL (remove query parameters, etc.)
        import re
        match = re.match(r'(https?://(?:www\.)?linkedin\.com/in/[^/]+).*', url)
        if match:
            return match.group(1)
        
        return url
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the batch processor.
        
        Returns:
            Dictionary with current status
        """
        return {
            "queue_stats": self.queue_manager.get_queue_stats(),
            "processing_active": self.processing_lock.locked(),
            "has_callback": self.session_callback is not None,
            "system_state": self.state_machine.get_current_state()
        }