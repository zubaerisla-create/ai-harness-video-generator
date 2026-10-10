import json
import re
import logging
import random
import httpx
from typing import Dict, Any, Optional, List
from backend.app.config import settings
from backend.app.schemas.video import StoryScript, ScenePlanItem

logger = logging.getLogger("ai_harness.story_planner")

# High-Retention 9:16 Viral Shorts Visual Directives
PILLAR_DIRECTIVES = {
    "business_strategy": "cinematic Wall Street documentary, sleek minimalist skyscraper, financial metric hologram, dramatic 35mm lighting, high-stakes corporate aesthetic",
    "ai_news": "futuristic robotics research lab, glowing humanoid robot prototype, optical quantum fiber arrays, high-tech Silicon Valley cleanroom",
    "sci_fi_concept": "IMAX space exploration, monolithic Dyson swarm mirror arrays, deep interstellar cosmic nebula, hard science fiction photorealism",
    "emerging_tech": "clean precision engineering, magnetic tokamak fusion plasma chamber, microscopic silicon wafer lithography, glowing energy cells",
    "future_predictions": "utopian 2040 smart metropolis, autonomous aerial transit, biophilic architectural towers, golden hour cinematic aerial view"
}

MOTION_TYPES = ["zoom_in", "zoom_out", "pan_left", "pan_right", "slow_push"]
TRANSITIONS = ["fade", "dissolve", "zoom_cut", "whip_pan"]

def clean_script_narration(text: str) -> str:
    """
    Strips unwanted headings like 'Act 1:', 'Scene 1:', 'Voiceover:', markdown stars, etc.
    Guarantees clean, conversational speech and caption output.
    """
    t = str(text).strip()
    # Remove Act/Scene markers
    t = re.sub(r'(?i)^(act|scene)\s*\d+[:\-\.]?\s*', '', t)
    t = re.sub(r'(?i)^(voiceover|narration|narrator|speaker)[:\-\.]?\s*', '', t)
    # Remove markdown asterisks, brackets
    t = t.replace('**', '').replace('*', '').replace('__', '').replace('#', '')
    t = re.sub(r'\[.*?\]', '', t)
    return " ".join(t.split())

class StoryPlanner:
    def __init__(self):
        self.ollama_url = f"{settings.OLLAMA_BASE_URL}/api/generate"
        self.model = settings.OLLAMA_MODEL

    async def generate_script(
        self,
        prompt: str,
        style: str = "business_strategy",
        target_duration: int = 45,
        character_guidelines: Optional[str] = None
    ) -> StoryScript:
        """
        Plans a viral-optimized short-form script for FB Reels & YouTube Shorts (30-60s).
        Divides into 8 to 11 rapid micro-scenes (3.5 to 5.0 seconds each) for maximum watch-time.
        """
        valid_styles = ["business_strategy", "ai_news", "sci_fi_concept", "emerging_tech", "future_predictions"]
        style_key = style.lower() if style.lower() in valid_styles else "business_strategy"
        style_enhancer = PILLAR_DIRECTIVES.get(style_key, PILLAR_DIRECTIVES["business_strategy"])

        # Rapid pacing for Shorts / Reels: ~4.5 seconds per scene
        # 45s = ~10 scenes, 30s = 7 scenes, 60s = 12 scenes
        num_scenes = max(6, min(12, int(round(target_duration / 4.5))))
        words_per_scene = int(round(4.5 * 2.5))  # ~11-12 words per second-by-second scene

        system_instruction = (
            f"You are an elite short-form video director and scriptwriter for YouTube Shorts and Facebook Reels. "
            f"You write viral, high-retention scripts about business strategies, AI breakthroughs, science fiction, and future technology. "
            f"NEVER write cartoons, anime, or fairy tales. Keep the tone sharp, factual, and captivating.\n"
            f"Video Length: {target_duration} seconds across exactly {num_scenes} rapid scenes (~{words_per_scene} spoken words each).\n"
            f"Format:\n"
            f"- Scene 1 MUST be a 2-second viral scroll-stopping hook (e.g., a contrarian fact or question).\n"
            f"- Scene 2-8: Rapid breakdown of the core strategy, mechanism, or breakthrough.\n"
            f"- Final Scene: Mind-bending takeaway or question that loops back to the beginning.\n"
            f"- 'narration_text' MUST be raw spoken words only. DO NOT include 'Act 1', 'Scene 1', 'Voiceover', or markdown.\n"
            f"- 'visual_prompt': photorealistic cinematic visual description with lighting and composition.\n"
            f"- 'motion_type': one of {MOTION_TYPES}\n"
            f"- 'transition': one of {TRANSITIONS}\n"
            f"Output strictly valid JSON with this exact schema:\n"
            f'{{"title": "...", "synopsis": "...", "scenes": [{{"sequence_number": 1, "narration_text": "...", "visual_prompt": "...", "motion_type": "zoom_in", "transition": "fade", "estimated_duration": 4.5}}]}}'
        )

        user_content = f"Topic Concept: {prompt}\nTarget Duration: {target_duration} seconds.\nScenes Required: {num_scenes}."

        for attempt in range(1, settings.LLM_RETRY_COUNT + 1):
            try:
                logger.info(f"Planning script via Ollama ({self.model}), attempt {attempt}")
                script = await self._call_ollama(system_instruction, user_content, num_scenes, target_duration)
                if script:
                    return script
            except Exception as e:
                logger.warning(f"Ollama planning attempt {attempt} failed: {e}")

        logger.info("Using built-in high-retention viral script synthesizer.")
        return self._generate_fallback_script(prompt, style_key, num_scenes, target_duration, style_enhancer)

    async def _call_ollama(
        self,
        system_instruction: str,
        user_content: str,
        num_scenes: int,
        target_duration: int
    ) -> Optional[StoryScript]:
        payload = {
            "model": self.model,
            "prompt": f"{system_instruction}\n\nUser Request: {user_content}\n\nJSON Output:",
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.65,
                "top_p": 0.9,
                "num_predict": 1400,
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.ollama_url, json=payload)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            raw = data.get("response", "{}")
            parsed = json.loads(raw)
            if "story" in parsed and isinstance(parsed["story"], dict):
                parsed = parsed["story"]

            scenes = parsed.get("scenes", [])
            if not isinstance(scenes, list) or len(scenes) == 0:
                return None

            clean_scenes = []
            per_scene_dur = round(target_duration / len(scenes), 2)
            for idx, sc in enumerate(scenes):
                if not isinstance(sc, dict):
                    continue
                vp = sc.get("visual_prompt", "")
                if isinstance(vp, dict):
                    vp = vp.get("description") or vp.get("visual_prompt") or str(vp)
                
                nt = clean_script_narration(sc.get("narration_text", ""))
                motion = sc.get("motion_type", MOTION_TYPES[idx % len(MOTION_TYPES)])
                if motion not in MOTION_TYPES:
                    motion = MOTION_TYPES[idx % len(MOTION_TYPES)]
                
                trans = sc.get("transition", TRANSITIONS[idx % len(TRANSITIONS)])
                if trans not in TRANSITIONS:
                    trans = "fade"

                clean_scenes.append(ScenePlanItem(
                    sequence_number=idx + 1,
                    narration_text=nt,
                    visual_prompt=str(vp),
                    character_continuity="Professional high-definition cinematography, clean safe-zone layout",
                    motion_type=motion,
                    transition=trans,
                    estimated_duration=per_scene_dur
                ))

            return StoryScript(
                title=parsed.get("title", "High-Impact Tech Breakdown"),
                synopsis=parsed.get("synopsis", "Automated viral short breakdown."),
                characters={"Format": "Cinematic 9:16 Vertical"},
                scenes=clean_scenes
            )

    def _generate_fallback_script(
        self,
        prompt: str,
        style: str,
        num_scenes: int,
        target_duration: int,
        style_enhancer: str
    ) -> StoryScript:
        """
        Generates genuine, professional viral story breakdowns for Business, AI,
        Sci-Fi, Emerging Tech, and Future Predictions with second-by-second pacing.
        """
        # Clean title
        title_raw = prompt.split(":")[0] if ":" in prompt else prompt[:40]
        title = title_raw.strip().title()
        
        per_scene_dur = round(target_duration / num_scenes, 2)

        # High-retention script templates based on content pillar
        if style == "business_strategy":
            beats = [
                ("Why most people misunderstand how this company actually makes billions.", "Wide aerial view of glass corporate headquarters at dusk, dramatic lighting."),
                ("On the surface, they sell products everyone recognizes every single day.", "Macro camera tracking along sleek retail packaging on a minimalist shelf."),
                ("But here is the hidden mechanism: their core product is a loss leader.", "Holographic financial revenue breakdown glowing over an executive boardroom table."),
                ("The real profit engine operates completely behind the scenes at eighty percent margins.", "Wall Street digital trading terminals flickering with live cashflow metrics."),
                ("By locking customers into a recurring ecosystem, customer lifetime value skyrockets.", "Interconnected digital network nodes illuminating globally across a 3D Earth map."),
                ("Competitors spent billions trying to copy the hardware, while ignoring the moat.", "Cinematic contrast between struggling outdated factories and automated robotic distribution."),
                ("The lesson for any founder is simple: own the distribution network, not just the product.", "Confident executive stepping out of an architectural boardroom overlooking a modern skyline."),
                ("And that is why the biggest monopolies in history rarely look like what they sell.", "Dramatic push-in on an abstract golden architectural monument in the setting sun.")
            ]
        elif style == "ai_news":
            beats = [
                ("In the last forty-eight hours, something fundamental just shifted in artificial intelligence.", "Extreme close-up on optical compute chips with pulsing electric blue light."),
                ("Researchers broke through the compute wall using test-time reasoning models.", "Neural network synapse lines firing in three-dimensional holographic space."),
                ("Instead of just predicting the next word, the AI now pauses to self-correct its thoughts.", "Cleanroom laboratory with robotic arms assembling microscopic photonic circuits."),
                ("This means complex mathematics and software engineering problems are solved in seconds.", "Multiple translucent monitor screens streaming self-verifying algorithmic code."),
                ("At the same time, next-generation humanoid robots are walking off research stages into factories.", "Full-body view of a sleek humanoid robotic worker lifting automotive precision parts."),
                ("The physical world and digital intelligence are merging faster than policy can keep up.", "High-speed timelapse of autonomous logistics drones navigating a smart metropolitan port."),
                ("Those who understand this shift will build the next decade of trillion-dollar tools.", "Modern tech founder working with floating holographic generative design software."),
                ("We are not entering the future of AI. We are already living inside it.", "Cinematic wide shot looking toward a breathtaking sunset over a glowing Silicon Valley skyline.")
            ]
        elif style == "sci_fi_concept":
            beats = [
                ("What happens when a civilization outgrows the energy of an entire planet?", "Breathtaking view of planet Earth surrounded by glowing orbital solar arrays."),
                ("Enter the Dyson Swarm: humanity's ultimate megastructure engineering ambition.", "Massive hexagonal solar collector mirrors floating in golden proximity to the Sun."),
                ("By orbiting millions of mirrors around the Sun, we capture sextillions of watts.", "Volumetric solar flares arching gracefully behind orbital mega-reflectors."),
                ("With that sheer energy, antimatter synthesis becomes cheap enough for interstellar travel.", "Magnetic containment torus pulsing with radiant violet antimatter plasma."),
                ("Spacecraft could accelerate to twenty percent the speed of light toward Proxima Centauri.", "Sleek deep-space exploratory vessel firing an ion propulsion beam into the cosmic void."),
                ("The physics are not science fiction; the math is entirely proven under general relativity.", "Detailed holographic astronomical blueprints showing Lagrange point orbital paths."),
                ("The only real bottleneck is developing autonomous robotic self-replication in space.", "Robotic asteroid mining probes cutting through metallic celestial bodies."),
                ("In the cosmic timeline, our journey to becoming a Type Two civilization has already begun.", "Vast panoramic view of deep interstellar space with glowing spiral galaxies.")
            ]
        elif style == "emerging_tech":
            beats = [
                ("This single emerging technology is about to make fossil fuels obsolete forever.", "Macro close-up on solid-state battery ceramic crystal lattices under electron microscope."),
                ("Traditional batteries rely on liquid electrolytes that degrade and overheat under load.", "Cross-section schematic illustrating atomic lithium ions flowing between electrodes."),
                ("Solid-state cells pack double the energy density with ten-minute fast charging times.", "Electric supercar chassis glowing with internal high-voltage battery architecture."),
                ("Simultaneously, magnetic fusion reactors just crossed net energy gain milestones.", "Interior view of a glowing tokamak vacuum vessel with magnetic plasma vortex."),
                ("Temperatures hotter than the center of the Sun held in place by superconducting magnets.", "Cryogenic cooling lines venting cold vapor across high-tech steel reactor housings."),
                ("Within a single generation, energy abundance will transform fresh water and transportation.", "Vast clean desalination facilities powered by baseline clean fusion energy."),
                ("When power becomes virtually limitless, the economics of civilization change permanently.", "Futuristic automated industrial infrastructure operating with zero emissions."),
                ("The technological revolution of our lifetime is happening right beneath the surface.", "Dramatic tilt up toward an awe-inspiring clean energy facility at twilight.")
            ]
        else: # future_predictions
            beats = [
                ("By the year 2035, the ordinary rhythm of daily human life will be unrecognizable.", "Cinematic view of an autonomous electric shuttle gliding through a biophilic smart city."),
                ("Commuting in traffic will be replaced by autonomous pod networks and smart air mobility.", "Sleek eVTOL passenger aircraft ascending smoothly above glittering urban skyways."),
                ("Ambient sensory AI assistants will handle communications, contracts, and daily logistics.", "First-person perspective of augmented reality contact lenses displaying real-time data overlays."),
                ("Humanoid robotics will take over repetitive physical labor, redefining the workforce.", "Humanoid robotic assistants stocking vertical organic hydroponic urban gardens."),
                ("Preventative gene editing and cellular rejuvenation could extend healthy human lifespans past one hundred.", "High-tech wellness clinic with non-invasive molecular diagnostic scanner rings."),
                ("Cities will operate as decentralized ecosystems with kinetic walkways and localized solar microgrids.", "Panoramic shot of vertical forest skyscrapers with cascading green hanging gardens."),
                ("The question is no longer whether this future is arriving, but whether you are prepared for it.", "Young visionary looking out over an inspiring, gleaming metropolis at twilight."),
                ("The next decade will create more wealth and disruption than the entire century before it.", "Cinematic pull-back revealing a breathtaking sunset reflecting off glass towers.")
            ]

        # Fit beats to num_scenes
        scenes = []
        for i in range(num_scenes):
            beat_idx = int((i / float(num_scenes)) * len(beats))
            beat_idx = min(beat_idx, len(beats) - 1)
            narration_text, visual_directive = beats[beat_idx]

            motion = MOTION_TYPES[i % len(MOTION_TYPES)]
            trans = "fade" if i == 0 else TRANSITIONS[i % len(TRANSITIONS)]

            full_visual = f"{style_enhancer}, {visual_directive}, cinematic vertical 9:16 framing, clean composition, no text"

            scenes.append(ScenePlanItem(
                sequence_number=i + 1,
                narration_text=clean_script_narration(narration_text),
                visual_prompt=full_visual,
                character_continuity="Professional high-definition cinematography, clean safe-zone layout",
                motion_type=motion,
                transition=trans,
                estimated_duration=per_scene_dur
            ))

        return StoryScript(
            title=title,
            synopsis=f"Short-form viral breakdown on {title}.",
            characters={"Protagonist": "Focus subject / narrator", "Format": "Cinematic 9:16 Vertical"},
            scenes=scenes
        )
