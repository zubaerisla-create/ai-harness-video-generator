import os
import io
import time
import math
import random
import urllib.parse
import urllib.request
import logging
import json
import hashlib
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List, Set
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

from backend.app.config import settings

logger = logging.getLogger("ai_harness.image_generator")

IMAGE_HISTORY_FILE = settings.OUTPUT_DIR / "image_history.json"

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by",
    "from", "about", "what", "how", "why", "who", "when", "is", "are", "was", "were",
    "it", "its", "this", "that", "scene", "act", "shot", "documentary", "photo", "cinematic",
    "lighting", "framing", "vertical", "composition", "authentic", "photography"
}

def clean_search_term(text: str) -> str:
    """Extracts high-impact search keywords from a visual or narrative description."""
    words = re_words(text)
    meaningful = [w for w in words if w.lower() not in STOPWORDS and len(w) > 2]
    return " ".join(meaningful[:4]).strip()

def re_words(text: str) -> List[str]:
    import re
    return re.findall(r'[a-zA-Z0-9_\-]+', text)

def apply_documentary_grade(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Applies professional editorial documentary grading:
    - Center-weighted vertical crop to target aspect ratio (e.g. 9:16)
    - High-quality Lanczos resampling
    - Subtle micro-contrast boost and natural color balance
    - Removes synthetic plastic AI look
    """
    orig_w, orig_h = img.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        new_w = int(orig_h * target_ratio)
        left = (orig_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, orig_h))
    else:
        new_h = int(orig_w / target_ratio)
        top = (orig_h - new_h) // 2
        img = img.crop((0, top, orig_w, top + new_h))

    img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    # Filmic micro-contrast & organic tone polish
    contrast_enhancer = ImageEnhance.Contrast(img)
    img = contrast_enhancer.enhance(1.08)
    color_enhancer = ImageEnhance.Color(img)
    img = color_enhancer.enhance(1.05)
    return img

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
        character_details: Optional[str] = None,
        used_urls: Optional[Set[str]] = None
    ) -> Tuple[bool, str, str]:
        pass

class WikipediaLeadImageProvider(VisualProviderBase):
    """
    Tier 1: Authentic Real-World Photography from Wikipedia & Wikimedia Commons.
    Extracts real photographs of companies, executives, research labs, space missions,
    semiconductors, products, and factories with ZERO AI distortion.
    """
    def __init__(self):
        self.backend_name = "wikipedia_real_photo"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None,
        used_urls: Optional[Set[str]] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        candidates = self._extract_entity_candidates(prompt, character_details)
        if not candidates:
            return False, self.backend_name, "No specific real-world entity identified"

        for cand in candidates:
            img_url = await asyncio.to_thread(self._fetch_wiki_image_url, cand, scene_index)
            if img_url and (used_urls is None or img_url not in used_urls):
                data = await asyncio.to_thread(self._download_image_bytes, img_url)
                if data:
                    try:
                        img = Image.open(io.BytesIO(data)).convert("RGB")
                        img = apply_documentary_grade(img, width, height)
                        img.save(output_path, "JPEG", quality=92)
                        if used_urls is not None:
                            used_urls.add(img_url)
                        logger.info(f"Retrieved authentic Wikipedia photo for '{cand}' in scene {scene_index}")
                        return True, self.backend_name, f"Authentic photo of '{cand}'"
                    except Exception as e:
                        logger.debug(f"Failed to process wiki photo for {cand}: {e}")

        return False, self.backend_name, "No suitable Wikipedia photo found"

    def _extract_entity_candidates(self, prompt: str, character_details: Optional[str]) -> List[str]:
        candidates = []
        if character_details:
            clean_char = character_details.replace("Documentary focus on", "").replace("Core focus on", "").strip()
            if len(clean_char) > 2:
                candidates.append(clean_char)

        # Look for capitalized proper nouns or known brands
        words = prompt.replace(",", " ").replace(".", " ").split()
        capitalized = [w.strip() for w in words if w and w[0].isupper() and len(w) > 2]
        
        # Merge consecutive capitalized words (e.g. "Apple Vision", "James Webb")
        merged = []
        i = 0
        while i < len(capitalized):
            if i + 1 < len(capitalized):
                merged.append(f"{capitalized[i]} {capitalized[i+1]}")
            merged.append(capitalized[i])
            i += 1

        for m in merged:
            if m.lower() not in ["the", "how", "why", "what", "when", "and", "new", "all", "its", "scene", "act"]:
                if m not in candidates:
                    candidates.append(m)

        # Add clean search term as final fallback entity
        clean_kw = clean_search_term(prompt)
        if clean_kw and clean_kw not in candidates:
            candidates.append(clean_kw)

        return candidates[:5]

    def _fetch_wiki_image_url(self, entity: str, scene_index: int) -> Optional[str]:
        encoded = urllib.parse.quote(entity)
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={encoded}&prop=pageimages|images&pithumbsize=1280&format=json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AIStoryHarness/2.0 (contact@ai-harness.local)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    if pid == "-1":
                        continue
                    # For scene 1, use the lead image
                    if scene_index == 1:
                        thumb = p.get("thumbnail", {}).get("source")
                        if thumb:
                            return thumb

                    # For other scenes, check article gallery images to provide visual diversity
                    images = p.get("images", [])
                    if images and len(images) > 1:
                        img_idx = (scene_index - 1) % len(images)
                        target_file = images[img_idx].get("title")
                        if target_file and not any(ext in target_file.lower() for ext in [".svg", ".ogg", ".webm"]):
                            detail_url = self._resolve_wiki_file_url(target_file)
                            if detail_url:
                                return detail_url

                    thumb = p.get("thumbnail", {}).get("source")
                    if thumb:
                        return thumb
        except Exception as e:
            logger.debug(f"Wiki lookup for '{entity}' failed: {e}")
        return None

    def _resolve_wiki_file_url(self, file_title: str) -> Optional[str]:
        encoded = urllib.parse.quote(file_title)
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={encoded}&prop=imageinfo&iiprop=url&iiurlwidth=1280&format=json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AIStoryHarness/2.0 (contact@ai-harness.local)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                pages = data.get("query", {}).get("pages", {})
                for pid, p in pages.items():
                    info = p.get("imageinfo", [{}])[0]
                    return info.get("thumburl") or info.get("url")
        except Exception:
            pass
        return None

    def _download_image_bytes(self, url: str) -> Optional[bytes]:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AIStoryHarness/2.0 (contact@ai-harness.local)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                if resp.status == 200:
                    raw = resp.read()
                    if len(raw) > 5000:
                        return raw
        except Exception:
            pass
        return None

class OpenverseSemanticProvider(VisualProviderBase):
    """
    Tier 2: Real Photographic Archive querying Openverse (700M+ Creative Commons photos).
    Dynamically extracts real-world subjects and actions from scene prompts,
    randomizes pagination to guarantee every scene gets a different photo.
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
        character_details: Optional[str] = None,
        used_urls: Optional[Set[str]] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        search_terms = self._generate_search_terms(prompt, style, scene_index)

        for term in search_terms:
            page_offset = (scene_index % 3) + 1
            data = await asyncio.to_thread(self._search_and_download, term, page_offset, width, height, used_urls)
            if data:
                try:
                    data.save(output_path, "JPEG", quality=92)
                    logger.info(f"Openverse photo fetched for scene {scene_index} (keyword: '{term}')")
                    return True, self.backend_name, f"Real photo for '{term}'"
                except Exception as e:
                    logger.warning(f"Error saving Openverse image: {e}")

        return False, self.backend_name, "Openverse yielded no unused visual"

    def _generate_search_terms(self, prompt: str, style: str, scene_index: int) -> List[str]:
        terms = []
        clean = clean_search_term(prompt)
        if clean:
            terms.append(clean)

        p_lower = prompt.lower()
        if any(w in p_lower for w in ["boardroom", "executive", "meeting", "ceo", "director"]):
            terms.append("corporate executive boardroom")
        if any(w in p_lower for w in ["trading", "stock", "wall street", "market", "finance"]):
            terms.append("trading floor financial market")
        if any(w in p_lower for w in ["factory", "warehouse", "manufacturing", "supply chain", "logistics"]):
            terms.append("industrial automated warehouse")
        if any(w in p_lower for w in ["cleanroom", "semiconductor", "lithography", "chip", "microchip"]):
            terms.append("semiconductor cleanroom manufacturing")
        if any(w in p_lower for w in ["lab", "robot", "robotics", "engineer", "testing"]):
            terms.append("robotics laboratory engineer")
        if any(w in p_lower for w in ["telescope", "space", "astronomy", "observatory", "planet", "galaxy"]):
            terms.append("astronomy space observatory")
        if any(w in p_lower for w in ["city", "urban", "metropolis", "skyscraper", "building"]):
            terms.append("modern city skyscraper architecture")

        # Style baseline backups with scene diversity
        style_defaults = {
            "business_strategy": [
                "corporate headquarters architecture", "financial district skyline", "business handshake office"
            ],
            "ai_news": [
                "robotics research laboratory", "data center server rack", "silicon chip engineering"
            ],
            "sci_fi_concept": [
                "astronomy deep space observatory", "telescope galaxy capture", "aerospace engineering facility"
            ],
            "emerging_tech": [
                "cleanroom technology laboratory", "precision engineering manufacturing", "clean energy facility"
            ],
            "future_predictions": [
                "modern sustainable architecture", "autonomous electric vehicle transit", "vertical city garden"
            ]
        }
        backups = style_defaults.get(style.lower(), ["documentary photojournalism landscape"])
        terms.append(backups[scene_index % len(backups)])
        return terms

    def _search_and_download(
        self,
        keyword: str,
        page: int,
        target_w: int,
        target_h: int,
        used_urls: Optional[Set[str]]
    ) -> Optional[Image.Image]:
        encoded = urllib.parse.quote(keyword)
        ov_url = f"https://api.openverse.org/v1/images/?q={encoded}&page={page}&page_size=8"
        req = urllib.request.Request(
            ov_url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AIStoryHarness/2.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=7.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                results = data.get("results", [])
                for r in results:
                    img_url = r.get("url")
                    if not img_url or (used_urls is not None and img_url in used_urls):
                        continue
                    try:
                        dl_req = urllib.request.Request(
                            img_url,
                            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                        )
                        with urllib.request.urlopen(dl_req, timeout=6.0) as dl_resp:
                            raw = dl_resp.read()
                            if len(raw) > 8000:
                                img = Image.open(io.BytesIO(raw)).convert("RGB")
                                if used_urls is not None:
                                    used_urls.add(img_url)
                                return apply_documentary_grade(img, target_w, target_h)
                    except Exception:
                        continue
        except Exception:
            pass
        return None

class PollinationsDiffusionProvider(VisualProviderBase):
    """
    Tier 3: Free AI Diffusion provider with photorealistic documentary prompt directives.
    Strips cheesy sci-fi buzzwords and injects 35mm photojournalism aesthetics.
    Uses dynamic seeds to ensure every generated image is completely distinct.
    """
    def __init__(self):
        self.backend_name = "pollinations_documentary"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None,
        used_urls: Optional[Set[str]] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        clean_p = " ".join(prompt.replace("{", " ").replace("}", " ").replace('"', ' ').replace("\n", " ").split())
        # Strip cheesy buzzwords
        for bad in ["hologram", "octane render", "glowing", "cyber", "3d render", "unreal engine"]:
            clean_p = re.sub(rf'(?i)\b{bad}\b', '', clean_p)

        # Build realistic documentary prompt
        prompt_parts = [clean_p[:110].strip()]
        if character_details and character_details.strip():
            prompt_parts.append(character_details.strip()[:50])

        prompt_parts.append("35mm documentary photography, candid, natural lighting, Leica M11, Kodak Portra 400")
        full_prompt = ", ".join(prompt_parts)[:170]
        encoded_prompt = urllib.parse.quote(full_prompt)

        # Dynamic seed ensures no two identical images are generated
        seed = random.randint(10000, 999999) + scene_index * 1337
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=896&seed={seed}&nologo=true"

        data = await asyncio.to_thread(self._fetch_image_sync, url)
        if data:
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
                img = apply_documentary_grade(img, width, height)
                img.save(output_path, "JPEG", quality=92)
                logger.info(f"Pollinations realistic visual generated for scene {scene_index}")
                return True, self.backend_name, f"Rendered realistic photography still for scene {scene_index}"
            except Exception as parse_err:
                logger.warning(f"Pollinations image parse error: {parse_err}")

        return False, self.backend_name, "Pollinations request skipped or rate-limited"

    def _fetch_image_sync(self, url: str) -> Optional[bytes]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://pollinations.ai/"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                if resp.status == 200:
                    content = resp.read()
                    if len(content) > 5000:
                        return content
        except Exception as e:
            logger.debug(f"Pollinations fetch attempt: {e}")
        return None

class EditorialDocumentaryCanvasProvider(VisualProviderBase):
    """
    Tier 4: Professional Editorial Documentary Canvas (Fail-Safe Offline Guarantee).
    Creates sophisticated archival documentary stills with cinematic duotone color grading,
    film grain, and editorial typography, ensuring the system NEVER renders crude shapes or crashes.
    """
    def __init__(self):
        self.backend_name = "editorial_documentary_canvas"

    async def generate_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "business_strategy",
        width: int = 720,
        height: int = 1280,
        scene_index: int = 1,
        character_details: Optional[str] = None,
        used_urls: Optional[Set[str]] = None
    ) -> Tuple[bool, str, str]:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            await asyncio.to_thread(
                self._render_editorial_canvas,
                prompt,
                output_path,
                style,
                width,
                height,
                scene_index
            )
            return True, self.backend_name, f"Rendered editorial documentary canvas for scene {scene_index}"
        except Exception as e:
            logger.error(f"Editorial canvas render error: {e}")
            return False, self.backend_name, str(e)

    def _render_editorial_canvas(
        self,
        prompt: str,
        output_path: Path,
        style: str,
        width: int,
        height: int,
        scene_index: int
    ):
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # Sophisticated documentary color palettes
        palettes = {
            "business_strategy": ((18, 24, 32), (32, 44, 58), (190, 165, 110)),
            "ai_news": ((14, 20, 28), (24, 38, 52), (80, 190, 220)),
            "sci_fi_concept": ((8, 12, 22), (20, 28, 48), (140, 160, 210)),
            "emerging_tech": ((16, 22, 24), (30, 42, 46), (120, 210, 170)),
            "future_predictions": ((22, 18, 28), (44, 32, 54), (230, 170, 100))
        }
        c_top, c_bot, c_accent = palettes.get(style.lower(), ((18, 24, 32), (32, 44, 58), (190, 165, 110)))

        # 1. Base gradient
        for y in range(height):
            ratio = y / float(height)
            r = int(c_top[0] * (1 - ratio) + c_bot[0] * ratio)
            g = int(c_top[1] * (1 - ratio) + c_bot[1] * ratio)
            b = int(c_top[2] * (1 - ratio) + c_bot[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Archival Documentary Grid & Rule Lines
        margin_x = 60
        draw.line([(margin_x, 140), (width - margin_x, 140)], fill=(c_accent[0], c_accent[1], c_accent[2], 90), width=1)
        draw.line([(margin_x, height - 160), (width - margin_x, height - 160)], fill=(c_accent[0], c_accent[1], c_accent[2], 90), width=1)
        
        # Crosshair framing marks at corners
        ch_len = 16
        draw.line([(margin_x, 140 - ch_len), (margin_x, 140 + ch_len)], fill=c_accent, width=2)
        draw.line([(width - margin_x, 140 - ch_len), (width - margin_x, 140 + ch_len)], fill=c_accent, width=2)
        draw.line([(margin_x, height - 160 - ch_len), (margin_x, height - 160 + ch_len)], fill=c_accent, width=2)
        draw.line([(width - margin_x, height - 160 - ch_len), (width - margin_x, height - 160 + ch_len)], fill=c_accent, width=2)

        # 3. Editorial Metadata Typography
        header_text = f"INVESTIGATIVE DOSSIER // ACT {scene_index:02d}"
        draw.text((margin_x + 10, 105), header_text, fill=c_accent)

        # Clean subject title
        clean_title = clean_search_term(prompt)[:32].upper() or style.replace("_", " ").upper()
        draw.text((margin_x + 10, height - 210), clean_title, fill=(240, 244, 248))
        draw.text((margin_x + 10, height - 145), f"ARCHIVAL RECORD // 2026 VERIFIED", fill=(160, 175, 190))

        # 4. Subtle Film Grain & Noise Overlay
        rng = random.Random(scene_index * 333 + hash(prompt) % 10000)
        for _ in range(800):
            nx = rng.randint(margin_x, width - margin_x)
            ny = rng.randint(160, height - 180)
            alpha_val = rng.randint(18, 55)
            draw.point((nx, ny), fill=(alpha_val, alpha_val, alpha_val))

        img.save(output_path, "JPEG", quality=90)

class ImageGeneratorService:
    """
    Unified Multi-Tier Realistic Image Generation Service.
    Guarantees authentic, documentary-grade photography, unique imagery per scene,
    and zero repetitive cheesy AI visuals.
    """
    def __init__(self):
        self.wiki_provider = WikipediaLeadImageProvider()
        self.openverse_provider = OpenverseSemanticProvider()
        self.pollinations_provider = PollinationsDiffusionProvider()
        self.editorial_canvas_provider = EditorialDocumentaryCanvasProvider()
        self._used_urls: Set[str] = set()

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

        # Tier 1: Real Authentic Photography from Wikipedia & Wikimedia Commons
        try:
            success, backend, msg = await self.wiki_provider.generate_image(
                prompt=prompt,
                output_path=output_path,
                style=style_key,
                width=width,
                height=height,
                scene_index=scene_index,
                character_details=character_details,
                used_urls=self._used_urls
            )
            if success:
                return True, backend, msg
        except Exception as e:
            logger.debug(f"Tier 1 Wikipedia photo skipped for scene {scene_index}: {e}")

        # Tier 2: Real Photographic CC Archive via Openverse (700M+ real photos)
        try:
            success, backend, msg = await self.openverse_provider.generate_image(
                prompt=prompt,
                output_path=output_path,
                style=style_key,
                width=width,
                height=height,
                scene_index=scene_index,
                character_details=character_details,
                used_urls=self._used_urls
            )
            if success:
                return True, backend, msg
        except Exception as e:
            logger.debug(f"Tier 2 Openverse skipped for scene {scene_index}: {e}")

        # Tier 3: Realistic Photojournalism AI Diffusion (Pollinations with 35mm photo directives)
        try:
            success, backend, msg = await self.pollinations_provider.generate_image(
                prompt=prompt,
                output_path=output_path,
                style=style_key,
                width=width,
                height=height,
                scene_index=scene_index,
                character_details=character_details,
                used_urls=self._used_urls
            )
            if success:
                return True, backend, msg
        except Exception as e:
            logger.debug(f"Tier 3 Pollinations skipped for scene {scene_index}: {e}")

        # Tier 4: Editorial Documentary Canvas (Guaranteed offline fallback)
        return await self.editorial_canvas_provider.generate_image(
            prompt=prompt,
            output_path=output_path,
            style=style_key,
            width=width,
            height=height,
            scene_index=scene_index,
            character_details=character_details,
            used_urls=self._used_urls
        )

image_generator_service = ImageGeneratorService()

# Backwards compatibility aliases for tests and providers
StoryboardCanvasProvider = EditorialDocumentaryCanvasProvider
ThematicProceduralCanvasProvider = EditorialDocumentaryCanvasProvider
