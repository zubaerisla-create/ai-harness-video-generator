import os
import random
import logging
import subprocess
from pathlib import Path
from typing import Optional, List
from backend.app.config import settings

logger = logging.getLogger("ai_harness.music_library")

class MusicLibraryService:
    def __init__(self):
        self.music_dir = Path(settings.ASSETS_DIR)
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.sfx_dir = self.music_dir / "sfx"
        self.sfx_dir.mkdir(parents=True, exist_ok=True)

    def get_background_track(self, style: str, target_duration: float, output_path: Path) -> Optional[Path]:
        """
        Returns a high-quality cinematic background music bed matching the business/tech pillar.
        Loops user-provided tracks if present, or synthesizes a pristine ambient audio bed.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        existing_tracks = list(self.music_dir.glob("*.mp3")) + list(self.music_dir.glob("*.wav"))
        # Exclude sfx files
        existing_tracks = [t for t in existing_tracks if "sfx" not in str(t).lower()]
        matching = [t for t in existing_tracks if style.lower() in t.stem.lower()]

        selected_track = random.choice(matching) if matching else (random.choice(existing_tracks) if existing_tracks else None)

        if selected_track:
            try:
                cmd = [
                    "ffmpeg", "-y",
                    "-stream_loop", "-1",
                    "-i", str(selected_track),
                    "-t", str(target_duration),
                    "-af", f"afade=t=out:st={max(0, target_duration - 3.0)}:d=3.0",
                    str(output_path)
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                return output_path
            except Exception as e:
                logger.warning(f"Failed to loop existing music track: {e}")

        # High-grade atmospheric synthesizer bed
        return self._generate_cinematic_music_bed(style, target_duration, output_path)

    def _generate_cinematic_music_bed(self, style: str, duration: float, output_path: Path) -> Path:
        """
        Synthesizes a deep, modern cinematic ambient audio bed with low-frequency warmth
        and gentle harmonic pulses (no childish or cartoon frequencies).
        """
        style_key = style.lower()
        if "business" in style_key:
            # Deep authoritative corporate pulse (A Minor / C Major warm bass)
            f1, f2, f3 = 110.0, 164.8, 220.0
        elif "ai" in style_key:
            # High-tech resonant cybernetic pad
            f1, f2, f3 = 130.8, 196.0, 261.6
        elif "sci_fi" in style_key or "scifi" in style_key:
            # Deep interstellar cosmic drone (Low D / F / A)
            f1, f2, f3 = 73.4, 110.0, 146.8
        elif "emerging" in style_key:
            # Clean precision tech harmonics
            f1, f2, f3 = 146.8, 220.0, 293.6
        else:
            # Uplifting future documentary pad
            f1, f2, f3 = 174.6, 261.6, 349.2

        fade_out = max(0.0, duration - 2.5)
        
        # Audio filter creating warm ambient drone with slow 0.5Hz volume pulsation
        synth_expr = (
            f"aevalsrc='(0.09*sin(2*PI*{f1}*t) + 0.06*sin(2*PI*{f2}*t) + 0.04*sin(2*PI*{f3}*t)) * (0.8 + 0.2*sin(2*PI*0.35*t))':d={duration},"
            f"lowpass=f=380,volume=0.35,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out}:d=2.5"
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", synth_expr,
            "-ar", "44100",
            "-ac", "2",
            str(output_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            logger.error(f"Failed to generate music bed: {e}")
        return output_path

    def generate_transition_whoosh(self, output_path: Path) -> Path:
        """
        Generates a 0.5-second cinematic whoosh sound effect for scene transitions.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        # Bandpass swept noise simulating a fast camera whip-pan / whoosh
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "anoisesrc=d=0.5:c=pink:r=44100",
            "-af", "bandpass=f=1200:w=800,afade=t=in:st=0:d=0.25,afade=t=out:st=0.25:d=0.25,volume=0.45",
            str(output_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            logger.debug(f"Whoosh generation fallback: {e}")
        return output_path

    def generate_impact_drop(self, output_path: Path) -> Path:
        """
        Generates a 0.8-second deep cinematic sub-bass impact for opening hooks.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            return output_path

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "aevalsrc='0.35*sin(2*PI*max(35, 120-110*t)*t)':d=0.8",
            "-af", "lowpass=f=160,afade=t=in:st=0:d=0.05,afade=t=out:st=0.1:d=0.7,volume=0.55",
            str(output_path)
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            logger.debug(f"Impact drop generation fallback: {e}")
        return output_path

    def generate_timeline_sfx(self, scene_start_times: List[float], total_duration: float, output_path: Path) -> Optional[Path]:
        """
        Synthesizes a master sound effects track synchronized to scene transition cuts:
        - Opening Hook: Deep sub-bass drop impact.
        - Each subsequent scene cut: Fast cinematic whoosh transition.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        whoosh = self.generate_transition_whoosh(self.sfx_dir / "whoosh.wav")
        impact = self.generate_impact_drop(self.sfx_dir / "impact.wav")

        if not whoosh.exists() or not impact.exists():
            return None

        # Build FFmpeg adelay filter chain
        inputs = ["-i", str(impact)]
        filter_parts = ["[0:a]adelay=0|0[a0]"]
        mix_inputs = ["[a0]"]

        # Add whoosh at each transition point (excluding first scene at 0.0s)
        transition_points = [t for t in scene_start_times[1:] if t < total_duration - 1.0]
        for idx, t_sec in enumerate(transition_points):
            delay_ms = max(0, int((t_sec - 0.2) * 1000))
            in_idx = idx + 1
            inputs.extend(["-i", str(whoosh)])
            filter_parts.append(f"[{in_idx}:a]adelay={delay_ms}|{delay_ms}[a{in_idx}]")
            mix_inputs.append(f"[a{in_idx}]")

        filter_parts.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[out]")

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", "[out]",
            "-t", str(total_duration),
            "-ar", "44100",
            "-ac", "2",
            str(output_path)
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return output_path
        except Exception as e:
            logger.warning(f"Timeline SFX assembly failed: {e}")
            return None

