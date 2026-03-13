"""Metrics API endpoints for monitoring and observability."""

from fastapi import APIRouter, Response
from typing import Dict, Any
from app.agents.metrics import (
    export_metrics,
    export_metrics_prometheus,
    get_metrics_collector,
    get_business_metrics,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/")
async def get_metrics() -> Dict[str, Any]:
    """Get all metrics in JSON format.
    
    Returns:
        Dictionary with performance and business metrics
    """
    return export_metrics()


@router.get("/prometheus")
async def get_metrics_prometheus() -> Response:
    """Get metrics in Prometheus format.
    
    Returns:
        Prometheus-formatted metrics
    """
    content = export_metrics_prometheus()
    return Response(content=content, media_type="text/plain")


@router.get("/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics summary.
    
    Returns:
        Performance metrics for all operations
    """
    collector = get_metrics_collector()
    return collector.get_summary()


@router.get("/performance/{operation}")
async def get_operation_metrics(operation: str) -> Dict[str, Any]:
    """Get performance metrics for a specific operation.
    
    Args:
        operation: Operation name
        
    Returns:
        Performance metrics for the operation
    """
    collector = get_metrics_collector()
    return collector.get_summary(operation)


@router.get("/business")
async def get_business_metrics_endpoint() -> Dict[str, int]:
    """Get business metrics.
    
    Returns:
        Business metric counters
    """
    metrics = get_business_metrics()
    return metrics.get_all()


@router.post("/reset")
async def reset_metrics() -> Dict[str, str]:
    """Reset all metrics.
    
    Returns:
        Success message
    """
    collector = get_metrics_collector()
    collector.reset()
    
    business = get_business_metrics()
    business.reset()
    
    return {"status": "success", "message": "All metrics reset"}


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint with basic metrics.
    
    Returns:
        Health status and basic metrics
    """
    metrics = export_metrics()
    
    # Calculate health score based on error rates
    perf = metrics.get("performance", {})
    total_errors = sum(
        stats.get("error_count", 0) 
        for stats in perf.values()
    )
    total_calls = sum(
        stats.get("count", 0) 
        for stats in perf.values()
    )
    
    error_rate = total_errors / total_calls if total_calls > 0 else 0
    health_status = "healthy" if error_rate < 0.05 else "degraded"
    
    return {
        "status": health_status,
        "error_rate": error_rate,
        "total_calls": total_calls,
        "total_errors": total_errors,
        "metrics_available": True
    }
