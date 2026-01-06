"""Scheduler shim for backward compatibility.

Re-exports PluginScheduler and related dataclasses/enums from plugins.scheduler
so existing imports (core.scheduler) continue to work.
"""

from plugins.scheduler import (
    PluginScheduler,
    ScheduleConfig,
    ExecutionRecord,
    ExecutionStatus,
)

__all__ = [
    "PluginScheduler",
    "ScheduleConfig",
    "ExecutionRecord",
    "ExecutionStatus",
]
