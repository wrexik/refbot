"""Advanced Plugin Scheduler - APScheduler integration with cron and retry logic"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Callable, Optional, List, Any
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Execution status enumeration"""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ExecutionRecord:
    """Record of a plugin execution"""
    plugin_name: str
    job_id: str
    status: ExecutionStatus
    start_time: datetime
    end_time: datetime
    duration_ms: float
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class ScheduleConfig:
    """Plugin schedule configuration"""
    job_id: str
    plugin_name: str
    cron_expression: str = "0 * * * *"  # Every hour
    max_retries: int = 3
    initial_retry_delay_seconds: int = 60
    backoff_multiplier: float = 2.0
    max_retry_delay_seconds: int = 3600


class PluginScheduler:
    """Advanced plugin scheduler with cron and retry support"""
    
    def __init__(self, max_history_size: int = 1000):
        """
        Initialize plugin scheduler
        
        Args:
            max_history_size: Maximum execution history records to keep
        """
        if not HAS_APSCHEDULER:
            logger.warning("APScheduler not installed, scheduling disabled")
            self.enabled = False
            return
        
        self.enabled = True
        self.scheduler = BackgroundScheduler()
        self.max_history_size = max_history_size
        self.execution_history: deque = deque(maxlen=max_history_size)
        self.jobs: Dict[str, Dict] = {}
        self.lock = threading.RLock()
        self.success_callbacks: List[Callable] = []
        self.failure_callbacks: List[Callable] = []
    
    def start(self) -> None:
        """Start the scheduler"""
        if not self.enabled:
            logger.warning("Scheduler not enabled")
            return
        
        try:
            self.scheduler.start()
            logger.info("Scheduler started")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def stop(self) -> None:
        """Stop the scheduler"""
        if not self.enabled:
            return
        
        try:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    def add_job(self, config: ScheduleConfig, func: Callable) -> bool:
        """
        Add a scheduled job
        
        Args:
            config: Schedule configuration
            func: Function to execute
            
        Returns:
            True if successful
        """
        if not self.enabled:
            logger.warning("Scheduler not enabled")
            return False
        
        try:
            with self.lock:
                # Create wrapper with retry logic
                wrapper = self._create_job_wrapper(config, func)
                
                # Add to scheduler
                trigger = CronTrigger.from_crontab(config.cron_expression)
                job = self.scheduler.add_job(
                    wrapper,
                    trigger=trigger,
                    id=config.job_id,
                    name=config.plugin_name,
                    max_instances=1
                )
                
                # Store job info
                self.jobs[config.job_id] = {
                    "plugin_name": config.plugin_name,
                    "cron_expression": config.cron_expression,
                    "config": config,
                    "added_at": datetime.now()
                }
                
                logger.info(f"Added job: {config.job_id} ({config.plugin_name})")
                return True
        
        except Exception as e:
            logger.error(f"Failed to add job {config.job_id}: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job
        
        Args:
            job_id: Job ID to remove
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            with self.lock:
                self.scheduler.remove_job(job_id)
                if job_id in self.jobs:
                    del self.jobs[job_id]
                logger.info(f"Removed job: {job_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False
    
    def get_active_jobs(self) -> List[Dict]:
        """
        Get list of active jobs
        
        Returns:
            List of active job information
        """
        with self.lock:
            return list(self.jobs.values())
    
    def _create_job_wrapper(self, config: ScheduleConfig, func: Callable) -> Callable:
        """
        Create a job wrapper with retry logic
        
        Args:
            config: Schedule configuration
            func: Original function
            
        Returns:
            Wrapped function with retry logic
        """
        def wrapper():
            retry_count = 0
            last_error = None
            
            while retry_count <= config.max_retries:
                start_time = datetime.now()
                
                try:
                    # Execute function
                    result = func()
                    
                    # Record success
                    end_time = datetime.now()
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    
                    record = ExecutionRecord(
                        plugin_name=config.plugin_name,
                        job_id=config.job_id,
                        status=ExecutionStatus.SUCCESS,
                        start_time=start_time,
                        end_time=end_time,
                        duration_ms=duration_ms,
                        result=result,
                        retry_count=retry_count
                    )
                    
                    self.execution_history.append(record)
                    
                    # Call success callbacks
                    for callback in self.success_callbacks:
                        try:
                            callback(record)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                    
                    return result
                
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Job {config.job_id} attempt {retry_count + 1} failed: {e}")
                    
                    if retry_count < config.max_retries:
                        # Calculate backoff delay
                        delay_seconds = min(
                            config.initial_retry_delay_seconds * (config.backoff_multiplier ** retry_count),
                            config.max_retry_delay_seconds
                        )
                        
                        logger.info(f"Retrying {config.job_id} in {delay_seconds}s...")
                        time.sleep(delay_seconds)
                        retry_count += 1
                    else:
                        break
            
            # Record failure
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            record = ExecutionRecord(
                plugin_name=config.plugin_name,
                job_id=config.job_id,
                status=ExecutionStatus.FAILED,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                error=last_error,
                retry_count=retry_count
            )
            
            self.execution_history.append(record)
            
            # Call failure callbacks
            for callback in self.failure_callbacks:
                try:
                    callback(record)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        return wrapper
    
    def register_success_callback(self, callback: Callable) -> None:
        """Register a success callback"""
        self.success_callbacks.append(callback)
    
    def register_failure_callback(self, callback: Callable) -> None:
        """Register a failure callback"""
        self.failure_callbacks.append(callback)
    
    def get_statistics(self, job_id: str) -> Optional[Dict]:
        """
        Get execution statistics for a job
        
        Args:
            job_id: Job ID
            
        Returns:
            Statistics dictionary
        """
        records = [r for r in self.execution_history if r.job_id == job_id]
        
        if not records:
            return None
        
        successful = sum(1 for r in records if r.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for r in records if r.status == ExecutionStatus.FAILED)
        total = len(records)
        
        durations = [r.duration_ms for r in records]
        
        return {
            "job_id": job_id,
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
            "last_execution": records[-1].end_time if records else None
        }
    
    def get_history(self, job_id: Optional[str] = None, limit: int = 100) -> List[ExecutionRecord]:
        """
        Get execution history
        
        Args:
            job_id: Filter by job ID (optional)
            limit: Maximum records to return
            
        Returns:
            List of execution records
        """
        records = list(self.execution_history)
        
        if job_id:
            records = [r for r in records if r.job_id == job_id]
        
        return records[-limit:]
