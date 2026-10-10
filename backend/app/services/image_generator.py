import os
import io
import time
import math
import random
import urllib.parse
import logging
import httpx
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from backend.app.config import settings

logger = logging.getLogger("ai_harness.image_generator")

# High-Engagement Professional Visual Prompts (Zero Anime/Cartoons)
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

class AIHordeDiffusionProvider(VisualProviderBase):
    """
    Generates genuine AI diffusion images via the open AI Horde distributed cluster.
    100% free, zero API key required, fallback-resilient.
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
        
        # Clean prompt
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
                "steps": 18,
                "n": 1,
                "sampler_name": "k_euler_a",
                "width": 512,
                "height": 896,
                "cfg_scale": 7.5,
                "seed": str(seed),
                "karras": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(submit_url, json=payload, headers=headers)
                if resp.status_code != 202:
                    return False, self.backend_name, f"HTTP {resp.status_code}"
                
                job_id = resp.json().get("id")
                if not job_id:
                    return False, self.backend_name, "No job ID returned"

                check_url = f"https://aihorde.net/api/v2/generate/check/{job_id}"
                status_url = f"https://aihorde.net/api/v2/generate/status/{job_id}"

                # Poll up to 25 seconds
                for _ in range(12):
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
        except Exception as e:
            logger.debug(f"AI Horde attempt bypassed: {e}")

        return False, self.backend_name, "Timed out or queue busy"

class ProceduralCinematicProvider(VisualProviderBase):
    """
    High-grade procedural cinematic visuals for business, AI, science fiction, and emerging tech.
    - Zero reused stock footage.
    - Generates unique motion graphic diagrams, neon neural networks, holographic charts,
      and cosmological physics visuals.
    - NEVER draws "Act 1", "Act 2", or any unwanted top labels. The top 25% is completely clean.
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
        # Generate an entirely unique seed per scene so every image is distinct
        seed = int(time.time() * 1000) % 100000 + (scene_index * 37) + hash(prompt) % 10000
        rng = random.Random(seed)

        img = Image.new("RGB", (width, height), color=(10, 12, 18))
        draw = ImageDraw.Draw(img)

        # Style-specific color grading themes
        themes = {
            "business_strategy": [
                ((8, 14, 28), (20, 45, 80), (0, 180, 216)),       # Tech Wall Street (Navy to Electric Cyan)
                ((18, 12, 28), (55, 30, 85), (255, 180, 50)),     # Premium Gold Corporate (Onyx to Amber)
                ((12, 22, 18), (25, 65, 45), (75, 230, 160)),     # Growth Emerald (Dark Jade to Mint)
            ],
            "ai_news": [
                ((5, 10, 25), (15, 35, 75), (0, 240, 255)),        # Quantum Cyan
                ((15, 5, 25), (60, 20, 90), (255, 60, 180)),       # Neural Magenta & Violet
                ((8, 18, 22), (20, 70, 85), (100, 255, 210)),      # Synthetic Intelligence
            ],
            "sci_fi_concept": [
                ((2, 4, 12), (18, 12, 45), (180, 80, 255)),        # Deep Nebula Violet
                ((8, 4, 16), (40, 15, 35), (255, 90, 40)),         # Antimatter Solar Flare
                ((2, 12, 20), (10, 40, 65), (70, 200, 255)),       # Cryogenic Space
            ],
            "emerging_tech": [
                ((12, 16, 24), (30, 50, 75), (80, 220, 255)),      # Tokamak Fusion Plasma
                ((15, 20, 10), (45, 70, 25), (170, 255, 80)),      # CRISPR Bio-Tech
                ((20, 15, 10), (75, 45, 20), (255, 160, 60)),      # Solid-State Battery Cells
            ],
            "future_predictions": [
                ((10, 15, 30), (35, 55, 95), (255, 210, 90)),      # Year 2035 Horizon Twilight
                ((6, 20, 25), (25, 80, 95), (140, 255, 230)),      # Biophilic Smart City
                ((18, 8, 25), (70, 25, 80), (255, 120, 160)),      # Post-Labor Renaissance
            ]
        }

        theme_list = themes.get(style.lower(), themes["business_strategy"])
        top_c, mid_c, accent_c = theme_list[(scene_index - 1) % len(theme_list)]

        # 1. Base Gradient Background (Cinematic Lighting)
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

        # 2. Render Pillar-Specific Unique Motion Graphic Elements
        if style in ["business_strategy", "ai_news"]:
            # Financial Candlestick / Holographic Growth Chart or Neural Network Graph
            if scene_index % 2 == 1:
                # Glowing Growth Line & Grid
                grid_y_start = int(height * 0.38)
                grid_y_end = int(height * 0.75)
                for gy in range(grid_y_start, grid_y_end, 55):
                    draw.line([(40, gy), (width - 40, gy)], fill=(top_c[0] + 25, top_c[1] + 35, top_c[2] + 45), width=1)
                
                # Chart points
                points = []
                num_pts = 7
                x_step = (width - 120) // (num_pts - 1)
                curr_y = int(height * 0.68)
                for i in range(num_pts):
                    px = 60 + i * x_step
                    curr_y -= rng.randint(20, 65)
                    curr_y = max(int(height * 0.40), curr_y)
                    points.append((px, curr_y))
                
                # Draw glowing line
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i+1]], fill=accent_c, width=4)
                    draw.ellipse([points[i][0] - 6, points[i][1] - 6, points[i][0] + 6, points[i][1] + 6], fill=(255, 255, 255), outline=accent_c, width=2)
                draw.ellipse([points[-1][0] - 8, points[-1][1] - 8, points[-1][0] + 8, points[-1][1] + 8], fill=(255, 255, 255), outline=accent_c, width=3)
            else:
                # Interconnected Neural Network Nodes
                node_coords = []
                for _ in range(14):
                    nx = rng.randint(70, width - 70)
                    ny = rng.randint(int(height * 0.35), int(height * 0.72))
                    node_coords.append((nx, ny))
                
                for i in range(len(node_coords)):
                    for j in range(i + 1, min(i + 4, len(node_coords))):
                        draw.line([node_coords[i], node_coords[j]], fill=(accent_c[0] // 2, accent_c[1] // 2, accent_c[2] // 2), width=1)
                
                for nx, ny in node_coords:
                    r_sz = rng.randint(4, 9)
                    draw.ellipse([nx - r_sz, ny - r_sz, nx + r_sz, ny + r_sz], fill=accent_c, outline=(255, 255, 255), width=2)

        elif style in ["sci_fi_concept", "emerging_tech"]:
            # Cosmic Megastructure, Dyson Ring, or Fusion Tokamak Torus
            center_x = width // 2
            center_y = int(height * 0.52)
            
            # Concentric Orbital Rings with perspective tilt
            for ring_r in range(70, 240, 45):
                draw.arc([center_x - ring_r, center_y - ring_r // 2, center_x + ring_r, center_y + ring_r // 2], start=0, end=360, fill=(accent_c[0] // 2, accent_c[1] // 2, accent_c[2] // 2), width=2)
            
            # Glowing Core / Plasma Sun
            core_r = 45
            draw.ellipse([center_x - core_r, center_y - core_r, center_x + core_r, center_y + core_r], fill=(255, 255, 255), outline=accent_c, width=6)
            
            # Radiating vector beams
            for angle_deg in range(0, 360, 45):
                rad = math.radians(angle_deg)
                bx = int(center_x + math.cos(rad) * 280)
                by = int(center_y + math.sin(rad) * 140)
                draw.line([(center_x, center_y), (bx, by)], fill=(accent_c[0] // 3, accent_c[1] // 3, accent_c[2] // 3), width=1)

        else:
            # Future 2035 Skyline Wireframe & Atmospheric Horizon
            horizon_y = int(height * 0.65)
            # Sky particles
            for _ in range(35):
                sx = rng.randint(20, width - 20)
                sy = rng.randint(int(height * 0.25), horizon_y - 20)
                draw.ellipse([sx, sy, sx + 2, sy + 2], fill=(255, 255, 255))
            
            # Geometric Skyscraper silhouettes
            current_x = 30
            while current_x < width - 30:
                b_w = rng.randint(40, 85)
                b_h = rng.randint(110, 290)
                top_by = horizon_y - b_h
                draw.rectangle([current_x, top_by, current_x + b_w, height], fill=(top_c[0] // 2, top_c[1] // 2, top_c[2] // 2), outline=accent_c, width=1)
                
                # Window grid lines
                for wy in range(top_by + 20, horizon_y, 25):
                    draw.line([(current_x + 5, wy), (current_x + b_w - 5, wy)], fill=(accent_c[0] // 3, accent_c[1] // 3, accent_c[2] // 3), width=1)
                current_x += b_w + rng.randint(10, 25)

        # 3. Depth & Lens Flare Highlights
        flare_x = int(width * (0.3 + (scene_index * 13 % 40) / 100.0))
        flare_y = int(height * 0.38)
        draw.ellipse([flare_x - 30, flare_y - 30, flare_x + 30, flare_y + 30], fill=(255, 255, 255), outline=accent_c, width=1)

        # 4. Vignette shading on borders
        vignette_color = (0, 0, 0)
        draw.line([(0, 0), (width, 0)], fill=vignette_color, width=8)
        draw.line([(0, height - 1), (width, height - 1)], fill=vignette_color, width=12)

        # IMPORTANT: ZERO ACT LABELS, ZERO TOP HEADERS!
        # The top 25% of the frame is 100% clean and pristine.
        img.save(output_path, "JPEG", quality=94)

# Backward-compatibility alias for test suites and legacy imports
StoryboardCanvasProvider = ProceduralCinematicProvider

class ImageGeneratorService:
    def __init__(self):
        self.ai_horde_provider = AIHordeDiffusionProvider()
        self.procedural_provider = ProceduralCinematicProvider()
        self.default_provider = settings.VISUAL_PROVIDER

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

        # Normalize style key to professional pillars
        valid_styles = ["business_strategy", "ai_news", "sci_fi_concept", "emerging_tech", "future_predictions"]
        style_key = style.lower() if style.lower() in valid_styles else "business_strategy"

        # Primary attempt: AI Horde diffusion image if configured
        if self.default_provider in ["ai_diffusion", "ai_horde"]:
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
            except Exception as e:
                logger.debug(f"Diffusion generation skipped to procedural: {e}")

        # High-performance procedural cinematic visual generator (Zero network dependency, fast, unique)
        return await self.procedural_provider.generate_image(
            prompt=prompt,
            output_path=output_path,
            style=style_key,
            width=width,
            height=height,
            scene_index=scene_index,
            character_details=character_details
        )
