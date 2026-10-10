import os
import io
import time
import math
import random
import urllib.parse
import urllib.request
import logging
import json
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from backend.app.config import settings

logger = logging.getLogger("ai_harness.image_generator")

# Visual style directives
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
    Tier 1: Free AI Diffusion provider using Pollinations.
    Uses free 512x896 endpoint (avoids 402 resolution blocks) and upscales to 9:16 vertical (720x1280).
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

        clean_p = " ".join(prompt.replace("{", " ").replace("}", " ").replace('"', ' ').replace("\n", " ").split())
        p_lower = clean_p.lower()

        # Build prompt
        parts = [clean_p[:110]]
        if character_details and character_details.strip():
            parts.append(character_details.strip()[:60])

        if any(w in p_lower for w in ["anime", "manga", "cartoon", "lumi", "kai", "dragon", "drawn"]):
            parts.append("anime fantasy masterpiece 8k")
        else:
            parts.append("cinematic 8k photorealistic")

        full_prompt = ", ".join(parts)[:160]
        encoded_prompt = urllib.parse.quote(full_prompt)

        # Use 512x896 free tier resolution to prevent 402 Payment Required errors
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=896&nologo=true"

        data = await asyncio.to_thread(self._fetch_image_sync, url)
        if data:
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
                if img.size != (width, height):
                    img = img.resize((width, height), Image.Resampling.LANCZOS)
                img.save(output_path, "JPEG", quality=92)
                logger.info(f"Pollinations visual synthesized for scene {scene_index}")
                return True, self.backend_name, f"Rendered Flux diffusion visual for scene {scene_index}"
            except Exception as parse_err:
                logger.warning(f"Pollinations image parse error: {parse_err}")

        return False, self.backend_name, "Pollinations request skipped or unavailable"

    def _fetch_image_sync(self, url: str) -> Optional[bytes]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://pollinations.ai/"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=14.0) as resp:
                if resp.status == 200:
                    content = resp.read()
                    if len(content) > 5000:
                        return content
        except Exception as e:
            logger.debug(f"Pollinations fetch attempt: {e}")
        return None

class OpenverseSemanticProvider(VisualProviderBase):
    """
    Tier 2: Semantic Image Provider querying Openverse (700M+ Creative Commons image archive).
    Extracts core thematic scene entities (dragon, starry night, mountain, bridge, city, lab)
    and formats the image into a vertical 9:16 cinematographic frame.
    """
    def __init__(self):
        self.backend_name = "openverse_archive"

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

        p_lower = prompt.lower()
        search_terms = self._extract_keywords(p_lower, style)

        for term in search_terms:
            data = await asyncio.to_thread(self._search_and_download, term, width, height)
            if data:
                try:
                    data.save(output_path, "JPEG", quality=92)
                    logger.info(f"Openverse semantic visual fetched for scene {scene_index} (keyword: '{term}')")
                    return True, self.backend_name, f"Found semantic visual for '{term}'"
                except Exception as e:
                    logger.warning(f"Error saving Openverse image: {e}")

        return False, self.backend_name, "Openverse yielded no suitable visual"

    def _extract_keywords(self, p: str, style: str) -> List[str]:
        terms = []
        if any(w in p for w in ["dragon", "lumi"]):
            terms.extend(["fantasy dragon", "dragon art", "mystical dragon"])
        if any(w in p for w in ["bridge"]):
            terms.extend(["ancient bridge", "fantasy bridge", "stone bridge"])
        if any(w in p for w in ["forest", "tree", "woods"]):
            terms.extend(["enchanted forest", "magical forest", "misty forest"])
        if any(w in p for w in ["mountain", "cliff", "shadow creature", "monster"]):
            terms.extend(["dark mountain", "dramatic mountain peak", "rocky mountain"])
        if any(w in p for w in ["star", "night", "sky", "galaxy"]):
            terms.extend(["starry night sky", "milky way stars", "night sky"])
        if any(w in p for w in ["light", "burst", "defeat", "celebrat", "sun", "dawn"]):
            terms.extend(["golden light magic", "fireworks night", "golden sunset"])
        if any(w in p for w in ["village", "town", "house"]):
            terms.extend(["peaceful village night", "old village", "fantasy town"])
        if any(w in p for w in ["robot", "cyber", "ai", "hologram", "future"]):
            terms.extend(["cyberpunk neon city", "futuristic robot", "high tech lab"])
        if any(w in p for w in ["business", "money", "corporate", "stock", "market"]):
            terms.extend(["skyscraper skyline", "financial district", "modern corporate building"])

        if not terms:
            style_defaults = {
                "business_strategy": ["modern skyscraper skyline", "executive office architecture"],
                "ai_news": ["futuristic technology laboratory", "digital neural network"],
                "sci_fi_concept": ["deep space nebula galaxy", "futuristic cosmic planet"],
                "emerging_tech": ["high tech cleanroom", "microchip technology"],
                "future_predictions": ["futuristic smart city", "biophilic modern architecture"]
            }
            terms = style_defaults.get(style.lower(), ["dramatic cinematic landscape", "starry night sky"])

        return terms

    def _search_and_download(self, keyword: str, target_w: int, target_h: int) -> Optional[Image.Image]:
        encoded = urllib.parse.quote(keyword)
        ov_url = f"https://api.openverse.org/v1/images/?q={encoded}&page_size=4"
        req = urllib.request.Request(
            ov_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AIStoryHarness/2.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=9.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get("results", [])
                for r in results:
                    img_url = r.get("url")
                    if not img_url:
                        continue
                    try:
                        dl_req = urllib.request.Request(
                            img_url,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                        )
                        with urllib.request.urlopen(dl_req, timeout=7.0) as dl_resp:
                            raw = dl_resp.read()
                            if len(raw) > 8000:
                                img = Image.open(io.BytesIO(raw)).convert("RGB")
                                return self._crop_to_vertical(img, target_w, target_h)
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    def _crop_to_vertical(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        orig_w, orig_h = img.size
        target_ratio = target_w / target_h
        orig_ratio = orig_w / orig_h

        if orig_ratio > target_ratio:
            # Wider than target ratio: crop left and right
            new_w = int(orig_h * target_ratio)
            left = (orig_w - new_w) // 2
            img = img.crop((left, 0, left + new_w, orig_h))
        else:
            # Taller than target ratio: crop top and bottom
            new_h = int(orig_w / target_ratio)
            top = (orig_h - new_h) // 2
            img = img.crop((0, top, orig_w, top + new_h))

        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        # Subtle contrast and saturation polish for mobile OLED screens
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.12)
        return img

class ThematicProceduralCanvasProvider(VisualProviderBase):
    """
    Tier 3: Rich Thematic Environment Canvas (Never fails, zero offline dependencies).
    Generates dynamic atmospheric environments tailored directly to scene sentiment:
    celestial bodies, layered mountain silhouettes, glowing particles, cosmic nebulas,
    and distinct color palettes for every single scene.
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
                self._render_scene_environment,
                prompt,
                output_path,
                style,
                width,
                height,
                scene_index
            )
            return True, self.backend_name, f"Rendered thematic environment for scene {scene_index}"
        except Exception as e:
            logger.error(f"Procedural environment render error: {e}")
            return False, self.backend_name, str(e)

    def _render_scene_environment(
        self,
        prompt: str,
        output_path: Path,
        style: str,
        width: int,
        height: int,
        scene_index: int
    ):
        seed = scene_index * 2026 + (hash(prompt) % 100000)
        rng = random.Random(seed)
        p_lower = prompt.lower()

        is_dragon_fantasy = any(w in p_lower for w in ["dragon", "lumi", "kai", "magic", "fantasy", "anime", "forest", "bridge"])
        is_space = any(w in p_lower for w in ["star", "galaxy", "space", "nebula", "cosmos", "dyson", "alien"])
        is_shadow = any(w in p_lower for w in ["shadow", "dark", "mountain", "creature", "monster", "danger", "evil"])
        is_light = any(w in p_lower for w in ["light", "defeat", "celebrat", "sun", "gold", "dawn", "morning", "triumph"])
        is_tech = any(w in p_lower for w in ["ai", "robot", "tech", "chip", "cyber", "network"])

        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # 1. Background Gradient Palette
        if is_light:
            sky_top = (15, 20, 55)
            sky_mid = (70, 40, 95)
            sky_bot = (255, 175, 75)
        elif is_shadow:
            sky_top = (8, 5, 16)
            sky_mid = (26, 12, 36)
            sky_bot = (70, 18, 35)
        elif is_tech:
            sky_top = (4, 10, 24)
            sky_mid = (12, 35, 75)
            sky_bot = (0, 210, 240)
        elif is_dragon_fantasy or is_space:
            sky_top = (6, 9, 24)
            sky_mid = (18, 28, 60)
            sky_bot = (40, 70, 105) if scene_index % 2 == 0 else (65, 30, 80)
        else:
            sky_top = (10, 16, 32)
            sky_mid = (22, 45, 75)
            sky_bot = (15, 85, 125)

        for y in range(height):
            t = y / float(height)
            if t < 0.65:
                st = t / 0.65
                r = int(sky_top[0] + (sky_mid[0] - sky_top[0]) * st)
                g = int(sky_top[1] + (sky_mid[1] - sky_top[1]) * st)
                b = int(sky_top[2] + (sky_mid[2] - sky_top[2]) * st)
            else:
                st = (t - 0.65) / 0.35
                r = int(sky_mid[0] + (sky_bot[0] - sky_mid[0]) * st)
                g = int(sky_mid[1] + (sky_bot[1] - sky_mid[1]) * st)
                b = int(sky_mid[2] + (sky_bot[2] - sky_mid[2]) * st)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Celestial Body (Luminous Moon, Golden Sun, or Pulsar)
        orb_x = rng.randint(int(width * 0.25), int(width * 0.75))
        orb_y = rng.randint(int(height * 0.16), int(height * 0.36))
        orb_r = rng.randint(48, 88)

        glow_col = (255, 220, 130) if is_light else ((100, 225, 255) if is_dragon_fantasy or is_space else (255, 110, 130))
        for halo in range(orb_r + 55, orb_r, -5):
            draw.ellipse(
                [orb_x - halo, orb_y - halo, orb_x + halo, orb_y + halo],
                outline=(glow_col[0] // 3, glow_col[1] // 3, glow_col[2] // 3)
            )

        draw.ellipse([orb_x - orb_r, orb_y - orb_r, orb_x + orb_r, orb_y + orb_r], fill=(248, 250, 255), outline=glow_col)

        # 3. Twinkling Stars
        num_stars = rng.randint(140, 240)
        for _ in range(num_stars):
            sx = rng.randint(0, width)
            sy = rng.randint(0, int(height * 0.75))
            sr = rng.choice([1, 1, 1, 2, 2, 3])
            brightness = rng.randint(180, 255)
            color = (brightness, brightness, int(brightness * 0.9)) if rng.random() > 0.35 else (140, 220, 255)
            draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=color)

        # 4. Multi-Layer Mountain Ranges / Horizon Silhouettes
        for layer in range(3):
            factor = 0.35 + layer * 0.28
            layer_col = (
                int(sky_top[0] * factor),
                int(sky_top[1] * factor),
                int(sky_top[2] * factor)
            )
            base_y = int(height * (0.60 + layer * 0.12))
            points = [(0, height), (0, base_y)]
            x = 0
            while x < width:
                x += rng.randint(45, 95)
                peak_y = base_y + rng.randint(-65, 45)
                points.append((min(width, x), peak_y))
            points.append((width, height))
            draw.polygon(points, fill=layer_col)

        # 5. Magical Floating Particles (Lumi's magic / Starlight)
        if is_dragon_fantasy or is_light or is_space:
            for _ in range(35):
                px = rng.randint(30, width - 30)
                py = rng.randint(int(height * 0.38), height - 80)
                pr = rng.randint(3, 6)
                p_col = (0, 235, 255) if (is_dragon_fantasy or is_space) else (255, 225, 90)
                draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=p_col)

        img.save(output_path, "JPEG", quality=92)

class ImageGeneratorService:
    def __init__(self):
        self.pollinations_provider = PollinationsDiffusionProvider()
        self.openverse_provider = OpenverseSemanticProvider()
        self.thematic_canvas_provider = ThematicProceduralCanvasProvider()

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

        # Tier 1: Pollinations Flux Diffusion (Free 512x896 endpoint, auto-upscaled)
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
            logger.warning(f"Tier 1 Pollinations skipped for scene {scene_index}: {e}")

        # Tier 2: Openverse Semantic Image Archive (700M+ real art & photo library)
        try:
            success, backend, msg = await self.openverse_provider.generate_image(
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
            logger.warning(f"Tier 2 Openverse skipped for scene {scene_index}: {e}")

        # Tier 3: Rich Thematic Procedural Environment (Zero dependencies, guaranteed unique)
        return await self.thematic_canvas_provider.generate_image(
            prompt=prompt,
            output_path=output_path,
            style=style_key,
            width=width,
            height=height,
            scene_index=scene_index,
            character_details=character_details
        )
