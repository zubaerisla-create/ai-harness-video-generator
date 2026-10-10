import os
import sys
import wave
import subprocess
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from backend.app.config import settings

logger = logging.getLogger("ai_harness.voice_generator")

class VoiceGenerator:
    def __init__(self):
        self.provider = settings.TTS_PROVIDER
        self.model_path = Path(settings.PIPER_MODEL_PATH)
        self.config_path = Path(settings.PIPER_CONFIG_PATH)

    async def generate_scene_narration(
        self,
        text: str,
        output_path: Path,
        voice_override: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Generates spoken audio for scene narration.
        Returns: (success: bool, duration_seconds: float, message: str)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not text or not text.strip():
            logger.warning("Empty text passed for narration generation")
            return False, 0.0, "Empty narration text"

        # Try Piper if configured and available
        if self.provider == "piper":
            success, dur, msg = await self._generate_piper(text, output_path, voice_override)
            if success:
                return True, dur, msg
            logger.warning(f"Piper failed ({msg}), falling back to edge-tts if installed")

        # Fallback to edge-tts
        success, dur, msg = await self._generate_edge_tts(text, output_path, voice_override)
        if success:
            return True, dur, msg

        # Final fallback: generate a silent wav of estimated duration so the pipeline does not completely halt
        logger.error(f"All TTS providers failed: {msg}. Generating synthetic timed silence.")
        est_words = len(text.split())
        est_dur = max(3.0, est_words / 2.3)
        self._generate_silence(output_path, est_dur)
        return True, est_dur, "Generated timed silence (TTS offline fallback)"

    async def _generate_piper(
        self,
        text: str,
        output_wav: Path,
        voice_override: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Runs Piper TTS locally via subprocess.
        Piper model and config must exist on disk.
        """
        model_file = self.model_path
        if not model_file.exists():
            return False, 0.0, f"Piper model not found at {model_file}"

        try:
            cmd = [
                sys.executable, "-m", "piper",
                "--model", str(model_file),
                "--output_file", str(output_wav)
            ]
            if self.config_path.exists():
                cmd.extend(["--config", str(self.config_path)])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate(input=text.encode("utf-8"))

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace")
                return False, 0.0, f"Piper exit code {proc.returncode}: {err_msg}"

            dur = self.get_audio_duration(output_wav)
            if dur <= 0:
                return False, 0.0, "Piper generated invalid/empty audio file"

            return True, dur, "Piper audio generated successfully"
        except Exception as e:
            return False, 0.0, f"Piper execution error: {str(e)}"

    async def _generate_edge_tts(
        self,
        text: str,
        output_path: Path,
        voice_override: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Runs edge-tts via Python library or CLI as high-fidelity fallback.
        """
        try:
            import edge_tts
            voice = voice_override or "en-US-ChristopherNeural"
            communicate = edge_tts.Communicate(text, voice)
            
            # Temporary mp3 output
            temp_mp3 = output_path.with_suffix(".mp3")
            await communicate.save(str(temp_mp3))

            # Convert to standard 24kHz/44.1kHz WAV for video assembly consistency
            convert_cmd = [
                "ffmpeg", "-y", "-i", str(temp_mp3),
                "-ac", "2", "-ar", "44100", str(output_path)
            ]
            proc = await asyncio.create_subprocess_exec(
                *convert_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()

            if temp_mp3.exists() and temp_mp3 != output_path:
                try:
                    temp_mp3.unlink()
                except Exception:
                    pass

            dur = self.get_audio_duration(output_path)
            if dur > 0:
                return True, dur, "Edge-TTS audio generated successfully"
            return False, 0.0, "Failed to measure generated audio duration"
        except ImportError:
            return False, 0.0, "edge-tts python package not installed"
        except Exception as e:
            return False, 0.0, f"edge-tts error: {str(e)}"

    def get_audio_duration(self, audio_file: Path) -> float:
        """
        Accurately measures audio duration in seconds using wave module or ffprobe.
        """
        if not audio_file.exists():
            return 0.0

        # Try standard wave module first (for WAV files)
        try:
            with wave.open(str(audio_file), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return round(frames / float(rate), 3)
        except Exception:
            pass

        # Fallback to ffprobe
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_file)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0:
                return round(float(res.stdout.strip()), 3)
        except Exception as e:
            logger.warning(f"ffprobe duration measurement failed for {audio_file}: {e}")

        return 0.0

    def _generate_silence(self, output_wav: Path, duration_seconds: float):
        """
        Generates standard 44.1kHz silent WAV file using ffmpeg or wave.
        """
        try:
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"anullsrc=r=44100:cl=stereo", "-t", str(duration_seconds),
                str(output_wav)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except Exception as e:
            logger.error(f"Failed to generate synthetic silence: {e}")
