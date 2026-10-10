#!/usr/bin/env python3
import sys
import time
import json
import psutil
import asyncio
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.config import settings
from backend.app.database.session import init_db, AsyncSessionLocal
from backend.app.database.repository import JobRepository
from backend.app.workers.queue import VideoPipelineOrchestrator

async def run_benchmark(duration_sec: int = 30, style: str = "anime"):
    print("=" * 65)
    print(f"  AI STORY HARNESS - LIVE PIPELINE BENCHMARK")
    print(f"  Target Video Duration: {duration_sec}s | Style: {style}")
    print("=" * 65)

    await init_db()

    prompt = "A young student dreams of building software, overcomes adversity, and founds an AI lab."
    
    cpu_before = psutil.cpu_percent(interval=1.0)
    mem_before = psutil.virtual_memory().used / (1024 * 1024)

    t_start = time.time()

    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        job = await job_repo.create_job({
            "prompt": prompt,
            "style": style,
            "requested_duration": duration_sec,
            "requested_resolution": "720p",
            "aspect_ratio": "9:16",
            "enable_narration": True,
            "enable_subtitles": True,
            "enable_bgm": True,
            "status": "pending",
            "progress": 0,
            "stage": "queued"
        })
        job_id = job.id

    print(f"Created Benchmark Job ID: {job_id}")
    print("Executing complete video creation pipeline...")

    orchestrator = VideoPipelineOrchestrator()
    ok = await orchestrator.execute_job(job_id)

    t_end = time.time()
    total_time = round(t_end - t_start, 2)
    mem_after = psutil.virtual_memory().used / (1024 * 1024)
    cpu_after = psutil.cpu_percent(interval=1.0)

    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        job = await job_repo.get_job_by_id(job_id)

    if not ok or not job or job.status != "completed":
        print(f"Benchmark FAILED: {job.error_message if job else 'Unknown'}")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("  BENCHMARK RESULTS & THROUGHPUT ESTIMATION")
    print("=" * 65)
    print(f"  Job ID                    : {job_id}")
    print(f"  Total Pipeline Time       : {total_time} seconds")
    print(f"  Video Duration Rendered   : {job.video.duration}s")
    print(f"  Output Video Dimensions   : {job.video.width}x{job.video.height} @ {job.video.fps}fps")
    print(f"  Output File Size          : {job.video.file_size / (1024*1024):.2f} MB")
    print(f"  RAM Delta                 : {mem_after - mem_before:+.1f} MB (Peak RAM: {mem_after:.1f} MB)")
    print(f"  CPU Utilization (Sampled) : {cpu_after}%")

    if job.benchmark_data:
        bench = json.loads(job.benchmark_data)
        print("\n  STAGE TIMINGS BREAKDOWN:")
        for stage, dur in bench.get("timings", {}).items():
            pct = round((dur / total_time) * 100, 1)
            print(f"    - {stage:<26}: {dur:>6.2f}s ({pct:>4.1f}%)")

    # Estimate daily throughput for full 120s video:
    # Scale total_time to a 120s video if benchmark was shorter
    scaling_factor = 120.0 / max(1.0, float(duration_sec))
    projected_120s_time = total_time * scaling_factor
    projected_daily = round(86400.0 / projected_120s_time, 1)

    print("\n  PRODUCTION CAPACITY ANALYSIS:")
    print(f"    - Projected 120s Video Time : ~{round(projected_120s_time, 1)} seconds (~{round(projected_120s_time/60.0, 1)} minutes)")
    print(f"    - Projected Daily Capacity  : ~{projected_daily} videos / 24 hours")
    print(f"    - Daily Target (20-25 vids) : {'[MET WITH HEADROOM]' if projected_daily >= 25 else '[BELOW TARGET]'}")
    print("=" * 65)

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(run_benchmark(duration_sec=dur))
