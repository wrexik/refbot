"""Proxy Scoring System - Intelligent proxy ranking and load balancing"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    WEIGHTED = "weighted"
    RANDOM = "random"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Working normally
    OPEN = "open"      # Broken, not accepting requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class ProxyScore:
    """Proxy score data"""
    proxy_url: str
    overall_score: float
    success_rate_score: float
    speed_score: float
    reliability_score: float
    circuit_state: CircuitState


class ProxyScorer:
    """Advanced proxy scoring and load balancing system"""
    
    def __init__(self, reference_speed_ms: float = 200,
                 success_weight: float = 0.4,
                 speed_weight: float = 0.3,
                 reliability_weight: float = 0.3,
                 failure_threshold: int = 5,
                 recovery_threshold: int = 2):
        """
        Initialize proxy scorer
        
        Args:
            reference_speed_ms: Reference speed for scoring
            success_weight: Weight for success rate (0-1)
            speed_weight: Weight for speed (0-1)
            reliability_weight: Weight for reliability (0-1)
            failure_threshold: Consecutive failures to open circuit
            recovery_threshold: Successes needed to close circuit
        """
        self.reference_speed_ms = reference_speed_ms
        self.success_weight = success_weight
        self.speed_weight = speed_weight
        self.reliability_weight = reliability_weight
        self.failure_threshold = failure_threshold
        self.recovery_threshold = recovery_threshold
        
        self.proxy_metrics: Dict[str, Dict] = {}
        self.round_robin_index = 0
    
    def record_request(self, proxy_url: str, response_time_ms: float, success: bool) -> None:
        """
        Record a proxy request
        
        Args:
            proxy_url: Proxy URL
            response_time_ms: Response time in milliseconds
            success: Whether request succeeded
        """
        if proxy_url not in self.proxy_metrics:
            self.proxy_metrics[proxy_url] = {
                "total_requests": 0,
                "success_count": 0,
                "failure_count": 0,
                "consecutive_failures": 0,
                "consecutive_successes": 0,
                "response_times": [],
                "circuit_state": CircuitState.CLOSED,
                "last_failure_time": None
            }
        
        metrics = self.proxy_metrics[proxy_url]
        metrics["total_requests"] += 1
        
        if success:
            metrics["success_count"] += 1
            metrics["consecutive_failures"] = 0
            metrics["consecutive_successes"] += 1
            
            # Check if should close circuit
            if metrics["circuit_state"] == CircuitState.HALF_OPEN:
                if metrics["consecutive_successes"] >= self.recovery_threshold:
                    metrics["circuit_state"] = CircuitState.CLOSED
                    logger.info(f"Circuit CLOSED for {proxy_url}")
        else:
            metrics["failure_count"] += 1
            metrics["consecutive_failures"] += 1
            metrics["consecutive_successes"] = 0
            metrics["last_failure_time"] = __import__('datetime').datetime.now()
            
            # Check if should open circuit
            if metrics["circuit_state"] == CircuitState.CLOSED:
                if metrics["consecutive_failures"] >= self.failure_threshold:
                    metrics["circuit_state"] = CircuitState.OPEN
                    logger.warning(f"Circuit OPEN for {proxy_url} (failures: {metrics['consecutive_failures']})")
            
            elif metrics["circuit_state"] == CircuitState.OPEN:
                # Try to recover
                metrics["circuit_state"] = CircuitState.HALF_OPEN
                metrics["consecutive_failures"] = 0
                logger.info(f"Circuit HALF_OPEN for {proxy_url}")
        
        # Track response times
        if len(metrics["response_times"]) >= 1000:
            metrics["response_times"] = metrics["response_times"][-500:]
        metrics["response_times"].append(response_time_ms)
    
    def _calculate_score(self, proxy_url: str) -> ProxyScore:
        """
        Calculate overall score for a proxy
        
        Args:
            proxy_url: Proxy URL
            
        Returns:
            ProxyScore object
        """
        if proxy_url not in self.proxy_metrics:
            return ProxyScore(
                proxy_url=proxy_url,
                overall_score=0,
                success_rate_score=0,
                speed_score=0,
                reliability_score=0,
                circuit_state=CircuitState.CLOSED
            )
        
        metrics = self.proxy_metrics[proxy_url]
        
        # Success rate score (0-100)
        if metrics["total_requests"] == 0:
            success_rate_score = 50.0
        else:
            success_rate = metrics["success_count"] / metrics["total_requests"]
            success_rate_score = success_rate * 100
        
        # Speed score (0-100)
        if not metrics["response_times"]:
            speed_score = 50.0
        else:
            avg_response_time = statistics.mean(metrics["response_times"])
            # Score: lower response time = higher score
            speed_score = max(0, 100 - (avg_response_time / self.reference_speed_ms) * 100)
        
        # Reliability score (0-100)
        if metrics["total_requests"] < 10:
            reliability_score = 50.0
        else:
            # Based on consistency of response times
            if len(metrics["response_times"]) > 1:
                stdev = statistics.stdev(metrics["response_times"])
                mean = statistics.mean(metrics["response_times"])
                cv = (stdev / mean) if mean > 0 else 0  # Coefficient of variation
                reliability_score = max(0, 100 - (cv * 100))
            else:
                reliability_score = 50.0
        
        # Overall score
        overall_score = (
            success_rate_score * self.success_weight +
            speed_score * self.speed_weight +
            reliability_score * self.reliability_weight
        )
        
        # Penalize for open circuit
        if metrics["circuit_state"] == CircuitState.OPEN:
            overall_score *= 0.3
        
        return ProxyScore(
            proxy_url=proxy_url,
            overall_score=overall_score,
            success_rate_score=success_rate_score,
            speed_score=speed_score,
            reliability_score=reliability_score,
            circuit_state=metrics["circuit_state"]
        )
    
    def get_sorted_proxies(self, limit: Optional[int] = None) -> List[ProxyScore]:
        """
        Get proxies sorted by overall score
        
        Args:
            limit: Maximum number to return
            
        Returns:
            Sorted list of proxies
        """
        scores = [self._calculate_score(proxy) for proxy in self.proxy_metrics.keys()]
        scores.sort(key=lambda x: x.overall_score, reverse=True)
        
        if limit:
            scores = scores[:limit]
        
        return scores
    
    def get_next_proxy(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.WEIGHTED) -> Optional[str]:
        """
        Get next proxy based on load balancing strategy
        
        Args:
            strategy: Load balancing strategy
            
        Returns:
            Proxy URL or None
        """
        if not self.proxy_metrics:
            return None
        
        healthy_proxies = [
            p for p in self.proxy_metrics.keys()
            if self.proxy_metrics[p]["circuit_state"] != CircuitState.OPEN
        ]
        
        if not healthy_proxies:
            logger.warning("No healthy proxies available")
            return None
        
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            proxy = healthy_proxies[self.round_robin_index % len(healthy_proxies)]
            self.round_robin_index += 1
            return proxy
        
        elif strategy == LoadBalancingStrategy.LEAST_LOADED:
            # Use proxy with least total requests
            return min(healthy_proxies, key=lambda p: self.proxy_metrics[p]["total_requests"])
        
        elif strategy == LoadBalancingStrategy.WEIGHTED:
            # Use proxy with best score
            best_score = -1
            best_proxy = None
            
            for proxy in healthy_proxies:
                score = self._calculate_score(proxy).overall_score
                if score > best_score:
                    best_score = score
                    best_proxy = proxy
            
            return best_proxy
        
        elif strategy == LoadBalancingStrategy.RANDOM:
            import random
            return random.choice(healthy_proxies)
        
        return None
    
    def get_failover_chain(self, primary_proxy: str, chain_size: int = 3) -> List[str]:
        """
        Get failover chain for a proxy
        
        Args:
            primary_proxy: Primary proxy URL
            chain_size: Size of failover chain
            
        Returns:
            List of proxies ordered by score
        """
        sorted_proxies = self.get_sorted_proxies()
        
        # Filter out the primary proxy and get top alternatives
        alternatives = [p.proxy_url for p in sorted_proxies if p.proxy_url != primary_proxy]
        
        # Return chain starting with primary
        return [primary_proxy] + alternatives[:chain_size-1]
    
    def is_proxy_healthy(self, proxy_url: str) -> bool:
        """
        Check if proxy is healthy
        
        Args:
            proxy_url: Proxy URL
            
        Returns:
            True if healthy
        """
        if proxy_url not in self.proxy_metrics:
            return True  # Unknown proxy assumed healthy
        
        state = self.proxy_metrics[proxy_url]["circuit_state"]
        return state != CircuitState.OPEN
    
    def get_metrics(self, proxy_url: str) -> Optional[Dict]:
        """
        Get detailed metrics for a proxy
        
        Args:
            proxy_url: Proxy URL
            
        Returns:
            Metrics dictionary
        """
        if proxy_url not in self.proxy_metrics:
            return None
        
        metrics = self.proxy_metrics[proxy_url]
        
        return {
            "proxy_url": proxy_url,
            "total_requests": metrics["total_requests"],
            "success_count": metrics["success_count"],
            "failure_count": metrics["failure_count"],
            "success_rate": (metrics["success_count"] / metrics["total_requests"]
                           if metrics["total_requests"] > 0 else 0),
            "avg_response_time_ms": (statistics.mean(metrics["response_times"])
                                    if metrics["response_times"] else 0),
            "min_response_time_ms": (min(metrics["response_times"])
                                    if metrics["response_times"] else 0),
            "max_response_time_ms": (max(metrics["response_times"])
                                    if metrics["response_times"] else 0),
            "circuit_state": metrics["circuit_state"].value
        }
