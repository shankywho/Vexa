"""CFO-Bench evaluation and confidence calibration endpoints (spec sections 12.1, 17, 25, 26)."""

from __future__ import annotations

import logging
import uuid

import neatlogs
from fastapi import APIRouter, HTTPException, Query, status

from app.benchmarks.runner import CFOBenchRunner, benchmark_repository
from app.benchmarks.types import (
    BenchmarkRunSummary,
    ConfidenceCalibrationReport,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("", response_model=list[BenchmarkRunSummary])
async def list_benchmarks(
    limit: int = Query(default=20, le=100),
) -> list[BenchmarkRunSummary]:
    """List stored benchmark runs, newest first."""
    runs = benchmark_repository.list_all()
    if not runs:
        # Pre-compute initial benchmark so judges never encounter empty results (spec 25)
        runner = CFOBenchRunner()
        initial = await runner.run_benchmark()
        runs = [initial]
    return runs[:limit]


@router.post("/run", response_model=BenchmarkRunSummary, status_code=status.HTTP_201_CREATED)
@neatlogs.span(kind="WORKFLOW", name="run_benchmark")
async def run_benchmark() -> BenchmarkRunSummary:
    """Execute the full CFO-Bench suite across all 35 injected ground-truth scenarios."""
    runner = CFOBenchRunner()
    summary = await runner.run_benchmark()
    return summary


@router.get("/calibration", response_model=ConfidenceCalibrationReport)
async def get_calibration_report() -> ConfidenceCalibrationReport:
    """Retrieve the latest confidence calibration report with ECE and bucket breakdown (spec 12.1)."""
    latest = benchmark_repository.get_latest()
    if latest is None:
        runner = CFOBenchRunner()
        latest = await runner.run_benchmark()
    return latest.calibration_report


@router.get("/{id}", response_model=BenchmarkRunSummary)
async def get_benchmark(id: uuid.UUID) -> BenchmarkRunSummary:
    """Retrieve a specific benchmark run by ID with all scenario details."""
    run = benchmark_repository.get(id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark run not found")
    return run
