# services/queue_manager.py
"""
Queue manager for LinkedIn profile scraping.
"""

import json
import os
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.scraper_config import PROFILE_QUEUE_PATH, EVENTS
from utils.event_bus import EventBus

logger = logging.getLogger(__name__)

class QueueManager:
    """
    Manages the queue of LinkedIn profiles to be scraped.
    
    Provides FIFO queue operations with support for priority and status tracking.
    """
    
    def __init__(self, queue_file_path: str = PROFILE_QUEUE_PATH):
        """
        Initialize the queue manager.
        
        Args:
            queue_file_path: Path to the queue file
        """
        self.queue_file_path = queue_file_path
        self.lock = threading.Lock()
        self.event_bus = EventBus.get_instance()
        
        # Initialize the queue file if it doesn't exist
        if not os.path.exists(queue_file_path):
            self._write_queue([])
    
    def _read_queue(self) -> List[Dict[str, Any]]:
        """
        Read the profile queue from file.
        
        Returns:
            List of profile entries
        """
        try:
            with open(self.queue_file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Queue file at {self.queue_file_path} not found or invalid. Creating new queue.")
            return []
    
    def _write_queue(self, queue: List[Dict[str, Any]]) -> None:
        """
        Write the profile queue to file.
        
        Args:
            queue: List of profile entries to write
        """
        os.makedirs(os.path.dirname(self.queue_file_path), exist_ok=True)
        with open(self.queue_file_path, 'w') as f:
            json.dump(queue, f, indent=2)
    
    def add_profile(self, url: str, urgent: bool = False, initiator: str = "") -> bool:
        """
        Add a profile to the queue.
        
        Args:
            url: LinkedIn profile URL
            urgent: Whether this is an urgent request
            initiator: Who/what initiated this request
            
        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            queue = self._read_queue()
            
            # Check if profile is already in queue
            for entry in queue:
                if entry["url"] == url:
                    if entry["done"]:
                        # If already processed, update it to be reprocessed
                        entry["done"] = False
                        entry["urgent"] = urgent or entry["urgent"]
                        entry["initiator"] = initiator or entry["initiator"]
                        entry["updated_at"] = datetime.now().isoformat()
                        logger.info(f"Profile {url} already in queue but marked for reprocessing")
                    else:
                        # If already in queue but not processed, update priority if needed
                        if urgent and not entry["urgent"]:
                            entry["urgent"] = True
                            entry["updated_at"] = datetime.now().isoformat()
                            logger.info(f"Updated profile {url} to urgent priority")
                        else:
                            logger.info(f"Profile {url} already in queue")
                    
                    self._write_queue(queue)
                    self.event_bus.publish(EVENTS["QUEUE_UPDATED"], {"action": "updated", "url": url})
                    return True
            
            # If not in queue, add it
            queue.append({
                "url": url,
                "done": False,
                "urgent": urgent,
                "initiator": initiator,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "status": "queued"
            })
            
            self._write_queue(queue)
            logger.info(f"Added profile {url} to queue")
            self.event_bus.publish(EVENTS["QUEUE_UPDATED"], {"action": "added", "url": url})
            return True
    
    def get_next_profiles(self, count: int = 1, include_done: bool = False) -> List[Dict[str, Any]]:
        """
        Get the next profiles from the queue.
        
        Args:
            count: Number of profiles to get
            include_done: Whether to include completed profiles
            
        Returns:
            List of profile entries
        """
        with self.lock:
            queue = self._read_queue()
            
            # Filter and sort queue
            filtered_queue = [entry for entry in queue if include_done or not entry["done"]]
            
            # Sort by urgency (urgent first) and then by creation time (oldest first)
            sorted_queue = sorted(filtered_queue, 
                                  key=lambda x: (not x["urgent"], x["created_at"]))
            
            return sorted_queue[:count]
    
    def mark_profile_status(self, url: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark a profile's status in the queue.
        
        Args:
            url: Profile URL
            status: New status (e.g., 'in_progress', 'completed', 'failed')
            metadata: Optional metadata to store with the status update
            
        Returns:
            True if updated successfully, False otherwise
        """
        with self.lock:
            queue = self._read_queue()
            
            for entry in queue:
                if entry["url"] == url:
                    entry["status"] = status
                    entry["updated_at"] = datetime.now().isoformat()
                    
                    if status == "completed":
                        entry["done"] = True
                    
                    if metadata:
                        if "metadata" not in entry:
                            entry["metadata"] = {}
                        entry["metadata"].update(metadata)
                    
                    self._write_queue(queue)
                    
                    event_type = (EVENTS["PROFILE_SCRAPED"] if status == "completed" 
                                 else EVENTS["PROFILE_FAILED"] if status == "failed"
                                 else EVENTS["QUEUE_UPDATED"])
                    
                    self.event_bus.publish(event_type, {
                        "url": url, 
                        "status": status,
                        "metadata": metadata
                    })
                    
                    logger.info(f"Updated profile {url} status to {status}")
                    return True
            
            logger.warning(f"Profile {url} not found in queue")
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the queue.
        
        Returns:
            Dictionary with queue statistics
        """
        with self.lock:
            queue = self._read_queue()
            
            total = len(queue)
            pending = sum(1 for entry in queue if not entry["done"])
            completed = sum(1 for entry in queue if entry["done"])
            urgent = sum(1 for entry in queue if entry["urgent"] and not entry["done"])
            
            # Count by status
            status_counts = {}
            for entry in queue:
                status = entry.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total": total,
                "pending": pending,
                "completed": completed,
                "urgent": urgent,
                "status_counts": status_counts,
                "last_updated": datetime.now().isoformat()
            }
    
    def clear_queue(self) -> bool:
        """
        Clear the entire queue.
        
        Returns:
            True if cleared successfully
        """
        with self.lock:
            self._write_queue([])
            logger.info("Queue cleared")
            self.event_bus.publish(EVENTS["QUEUE_UPDATED"], {"action": "cleared"})
            return True