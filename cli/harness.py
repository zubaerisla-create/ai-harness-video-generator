#!/usr/bin/env python3
import sys
import os
import time
import json
import shutil
import argparse
import asyncio
from typing import Any
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.config import settings
from backend.app.database.session import AsyncSessionLocal, init_db
from backend.app.database.repository import JobRepository, VideoRepository
from backend.app.workers.queue import VideoPipelineOrchestrator

def print_header(title: str):
    print("=" * 65)
    print(f"  AI STORY VIDEO GENERATION HARNESS - {title}")
    print("=" * 65)

def print_row(key: str, value: Any):
    print(f"  {key:<26}: {value}")

async def cmd_generate(args):
    print_header("VIDEO GENERATION")
    prompt = args.prompt.strip()
    if not prompt:
        print("Error: Prompt cannot be empty.", file=sys.stderr)
        sys.exit(1)

    print_row("Prompt", prompt)
    print_row("Style", args.style)
    print_row("Target Duration", f"{args.duration}s")
    print_row("Resolution", args.resolution)
    print_row("Aspect Ratio", args.aspect_ratio)
    print_row("Visual Provider", settings.VISUAL_PROVIDER)
    print_row("TTS Provider", settings.TTS_PROVIDER)

    # Initialize DB schema
    await init_db()

    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        job = await job_repo.create_job({
            "prompt": prompt,
            "style": args.style,
            "requested_duration": args.duration,
            "requested_resolution": args.resolution,
            "aspect_ratio": args.aspect_ratio,
            "enable_narration": not args.no_narration,
            "enable_subtitles": not args.no_subtitles,
            "enable_bgm": not args.no_bgm,
            "status": "pending",
            "progress": 0,
            "stage": "queued"
        })
        job_id = job.id

    print_row("Job ID", job_id)
    print("-" * 65)
    print("Executing video generation pipeline...")

    orchestrator = VideoPipelineOrchestrator()
    success = await orchestrator.execute_job(job_id)

    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        job = await job_repo.get_job_by_id(job_id)
        if success and job and job.status == "completed":
            print("-" * 65)
            print("SUCCESS! Video generation complete.")
            if job.video:
                print_row("Video Title", job.video.title)
                print_row("Final Duration", f"{job.video.duration:.1f}s")
                print_row("Dimensions", f"{job.video.width}x{job.video.height} ({job.video.fps} fps)")
                print_row("File Size", f"{job.video.file_size / (1024*1024):.2f} MB")
                print_row("Output Path", job.video.file_path)
            if job.benchmark_data:
                bench = json.loads(job.benchmark_data)
                print("-" * 65)
                print("PERFORMANCE BENCHMARK METRICS:")
                print_row("Total Render Time", f"{bench.get('total_duration_seconds', 0)}s")
                for k, v in bench.get("timings", {}).items():
                    print_row(f"  - {k}", f"{v}s")
                print_row("Est. Daily Throughput", f"~{bench.get('estimated_daily_throughput', 0)} videos/day")
            sys.exit(0)
        else:
            err = job.error_message if job else "Unknown error"
            print(f"\nFAILURE: Job {job_id} failed: {err}", file=sys.stderr)
            sys.exit(1)

async def cmd_batch(args):
    print_header("BATCH VIDEO GENERATION")
    prompts_file = Path(args.prompts)
    if not prompts_file.exists():
        print(f"Error: Prompts file '{prompts_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    if not prompts:
        print("Error: No prompts found in file.", file=sys.stderr)
        sys.exit(1)

    total_to_run = min(args.count, len(prompts)) if args.count else len(prompts)
    selected_prompts = prompts[:total_to_run]
    print(f"Loaded {len(prompts)} prompts. Scheduling batch of {total_to_run} video(s)...")

    await init_db()
    orchestrator = VideoPipelineOrchestrator()
    completed_count = 0

    for idx, prompt in enumerate(selected_prompts, start=1):
        print(f"\n--- Batch Item {idx}/{total_to_run} ---")
        print_row("Prompt", prompt)
        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            job = await job_repo.create_job({
                "prompt": prompt,
                "style": args.style,
                "requested_duration": args.duration,
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

        ok = await orchestrator.execute_job(job_id)
        if ok:
            completed_count += 1
            print(f"Item {idx} Completed.")
        else:
            print(f"Item {idx} Failed. Continuing with batch...")

    print_header("BATCH SUMMARY")
    print_row("Total Processed", total_to_run)
    print_row("Successful", completed_count)
    print_row("Failed", total_to_run - completed_count)

async def cmd_status(args):
    print_header("JOB STATUS")
    await init_db()
    async with AsyncSessionLocal() as session:
        job_repo = JobRepository(session)
        job = await job_repo.get_job_by_id(args.job_id)
        if not job:
            print(f"Error: Job ID '{args.job_id}' not found.", file=sys.stderr)
            sys.exit(1)

        print_row("Job ID", job.id)
        print_row("Status", job.status.upper())
        print_row("Progress", f"{job.progress}%")
        print_row("Current Stage", job.stage)
        print_row("Prompt", job.prompt)
        print_row("Style", job.style)
        print_row("Created At", job.created_at)
        if job.completed_at:
            print_row("Completed At", job.completed_at)
        if job.error_message:
            print_row("Error", job.error_message)
        if job.video:
            print_row("Video File", job.video.file_path)

async def cmd_list(args):
    print_header("COMPLETED VIDEOS")
    await init_db()
    async with AsyncSessionLocal() as session:
        video_repo = VideoRepository(session)
        videos = await video_repo.list_videos(limit=args.limit)
        if not videos:
            print("  No videos generated yet.")
            return

        print(f"  {'ID':<10} {'TITLE':<32} {'DUR':<8} {'SIZE':<10} {'CREATED'}")
        print("  " + "-" * 62)
        for v in videos:
            size_mb = f"{v.file_size / (1024*1024):.1f} MB"
            created = v.created_at.strftime("%Y-%m-%d %H:%M")
            print(f"  {v.id[:8]:<10} {v.title[:30]:<32} {v.duration:<8.1f} {size_mb:<10} {created}")

async def cmd_delete(args):
    print_header("DELETE VIDEO")
    await init_db()
    async with AsyncSessionLocal() as session:
        video_repo = VideoRepository(session)
        v = await video_repo.get_video_by_id(args.video_id)
        if not v:
            print(f"Error: Video ID '{args.video_id}' not found.", file=sys.stderr)
            sys.exit(1)

        # Remove file
        try:
            fp = Path(v.file_path)
            if fp.exists():
                fp.unlink()
            if v.thumbnail_path and Path(v.thumbnail_path).exists():
                Path(v.thumbnail_path).unlink()
        except Exception as e:
            print(f"Warning deleting file: {e}")

        await video_repo.delete_video(args.video_id)
        print(f"Video '{args.video_id}' and associated files successfully deleted.")

async def cmd_stats(args):
    print_header("SYSTEM PERFORMANCE & STATS")
    await init_db()
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        from backend.app.models.database import VideoJob, Video
        
        total_vids = (await session.execute(select(func.count(Video.id)))).scalar_one() or 0
        completed = (await session.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "completed"))).scalar_one() or 0
        failed = (await session.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "failed"))).scalar_one() or 0
        pending = (await session.execute(select(func.count(VideoJob.id)).where(VideoJob.status == "pending"))).scalar_one() or 0
        avg_dur = (await session.execute(select(func.avg(Video.duration)))).scalar_one() or 0.0

        _, _, free = shutil.disk_usage(settings.OUTPUT_DIR)
        free_gb = free / (1024**3)

        print_row("Total Generated Videos", total_vids)
        print_row("Completed Jobs", completed)
        print_row("Failed Jobs", failed)
        print_row("Pending Jobs", pending)
        print_row("Avg Video Duration", f"{avg_dur:.1f}s")
        print_row("Free Storage", f"{free_gb:.1f} GB")
        est_daily = round(86400.0 / 180.0, 1) if completed == 0 else round(86400.0 / max(60.0, avg_dur), 1)
        print_row("Est. Daily Throughput", f"~{est_daily} videos/day")

async def cmd_doctor(args):
    print_header("SYSTEM DIAGNOSTICS & DOCTOR")
    import psutil
    import httpx

    # 1. OS & CPU
    print("1. HARDWARE & OPERATING SYSTEM:")
    print_row("  Platform", sys.platform)
    print_row("  CPU Cores", psutil.cpu_count(logical=True))
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    print_row("  Physical RAM", f"{mem.total / (1024**3):.2f} GB (Available: {mem.available / (1024**3):.2f} GB)")
    print_row("  Swap Space", f"{swap.total / (1024**3):.2f} GB (Used: {swap.used / (1024**3):.2f} GB)")
    total, used, free = shutil.disk_usage(settings.OUTPUT_DIR)
    print_row("  Output Disk Space", f"{free / (1024**3):.2f} GB free of {total / (1024**3):.2f} GB")

    # 2. Tools
    print("\n2. CLI & RENDERING TOOLS:")
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    print_row("  FFmpeg", ffmpeg_bin or "MISSING [FAIL]")
    print_row("  FFprobe", ffprobe_bin or "MISSING [FAIL]")

    # 3. AI Backends
    print("\n3. AI SERVICES & ENGINES:")
    # Ollama
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    print_row("  Ollama LLM", "ONLINE [OK]" if ollama_ok else "OFFLINE (Using rule-based fallback) [WARN]")

    # Piper TTS
    piper_model = Path(settings.PIPER_MODEL_PATH)
    print_row("  Piper Model", f"PRESENT ({piper_model.name})" if piper_model.exists() else "NOT FOUND [WARN]")

    # ComfyUI
    comfy_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.COMFYUI_URL}/system_stats")
            comfy_ok = r.status_code == 200
    except Exception:
        pass
    print_row("  ComfyUI Server", "ONLINE [OK]" if comfy_ok else "NOT DETECTED (Using Storyboard Canvas) [INFO]")
    print_row("  Configured Visuals", settings.VISUAL_PROVIDER)
    print("=" * 65)

async def cmd_autopilot(args):
    import random
    print_header(f"24/7 AUTONOMOUS AUTO-PILOT (TARGET: {args.target} VIDEOS/DAY)")
    await init_db()
    from backend.app.services.auto_pilot import CREATIVE_STORY_PROMPTS
    orchestrator = VideoPipelineOrchestrator()
    completed_today = 0

    print(f"  Target: {args.target} videos per 24 hours. Interval: {args.interval}s.")
    print("  Autonomous loop active. Press Ctrl+C at any time to stop.\n")

    while completed_today < args.target:
        style, prompt = random.choice(CREATIVE_STORY_PROMPTS)
        unique_prompt = f"{prompt} (Story #{completed_today + 1})"
        print("-" * 65)
        print(f"  [Auto-Pilot] Generating Video {completed_today + 1}/{args.target}")
        print(f"  Style : {style.upper()}")
        print(f"  Prompt: {unique_prompt}")

        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(session)
            job = await job_repo.create_job({
                "prompt": unique_prompt,
                "style": style,
                "requested_duration": args.duration,
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

        ok = await orchestrator.execute_job(job_id)
        if ok:
            completed_today += 1
            print(f"  [Success] Video {completed_today}/{args.target} created!")
        else:
            print(f"  [Warning] Video job encountered issue. Continuing...")

        if completed_today < args.target:
            print(f"  Waiting {args.interval}s before next video...")
            await asyncio.sleep(args.interval)

    print_header(f"DAILY TARGET ACHIEVED: {completed_today}/{args.target} VIDEOS GENERATED!")

def main():
    parser = argparse.ArgumentParser(description="AI Story Video Generation Harness CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen_p = subparsers.add_parser("generate", help="Generate a single video from prompt")
    gen_p.add_argument("--prompt", required=True, help="Story prompt")
    gen_p.add_argument("--duration", type=int, default=120, help="Duration in seconds (default: 120)")
    gen_p.add_argument("--style", default="anime", choices=["anime", "cartoon", "cinematic", "educational", "motivational"])
    gen_p.add_argument("--resolution", default="720p", choices=["720p", "1080p"])
    gen_p.add_argument("--aspect-ratio", default="9:16", choices=["9:16", "16:9", "1:1"])
    gen_p.add_argument("--no-narration", action="store_true", help="Disable audio narration")
    gen_p.add_argument("--no-subtitles", action="store_true", help="Disable burn-in subtitles")
    gen_p.add_argument("--no-bgm", action="store_true", help="Disable background music")

    # autopilot
    auto_p = subparsers.add_parser("autopilot", help="Run 24/7 continuous autonomous video generation")
    auto_p.add_argument("--target", type=int, default=25, help="Daily video target (default: 25)")
    auto_p.add_argument("--duration", type=int, default=120, help="Duration per video in seconds (default: 120)")
    auto_p.add_argument("--interval", type=int, default=30, help="Interval between videos in seconds (default: 30)")

    # batch
    batch_p = subparsers.add_parser("batch", help="Batch generate videos from a prompt file")
    batch_p.add_argument("--prompts", required=True, help="Path to prompts file")
    batch_p.add_argument("--duration", type=int, default=120)
    batch_p.add_argument("--style", default="anime")
    batch_p.add_argument("--count", type=int, default=20, help="Maximum number of prompts to process")

    # status
    stat_p = subparsers.add_parser("status", help="Check job status")
    stat_p.add_argument("job_id", help="Job ID")

    # list
    list_p = subparsers.add_parser("list", help="List completed videos")
    list_p.add_argument("--limit", type=int, default=20)

    # delete
    del_p = subparsers.add_parser("delete", help="Delete a video by ID")
    del_p.add_argument("video_id", help="Video ID")

    # stats
    subparsers.add_parser("stats", help="Show performance statistics")

    # doctor
    subparsers.add_parser("doctor", help="Run system diagnostics")

    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if args.command == "generate":
        loop.run_until_complete(cmd_generate(args))
    elif args.command == "autopilot":
        loop.run_until_complete(cmd_autopilot(args))
    elif args.command == "batch":
        loop.run_until_complete(cmd_batch(args))
    elif args.command == "status":
        loop.run_until_complete(cmd_status(args))
    elif args.command == "list":
        loop.run_until_complete(cmd_list(args))
    elif args.command == "delete":
        loop.run_until_complete(cmd_delete(args))
    elif args.command == "stats":
        loop.run_until_complete(cmd_stats(args))
    elif args.command == "doctor":
        loop.run_until_complete(cmd_doctor(args))

if __name__ == "__main__":
    main()
