import os
import json
import asyncio
import logging
import random
import zoneinfo
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import select, func

from backend.app.config import settings
from backend.app.database.session import AsyncSessionLocal
from backend.app.database.repository import JobRepository, DailyPublicationRepository
from backend.app.models.database import VideoJob
from backend.app.services.facebook_publisher import facebook_publisher

logger = logging.getLogger("ai_harness.auto_pilot")

# The 5 Core High-Engagement Pillars (No anime, cartoons, or childish fantasy)
# Optimized specifically for Facebook Reels & YouTube Shorts retention
PILLAR_TOPICS: Dict[str, List[Tuple[str, str]]] = {
    # Pillar 1: Business Strategies & Growth Moats
    "business_strategy": [
        ("The $40 Billion McDonald's Secret", "How McDonald's became the world's most profitable real estate empire while masquerading as a fast food burger chain."),
        ("The Costco 14% Profit Margin Moat", "Why Costco strictly refuses to make more than 14 percent profit on any item, and how that built an unbreakable retail monopoly."),
        ("Nvidia's Hidden CUDA Monopoly", "Why Big Tech cannot easily replace Nvidia GPUs: the multi-billion dollar software moat that rivals spent 15 years failing to copy."),
        ("Apple's Golden Handcuffs Strategy", "How iMessage blue bubbles, AirDrop, and cross-device locks engineered the stickiest behavioral retention loop in consumer history."),
        ("Red Bull Doesn't Manufacture Drinks", "How a tiny Austrian marketing firm outsourced beverage production and built a billion-dollar Formula 1 sports dynasty."),
        ("The Razor and Blade Pricing Formula", "The counter-intuitive psychology of selling hardware at a loss to extract 80 percent gross margin on recurring software and consumables."),
        ("Amazon AWS: The Secret Profit Engine", "How Amazon funded its brutal price wars in global retail using enterprise cloud infrastructure profits from AWS."),
        ("Spotify's Algorithmic Habit Loop", "How Spotify transformed music streaming into behavioral addiction through Discover Weekly and predictive audio clustering."),
        ("LVMH and the Luxury Paradox", "Why Bernard Arnault deliberately limits product supply to make luxury consumers pay 1,000 percent markups for exclusivity."),
        ("The Gillette & Dollar Shave Club War", "How a viral 90-second YouTube video challenged a century-old Procter and Gamble monopoly and sold for a billion dollars.")
    ],

    # Pillar 2: Current AI News & Breakthroughs
    "ai_news": [
        ("Humanoid Robots Entering Automobile Factories", "How next-generation humanoid robotics like Figure 02 and Optimus are transitioning from lab demos to autonomous 24/7 assembly lines."),
        ("Autonomous AI Agent Swarms in Production", "How multi-agent AI architectures are writing, debugging, testing, and deploying enterprise software without human intervention."),
        ("The AI Memory Bandwidth Bottleneck", "Why the global chip war has shifted from compute teraflops to High Bandwidth Memory and silicon photonics interconnects."),
        ("Next-Gen Reasoning LLMs and Test-Time Compute", "How AI architectures learned deliberate System-2 thinking, verification, and solving unsolved university mathematics."),
        ("AI Drug Discovery Breaking Records", "How generative molecular models mapped novel cancer-binding compounds in 48 hours instead of a decade of lab trials."),
        ("Synthetic Media & Photorealistic Video Models", "How diffusion transformer models achieved temporal physics coherence, transforming the multi-billion dollar VFX industry."),
        ("Open-Weight LLMs Closing the Frontier Gap", "How localized, highly quantized models running on consumer hardware are rivaling trillion-parameter cloud models."),
        ("Brain-Computer Interfaces Decoding Inner Monologue", "Clinical trials where neural implants translate non-vocalized thought signals into real-time speech at 95 percent accuracy.")
    ],

    # Pillar 3: Science Fiction Concepts Made Real
    "sci_fi_concept": [
        ("Dyson Swarms and Stellar Engineering", "Could humanity construct an orbital swarm of solar collectors around the Sun to harvest 100 percent of stellar radiation?"),
        ("Antimatter Propulsion for Interstellar Travel", "Why a single gram of antimatter possesses the explosive kinetic energy to propel exploratory probes to Proxima Centauri."),
        ("The Kardashev Scale: Where Earth Really Ranks", "From harnessing planetary weather to manipulating entire galactic superclusters: calculating humanity's exact cosmic energy rank."),
        ("Carbon Nanotube Space Elevators", "The physics of tethering orbital counterweights to ocean platforms to reduce space launch costs from thousands to ten dollars per kilogram."),
        ("Terraforming Mars with Artificial Magnetic Shields", "Deploying a 2-Tesla superconducting magnetic dipole at Lagrange Point L1 to rebuild the Martian atmosphere and atmospheric pressure."),
        ("Wormholes and the Alcubierre Warp Metric", "How negative energy density solutions in Einstein's field equations theoretically allow faster-than-light space-time contraction."),
        ("Cryonic Neuropreservation and Cellular Vitrification", "The biological engineering hurdles behind freezing human organs without ice crystal destruction for 22nd-century reanimation.")
    ],

    # Pillar 4: Emerging Technologies
    "emerging_tech": [
        ("Solid-State Batteries Ending Combustion Engines", "How ceramic electrolytes with lithium metal anodes unlock 1,000-kilometer vehicle range with 10-minute fast charging."),
        ("Net-Gain Magnetic Fusion Milestones", "How high-temperature superconducting magnets are trapping 100-million-degree plasma to deliver limitless clean baseline power."),
        ("CRISPR 3.0 Prime & Epigenetic Editing", "The genetic tools curing hereditary disorders in living humans by rewriting DNA nucleotides without double-strand breaks."),
        ("Neuromorphic Brain-Inspired Microchips", "Processors engineered with physical spiking synapses that compute sensory data using milliwatts rather than megawatts."),
        ("eVTOL Autonomous Air Mobility", "How electric vertical takeoff aircraft are clearing FAA and EASA certifications to revolutionize city-to-airport transit."),
        ("Synthetic Biology Growing Super-Materials", "Culturing spider silk fibers and carbon-negative concrete inside bioreactors with higher tensile strength than titanium alloy."),
        ("Quantum Key Distribution Satellites", "How space-based quantum entanglement creates communication channels that are mathematically immune to interception.")
    ],

    # Pillar 5: Predictions About The Future (2030-2050)
    "future_predictions": [
        ("What Daily Life Looks Like in 2035", "From autonomous electric transport to ambient AI sensory assistants: mapping out an ordinary Tuesday a decade into our future."),
        ("The Post-Labor Economic Transition", "What happens when artificial general intelligence and robotics outproduce human labor in manufacturing, law, and creative design?"),
        ("Longevity Escape Velocity and The 140-Year Lifespan", "Will the first person to live to 150 years old be someone who is already alive today? The biology of cellular senescence."),
        ("Smart Cities with Decentralized Microgrids", "How self-healing urban grids, rooftop biophilic agriculture, and kinetic walkways will redefine 2040 metropolitan infrastructure."),
        ("The First Permanent Human Colony on Mars", "Living underground in Martian volcanic lava tubes to escape cosmic radiation: the engineering realities of 2040 off-world colonies."),
        ("Planetary Geoengineering and Solar Radiation Dimming", "Can releasing stratospheric aerosol particles buy humanity 20 years to reverse global warming trends?"),
        ("The Convergence of Quantum Computing and AI", "What happens when quantum processors simulate molecular physics to design room-temperature superconductors in real-time?")
    ]
}

HISTORY_FILE = settings.DATA_DIR / "autopilot_topic_history.json"

class AutoPilotService:
    """
    Autonomous AI Content Automation & Facebook Publishing Agent.
    Strictly manages 5 daily publication slots with >= 2 hours between slots in Asia/Dhaka.
    Ensures advance rendering, idempotency, restart-safety, and persistent daily quota tracking.
    """

    def __init__(self):
        self.enabled: bool = settings.AUTOPILOT_ENABLED
        self.daily_target: int = settings.MAX_DAILY_PUBLISHED_VIDEOS  # Strictly 5 videos per day
        self.timezone_name: str = settings.TIMEZONE
        self.publish_slots: List[str] = list(settings.DAILY_PUBLISH_SLOTS)
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._pillars = list(PILLAR_TOPICS.keys())
        self._pillar_index = 0
        self._last_retry_check: float = 0.0

    def get_tz(self) -> zoneinfo.ZoneInfo:
        return zoneinfo.ZoneInfo(self.timezone_name)

    def get_local_now(self) -> datetime:
        return datetime.now(self.get_tz())

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._pilot_loop())
        logger.info(
            f"Auto-Pilot Autonomous Facebook Agent active "
            f"(Timezone: {self.timezone_name}, Slots: {self.publish_slots}, Daily Target: {self.daily_target})"
        )

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Auto-Pilot Autonomous Facebook Agent stopped.")

    def set_config(self, enabled: bool, target: int = 5, slots: Optional[List[str]] = None):
        self.enabled = enabled
        self.daily_target = max(1, min(10, target))
        if slots:
            self.publish_slots = slots
        logger.info(f"Auto-Pilot config updated: enabled={self.enabled}, daily_target={self.daily_target}, slots={self.publish_slots}")

    async def get_status(self) -> Dict[str, Any]:
        local_now = self.get_local_now()
        local_date_str = local_now.strftime("%Y-%m-%d")

        async with AsyncSessionLocal() as session:
            daily_repo = DailyPublicationRepository(session)
            job_repo = JobRepository(session)

            daily_rec = await daily_repo.get_or_create_daily(local_date_str, self.timezone_name)
            published_count = daily_rec.published_count
            fulfilled_slots = json.loads(daily_rec.slots_fulfilled or "[]")
            ready_job = await job_repo.get_ready_job_for_slot()
            active_jobs = await job_repo.get_running_jobs_count()

        # Slot matrix
        slot_status_list = []
        next_slot = None
        for s in self.publish_slots:
            is_fulfilled = s in fulfilled_slots
            # Parse slot time
            sh, sm = map(int, s.split(":"))
            slot_dt = local_now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            
            if is_fulfilled:
                status_label = "published"
            elif local_now < slot_dt:
                status_label = "upcoming"
                if next_slot is None:
                    next_slot = s
            elif local_now >= slot_dt and (local_now - slot_dt) < timedelta(hours=2):
                status_label = "due_now"
                if next_slot is None:
                    next_slot = s
            else:
                status_label = "passed_unfulfilled"

            slot_status_list.append({
                "slot": s,
                "status": status_label,
                "fulfilled": is_fulfilled
            })

        return {
            "enabled": self.enabled,
            "timezone": self.timezone_name,
            "local_time": local_now.strftime("%Y-%m-%d %H:%M:%S"),
            "local_date": local_date_str,
            "daily_target": self.daily_target,
            "published_today": published_count,
            "quota_remaining": max(0, self.daily_target - published_count),
            "quota_met": published_count >= self.daily_target,
            "next_slot": next_slot,
            "slots": slot_status_list,
            "has_ready_video": ready_job is not None,
            "active_pipeline_jobs": active_jobs,
            "dry_run": settings.DRY_RUN,
            "pillars_active": self._pillars
        }

    async def _pilot_loop(self):
        # Brief startup grace period
        await asyncio.sleep(4.0)

        while self._running:
            try:
                if self.enabled:
                    await self._check_and_orchestrate()
            except Exception as e:
                logger.error(f"Auto-Pilot loop exception: {e}", exc_info=True)

            # Check every 45 seconds for precision slot publishing
            await asyncio.sleep(45.0)

    async def _check_and_orchestrate(self):
        """Main scheduling and publishing evaluation cycle."""
        local_now = self.get_local_now()
        local_date_str = local_now.strftime("%Y-%m-%d")

        async with AsyncSessionLocal() as session:
            daily_repo = DailyPublicationRepository(session)
            job_repo = JobRepository(session)

            daily_rec = await daily_repo.get_or_create_daily(local_date_str, self.timezone_name)
            published_count = daily_rec.published_count
            fulfilled_slots = json.loads(daily_rec.slots_fulfilled or "[]")

            # Strict Invariant: Never publish more than daily_target (5) videos per local day
            if published_count >= self.daily_target:
                return

            from backend.app.workers.queue import worker_service

            # --------------------------------------------------------
            # STEP 1: Process Transient Retries (if any)
            # --------------------------------------------------------
            retry_jobs = await job_repo.get_retryable_upload_jobs()
            for r_job in retry_jobs:
                if published_count >= self.daily_target:
                    break
                # Only retry if at least 5 minutes since last attempt
                if r_job.completed_at and (datetime.utcnow() - r_job.completed_at).total_seconds() < 300:
                    continue
                logger.info(f"[Auto-Pilot] Retrying upload for Job {r_job.id} (Attempt {r_job.upload_attempts + 1})")
                success = await worker_service.orchestrator.publish_job(r_job.id)
                if success:
                    published_count += 1
                    return  # Yield turn after action

            # --------------------------------------------------------
            # STEP 2: Evaluate Scheduled Publishing Slots Due Right Now
            # --------------------------------------------------------
            for slot_str in self.publish_slots:
                if published_count >= self.daily_target:
                    break
                if slot_str in fulfilled_slots:
                    continue

                sh, sm = map(int, slot_str.split(":"))
                slot_dt = local_now.replace(hour=sh, minute=sm, second=0, microsecond=0)

                # Is this slot due now? (Between slot_dt and slot_dt + 2 hours)
                if slot_dt <= local_now < (slot_dt + timedelta(hours=2)):
                    logger.info(f"[Auto-Pilot] Publishing Slot '{slot_str}' is DUE NOW (Local time: {local_now.strftime('%H:%M:%S')})")
                    
                    ready_job = await job_repo.get_ready_job_for_slot()
                    if ready_job:
                        logger.info(f"[Auto-Pilot] Publishing ready video Job {ready_job.id} for Slot '{slot_str}'")
                        pub_ok = await worker_service.orchestrator.publish_job(ready_job.id, slot=slot_str)
                        if pub_ok:
                            published_count += 1
                        return
                    else:
                        # No video is ready for this due slot. Check if one is generating
                        active_count = await job_repo.get_running_jobs_count()
                        pending_job = await job_repo.get_next_pending_job()
                        if active_count == 0 and not pending_job:
                            logger.warning(f"[Auto-Pilot] No ready video for due slot '{slot_str}'. Triggering immediate generation.")
                            await self._schedule_advance_video(job_repo, target_slot_dt=slot_dt)
                            return

            # --------------------------------------------------------
            # STEP 3: Advance Preparation (Render in Advance Before Slot)
            # --------------------------------------------------------
            # Find the next upcoming unfulfilled slot today
            upcoming_slot = None
            upcoming_slot_dt = None
            for slot_str in self.publish_slots:
                if slot_str in fulfilled_slots:
                    continue
                sh, sm = map(int, slot_str.split(":"))
                s_dt = local_now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                if s_dt > local_now:
                    upcoming_slot = slot_str
                    upcoming_slot_dt = s_dt
                    break

            if upcoming_slot and upcoming_slot_dt:
                # How much time until this upcoming slot?
                diff_minutes = (upcoming_slot_dt - local_now).total_seconds() / 60.0
                
                # Check if we should render in advance (within advance window or queue empty)
                ready_job = await job_repo.get_ready_job_for_slot()
                active_count = await job_repo.get_running_jobs_count()
                pending_job = await job_repo.get_next_pending_job()

                if not ready_job and active_count == 0 and not pending_job:
                    # If within configured advance render window or under daily quota
                    if diff_minutes <= settings.ADVANCE_RENDER_MINUTES or diff_minutes <= 180:
                        logger.info(
                            f"[Auto-Pilot] Pre-rendering video in advance for Slot '{upcoming_slot}' "
                            f"(Due in {int(diff_minutes)} mins at {upcoming_slot_dt.strftime('%H:%M')})"
                        )
                        await self._schedule_advance_video(job_repo, target_slot_dt=upcoming_slot_dt)

    async def _schedule_advance_video(self, job_repo: JobRepository, target_slot_dt: Optional[datetime] = None):
        """Generates a unique story topic and creates a pending pipeline job."""
        style, prompt, sources = await self._pick_next_unique_topic()
        
        import uuid
        content_id = f"doc_{style}_{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"
        logger.info(f"[Auto-Pilot] Created advance content plan [{content_id}] '{prompt}'")

        await job_repo.create_job({
            "prompt": prompt,
            "style": style,
            "requested_duration": 45,
            "requested_resolution": "720p",
            "aspect_ratio": "9:16",
            "enable_narration": True,
            "enable_subtitles": True,
            "enable_bgm": True,
            "status": "pending",
            "progress": 0,
            "stage": "queued",
            "content_id": content_id,
            "scheduled_publish_time": target_slot_dt.replace(tzinfo=None) if target_slot_dt else None,
            "sources_used": json.dumps(sources) if sources else "[]"
        })

    def _load_history(self) -> List[str]:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_history(self, title: str):
        history = self._load_history()
        history.append(title)
        if len(history) > 500:
            history = history[-500:]
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record topic history: {e}")

    async def _pick_next_unique_topic(self) -> Tuple[str, str, List[str]]:
        history = set(self._load_history())

        # Select pillar in cyclic order to guarantee diversity
        pillar = self._pillars[self._pillar_index % len(self._pillars)]
        self._pillar_index += 1

        sources = []

        # 1. Fetch live real-time breaking news for this category from OnlineResearcher
        try:
            from backend.app.services.online_researcher import online_researcher
            trending = await online_researcher.get_trending_topics(pillar, limit=6)
            for title, desc, meta in trending:
                clean_title = title.strip()
                if clean_title not in history and len(clean_title) > 12:
                    self._save_history(clean_title)
                    link = meta.get("link")
                    if link:
                        sources.append(link)
                    logger.info(f"[Auto-Pilot] Selected live trending news topic: '{clean_title}' ({meta.get('publisher')})")
                    return pillar, f"{clean_title}: {desc}", sources
        except Exception as e:
            logger.warning(f"[Auto-Pilot] Live news discovery fallback: {e}")

        # 2. Curated topic fallback if offline or no new news found
        topic_candidates = PILLAR_TOPICS.get(pillar, PILLAR_TOPICS["business_strategy"])
        unused = [(t, d) for t, d in topic_candidates if t not in history]
        if not unused:
            unused = topic_candidates

        title, description = random.choice(unused)
        self._save_history(title)

        full_prompt = f"{title}: {description}"
        return pillar, full_prompt, sources

auto_pilot = AutoPilotService()
