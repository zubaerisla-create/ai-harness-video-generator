import os
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from backend.app.config import settings

logger = logging.getLogger("ai_harness.video_renderer")

class VideoRenderer:
    def __init__(self):
        self.fps = settings.DEFAULT_FPS
        self.preset = "fast"
        self.crf = "22"

    async def render_scene_clip(
        self,
        image_path: Path,
        audio_path: Optional[Path],
        output_clip_path: Path,
        duration: float,
        motion_type: str = "zoom_in",
        width: int = 720,
        height: int = 1280
    ) -> bool:
        """
        Renders an individual scene video clip with Ken Burns motion effect,
        cinematic contrast enhancement, and narration audio.
        """
        output_clip_path = Path(output_clip_path)
        output_clip_path.parent.mkdir(parents=True, exist_ok=True)

        total_frames = int(max(1.0, duration) * self.fps)
        zoom_filter = self._get_motion_filter(motion_type, total_frames, width, height)
        
        # Subtle mobile OLED color grading: crisp contrast and vibrant saturation
        color_grade = "eq=contrast=1.06:saturation=1.12:brightness=0.01"
        full_vfilter = f"[0:v]{zoom_filter},{color_grade}[v]"

        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path)]

        if audio_path and audio_path.exists():
            cmd.extend(["-i", str(audio_path)])
            cmd.extend([
                "-filter_complex", full_vfilter,
                "-map", "[v]",
                "-map", "1:a",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest"
            ])
        else:
            cmd.extend([
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-filter_complex", full_vfilter,
                "-map", "[v]",
                "-map", "1:a",
                "-c:a", "aac",
                "-b:a", "192k",
                "-t", str(duration)
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", self.preset,
            "-crf", self.crf,
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            str(output_clip_path)
        ])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(f"Scene render error: {stderr.decode('utf-8', errors='replace')}")
                return False
            return True
        except Exception as e:
            logger.error(f"Failed to render scene clip: {e}")
            return False

    async def assemble_final_video(
        self,
        scene_clip_paths: List[Path],
        output_video_path: Path,
        subtitle_path: Optional[Path] = None,
        bgm_path: Optional[Path] = None,
        sfx_path: Optional[Path] = None,
        enable_bgm: bool = True,
        enable_subtitles: bool = True,
        bgm_volume: float = 0.12,
        sfx_volume: float = 0.22
    ) -> Tuple[bool, str]:
        """
        Concatenates scene clips, layers background music & sound effects (whooshes, risers),
        burns in lower-third subtitles, and produces the final broadcast-ready MP4.
        """
        output_video_path = Path(output_video_path)
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = output_video_path.parent / f"tmp_{output_video_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        concat_list_file = temp_dir / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for p in scene_clip_paths:
                safe_path = str(p.resolve()).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        intermediate_concat = temp_dir / "concat_raw.mp4"

        # Step 1: Lossless concatenation
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(intermediate_concat)
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *concat_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                return False, f"Concat failed: {stderr.decode('utf-8', errors='replace')}"

            # Step 2: Audio Layering (Speech + BGM + SFX) & Subtitle Burning
            cmd = ["ffmpeg", "-y", "-i", str(intermediate_concat)]
            input_idx = 1
            has_bgm = enable_bgm and bgm_path and bgm_path.exists()
            has_sfx = sfx_path and sfx_path.exists()

            if has_bgm:
                cmd.extend(["-i", str(bgm_path)])
                bgm_input_id = input_idx
                input_idx += 1

            if has_sfx:
                cmd.extend(["-i", str(sfx_path)])
                sfx_input_id = input_idx
                input_idx += 1

            # Subtitle filter
            video_filters = []
            if enable_subtitles and subtitle_path and subtitle_path.exists():
                sub_str = str(subtitle_path.resolve()).replace("\\", "/").replace(":", "\\:")
                if subtitle_path.suffix.lower() == ".ass":
                    video_filters.append(f"ass='{sub_str}'")
                else:
                    video_filters.append(f"subtitles='{sub_str}'")

            filter_complex_parts = []
            if video_filters:
                filter_complex_parts.append(f"[0:v]{','.join(video_filters)}[outv]")

            # Audio mixing chain
            audio_inputs = ["[0:a]"]
            if has_bgm:
                filter_complex_parts.append(f"[{bgm_input_id}:a]volume={bgm_volume}[abgm]")
                audio_inputs.append("[abgm]")
            if has_sfx:
                filter_complex_parts.append(f"[{sfx_input_id}:a]volume={sfx_volume}[asfx]")
                audio_inputs.append("[asfx]")

            if len(audio_inputs) > 1:
                amix_in = "".join(audio_inputs)
                filter_complex_parts.append(f"{amix_in}amix=inputs={len(audio_inputs)}:duration=first:dropout_transition=2[outa]")

            if filter_complex_parts:
                cmd.extend(["-filter_complex", ";".join(filter_complex_parts)])
                cmd.extend(["-map", "[outv]" if video_filters else "0:v"])
                cmd.extend(["-map", "[outa]" if len(audio_inputs) > 1 else "0:a"])
            else:
                cmd.extend(["-map", "0:v", "-map", "0:a"])

            cmd.extend([
                "-c:v", "libx264",
                "-preset", self.preset,
                "-crf", self.crf,
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_video_path)
            ])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning("Complex audio/subtitle pass failed, falling back to clean render")
                fallback_cmd = [
                    "ffmpeg", "-y", "-i", str(intermediate_concat),
                    "-c:v", "libx264", "-c:a", "aac",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(output_video_path)
                ]
                proc_fb = await asyncio.create_subprocess_exec(*fallback_cmd)
                await proc_fb.wait()
                if proc_fb.returncode != 0:
                    return False, "Failed to render fallback video"

            # Cleanup temporary working directory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

            return True, "Final video rendered successfully"

        except Exception as e:
            logger.error(f"Assembly exception: {e}")
            return False, str(e)

    def _get_motion_filter(self, motion: str, frames: int, width: int, height: int) -> str:
        """
        Ken Burns zoompan movements optimized for 9:16 vertical video.
        Uses scale=1.3x margin to eliminate pixelation.
        """
        base_scale = f"scale={int(width * 1.3)}:{int(height * 1.3)},setsar=1"

        if motion == "zoom_in":
            zp = f"zoompan=z='min(zoom+0.0015,1.26)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={self.fps}"
        elif motion == "zoom_out":
            zp = f"zoompan=z='if(lte(on,1),1.25,max(1.0,zoom-0.0015))':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={self.fps}"
        elif motion == "pan_left":
            zp = f"zoompan=z=1.16:d={frames}:x='if(lte(on,1),(iw-iw/zoom)*0.85,max(10,x-1.8))':y='(ih-ih/zoom)/2':s={width}x{height}:fps={self.fps}"
        elif motion == "pan_right":
            zp = f"zoompan=z=1.16:d={frames}:x='if(lte(on,1),10,min(iw-iw/zoom-10,x+1.8))':y='(ih-ih/zoom)/2':s={width}x{height}:fps={self.fps}"
        else: # slow_push
            zp = f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={self.fps}"

        return f"{base_scale},{zp}"
