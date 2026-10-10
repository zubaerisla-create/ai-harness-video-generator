import os
import io
import time
import math
import random
import urllib.parse
import urllib.request
import logging
import httpx
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from backend.app.config import settings

logger = logging.getLogger("ai_harness.image_generator")

# High-Engagement Visual Directives
STYLE_VISUAL_ENHANCERS: Dict[str, str] = {
    "business_strategy": (
        "cinematic photorealistic 35mm film still, architectural glass monolith skyscraper, "
        "minimalist executive boardroom, Wall Street financial graph hologram, sleek corporate luxury, "
        "dramatic chiaroscuro lighting, color graded 8k resolution, cinematic depth of field"
    ),
    "ai_news": (
        "photorealistic futuristic tech laboratory, glowing humanoid robot chassis, "
        "neural network optical fiber arrays, clean glass cleanroom, holographic AI interface, "
        "octane render, volumetric light beams, sharp focus, 8k commercial quality"
    ),
    "sci_fi_concept": (
        "IMAX 70mm cinematography, monolithic Dyson swarm megastructure orbiting stellar surface, "
        "deep space cosmic nebula, antimatter plasma containment, hyperrealistic hard science fiction, "
        "atmospheric volumetric dust, photorealistic astronomy art"
    ),
    "emerging_tech": (
        "photorealistic industrial precision technology, magnetic tokamak fusion reactor with 100M-degree plasma, "
        "microscopic silicon photonic chip pathways, clean metallic engineering, anamorphic lens flare, 8k"
    ),
    "future_predictions": (
        "cinematic wide-angle view of year 2040 sustainable metropolis, autonomous maglev transit lines, "
        "biophilic vertical forest towers, golden hour twilight atmospheric lighting, utopian architectural photography"
    )
}

class VisualProviderBase(ABC):
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        pass

class PollinationsDiffusionProvider(VisualProviderBase):
    """
    State-of-the-art free AI Diffusion provider using Pollinations / Flux.
    Generates genuine, high-definition, photorealistic or stylized visuals
    directly tailored to the exact scene prompt. Zero API key, 100% free, fast.
    """
    def __init__(self):
        self.backend_name = "pollinations_flux"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate a distinct random seed for every scene
        seed = random.SystemRandom().randint(1000, 99999999)

        # Detect if prompt requests anime / cartoon / illustration or photorealism
        p_lower = prompt.lower()
        if any(w in p_lower for w in ["anime", "manga", "cartoon", "lumi", "kai", "dragon", "drawn"]):
            enhancer = "masterpiece, high quality Japanese fantasy anime art, Makoto Shinkai style, vibrant colors, expressive character, detailed cinematic background, 8k"
        else:
            enhancer = STYLE_VISUAL_ENHANCERS.get(style.lower(), STYLE_VISUAL_ENHANCERS["business_strategy"])

        clean_p = " ".join(prompt.replace("{", " ").replace("}", " ").replace('"', ' ').replace("\n", " ").split())
        
        parts = [clean_p]
        if character_details and character_details.strip():
            parts.append(character_details.strip())
        parts.append(enhancer)
        parts.append("9:16 vertical composition, clean image, no text watermark")

        full_prompt = ", ".join(parts)[:380]
        encoded_prompt = urllib.parse.quote(full_prompt)

        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"

        data = await asyncio.to_thread(self._fetch_image_sync, url)
        if data:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            if img.size != (width, height):
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            img.save(output_path, "JPEG", quality=92)
            logger.info(f"Pollinations visual synthesized for scene {scene_index} (seed={seed})")
            return True, self.backend_name, f"Rendered Flux diffusion visual for scene {scene_index}"

        return False, self.backend_name, "Pollinations request timed out or unavailable"

    def _fetch_image_sync(self, url: str) -> Optional[bytes]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=18.0) as resp:
                if resp.status == 200:
                    content = resp.read()
                    if len(content) > 5000:
                        return content
        except Exception as e:
            logger.warning(f"Pollinations fetch exception: {e}")
        return None

class AIHordeDiffusionProvider(VisualProviderBase):
    """
    Secondary AI diffusion provider via open AI Horde distributed cluster.
    """
    def __init__(self, api_key: str = "0000000000"):
        self.backend_name = "ai_horde"
        self.api_key = api_key
        self.client_agent = "AIStoryHarness:2.0:cinematic"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        enhancer = STYLE_VISUAL_ENHANCERS.get(style.lower(), STYLE_VISUAL_ENHANCERS["business_strategy"])
        cleaned = " ".join(str(prompt).replace("{", " ").replace("}", " ").replace('"', ' ').split())
        seed = random.SystemRandom().randint(10000, 9999999)
        full_prompt = f"{cleaned}, {enhancer}, photorealistic, clean composition, no text, no captions, no watermark"

        submit_url = "https://aihorde.net/api/v2/generate/async"
        headers = {
            "apikey": self.api_key,
            "Client-Agent": self.client_agent,
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": full_prompt[:450],
            "params": {
                "steps": 16,
                "n": 1,
                "sampler_name": "k_euler_a",
                "width": 512,
                "height": 896,
                "cfg_scale": 7.0,
                "seed": str(seed),
                "karras": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(submit_url, json=payload, headers=headers)
                if resp.status_code != 202:
                    return False, self.backend_name, f"HTTP {resp.status_code}"
                
                job_id = resp.json().get("id")
                if not job_id:
                    return False, self.backend_name, "No job ID returned"

                check_url = f"https://aihorde.net/api/v2/generate/check/{job_id}"
                status_url = f"https://aihorde.net/api/v2/generate/status/{job_id}"

                for _ in range(8):
                    await asyncio.sleep(2.0)
                    c_resp = await client.get(check_url, headers=headers)
                    if c_resp.status_code != 200:
                        continue
                    c_data = c_resp.json()
                    if c_data.get("done", False):
                        s_resp = await client.get(status_url, headers=headers)
                        if s_resp.status_code == 200:
                            gens = s_resp.json().get("generations", [])
                            if gens and gens[0].get("img"):
                                img_url = gens[0]["img"]
                                img_resp = await client.get(img_url)
                                if img_resp.status_code == 200:
                                    img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                                    img.save(output_path, "JPEG", quality=94)
                                    return True, self.backend_name, "AI Horde diffusion image rendered"
                        break
        except Exception:
            pass

        return False, self.backend_name, "AI Horde unavailable"

class ProceduralCinematicProvider(VisualProviderBase):
    """
    High-grade procedural cinematic visuals for emergency fallback if network is offline.
    """
    def __init__(self):
        self.backend_name = "procedural_cinematic"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            await asyncio.to_thread(
                self._render_cinematic_visual,
                prompt,
                output_path,
                style,
                width,
                height,
                scene_index
            )
            return True, self.backend_name, f"Rendered unique cinematic visual for scene {scene_index}"
        except Exception as e:
            logger.error(f"Procedural visual render error: {e}")
            return False, self.backend_name, str(e)

    def _render_cinematic_visual(
        self,
        prompt: str,
        output_path: Path,
        style: str,
        width: int,
        height: int,
        scene_index: int
    ):
        seed = int(time.time() * 1000) % 100000 + (scene_index * 37) + hash(prompt) % 10000
        rng = random.Random(seed)

        img = Image.new("RGB", (width, height), color=(10, 12, 18))
        draw = ImageDraw.Draw(img)

        themes = {
            "business_strategy": [
                ((8, 14, 28), (20, 45, 80), (0, 180, 216)),
                ((18, 12, 28), (55, 30, 85), (255, 180, 50)),
                ((12, 22, 18), (25, 65, 45), (75, 230, 160)),
            ],
            "ai_news": [
                ((5, 10, 25), (15, 35, 75), (0, 240, 255)),
                ((15, 5, 25), (60, 20, 90), (255, 60, 180)),
                ((8, 18, 22), (20, 70, 85), (100, 255, 210)),
            ],
            "sci_fi_concept": [
                ((2, 4, 12), (18, 12, 45), (180, 80, 255)),
                ((8, 4, 16), (40, 15, 35), (255, 90, 40)),
                ((2, 12, 20), (10, 40, 65), (70, 200, 255)),
            ],
            "emerging_tech": [
                ((12, 16, 24), (30, 50, 75), (80, 220, 255)),
                ((15, 20, 10), (45, 70, 25), (170, 255, 80)),
                ((20, 15, 10), (75, 45, 20), (255, 160, 60)),
            ],
            "future_predictions": [
                ((10, 15, 30), (35, 55, 95), (255, 210, 90)),
                ((6, 20, 25), (25, 80, 95), (140, 255, 230)),
                ((18, 8, 25), (70, 25, 80), (255, 120, 160)),
            ]
        }

        theme_list = themes.get(style.lower(), themes["business_strategy"])
        top_c, mid_c, accent_c = theme_list[(scene_index - 1) % len(theme_list)]

        for y in range(height):
            ratio = y / float(height)
            if ratio < 0.6:
                sub_r = ratio / 0.6
                r = int(top_c[0] + (mid_c[0] - top_c[0]) * sub_r)
                g = int(top_c[1] + (mid_c[1] - top_c[1]) * sub_r)
                b = int(top_c[2] + (mid_c[2] - top_c[2]) * sub_r)
            else:
                sub_r = (ratio - 0.6) / 0.4
                r = int(mid_c[0] + (top_c[0] - mid_c[0]) * sub_r * 0.5)
                g = int(mid_c[1] + (top_c[1] - mid_c[1]) * sub_r * 0.5)
                b = int(mid_c[2] + (top_c[2] - mid_c[2]) * sub_r * 0.5)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Dynamic visual elements
        center_x = width // 2
        center_y = int(height * 0.52)
        for ring_r in range(70, 240, 45):
            draw.arc(
                [center_x - ring_r, center_y - ring_r // 2, center_x + ring_r, center_y + ring_r // 2],
                start=0,
                end=360,
                fill=(accent_c[0] // 2, accent_c[1] // 2, accent_c[2] // 2),
                width=2
            )

        img.save(output_path, "JPEG", quality=90)

class ImageGeneratorService:
    def __init__(self):
        self.pollinations_provider = PollinationsDiffusionProvider()
        self.ai_horde_provider = AIHordeDiffusionProvider()
        self.procedural_provider = ProceduralCinematicProvider()

    async def generate_scene_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        valid_styles = ["business_strategy", "ai_news", "sci_fi_concept", "emerging_tech", "future_predictions"]
        style_key = style.lower() if style.lower() in valid_styles else "business_strategy"

        # 1. Primary: Genuine AI Diffusion via Pollinations Flux (Real images matching scene prompt)
        try:
            success, backend, msg = await self.pollinations_provider.generate_image(
                prompt=prompt,
                output_path=output_path,
                style=style_key,
                width=width,
                height=height,
                scene_index=scene_index,
                character_details=character_details
            )
            if success:
                return True, backend, msg
        except Exception as e:
            logger.warning(f"Pollinations primary attempt failed for scene {scene_index}: {e}")

        # 2. Secondary: AI Horde cluster
        try:
            success, backend, msg = await self.ai_horde_provider.generate_image(
                prompt=prompt,
                output_path=output_path,
                style=style_key,
                width=width,
                height=height,
                scene_index=scene_index,
                character_details=character_details
            )
            if success:
                return True, backend, msg
        except Exception:
            pass

        # 3. Tertiary: High-performance procedural fallback
        return await self.procedural_provider.generate_image(
            prompt=prompt,
            output_path=output_path,
            style=style_key,
            width=width,
            height=height,
            scene_index=scene_index,
            character_details=character_details
        )
