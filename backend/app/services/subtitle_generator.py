import re
from pathlib import Path
from typing import List, Dict, Any

class SubtitleGenerator:
    """
    Generates high-retention synchronized subtitles in both SRT and ASS formats.
    Engineered specifically for Facebook Reels & YouTube Shorts algorithms:
    - High-visibility typography with solid contrast strokes.
    - Optimal vertical safe zone (avoiding bottom captions and top header UI).
    - Rapid 3 to 5-word rhythmic subtitle cues matching modern mobile viewer attention.
    - ZERO unwanted headings ('Act 1', 'Scene 1', etc.).
    """

    def generate_srt(self, timed_scenes: List[Dict[str, Any]], output_path: Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        entry_idx = 1

        for scene in timed_scenes:
            start_sec = scene["start_time"]
            dur_sec = scene["duration"]
            raw_text = self._clean_narration(scene.get("narration_text", ""))
            if not raw_text:
                continue

            words = raw_text.split()
            chunk_size = 4  # 3-4 words per cue for fast, engaging reading
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            
            chunk_dur = dur_sec / max(1, len(chunks))
            for i, chunk in enumerate(chunks):
                chunk_start = start_sec + (i * chunk_dur)
                chunk_end = chunk_start + chunk_dur
                
                lines.append(str(entry_idx))
                lines.append(f"{self._format_srt_time(chunk_start)} --> {self._format_srt_time(chunk_end)}")
                lines.append(chunk)
                lines.append("")
                entry_idx += 1

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path

    def generate_ass(self, timed_scenes: List[Dict[str, Any]], output_path: Path, width: int = 720, height: int = 1280) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ASS Stylesheet for Vertical 9:16 Shorts / Reels:
        # Font: DejaVu Sans Bold / Arial Black (heavy contrast)
        # PrimaryColour: &H00FFFFFF (Pure White)
        # AccentColour: &H0000E6FF (Neon Yellow highlight on alternating pulses)
        # OutlineColour: &H00000000 (Pure Solid Black outline)
        # MarginV: 200 (Lower third safe-zone: perfectly clears FB Reels & YT Shorts UI overlays)
        header = f"""[Script Info]
Title: AI Viral Shorts Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,26,&H00FFFFFF,&H0000E6FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,40,40,200,1
Style: Accent,DejaVu Sans,26,&H0000E6FF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.8,1.8,2,40,40,200,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for scene in timed_scenes:
            start_sec = scene["start_time"]
            dur_sec = scene["duration"]
            raw_text = self._clean_narration(scene.get("narration_text", ""))
            if not raw_text:
                continue

            words = raw_text.split()
            chunk_size = 4  # Snappy 3-4 word micro-cues
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            chunk_dur = dur_sec / max(1, len(chunks))

            for i, chunk in enumerate(chunks):
                chunk_start = start_sec + (i * chunk_dur)
                chunk_end = chunk_start + chunk_dur
                style_name = "Accent" if i % 2 == 1 else "Default"
                
                # Clean text for ASS dialogue event
                clean_chunk = chunk.replace("{", "\\{").replace("}", "\\}").replace("\n", " ").upper()
                event_line = f"Dialogue: 0,{self._format_ass_time(chunk_start)},{self._format_ass_time(chunk_end)},{style_name},,0,0,0,,{clean_chunk}"
                events.append(event_line)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + "\n")

        return output_path

    def _clean_narration(self, text: str) -> str:
        """Strips Act/Scene tags and unwanted headers."""
        t = str(text).strip()
        t = re.sub(r'(?i)^(act|scene)\s*\d+[:\-\.]?\s*', '', t)
        t = re.sub(r'(?i)^(voiceover|narration|narrator)[:\-\.]?\s*', '', t)
        t = t.replace('**', '').replace('*', '').replace('__', '')
        return " ".join(t.split())

    def _format_srt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _format_ass_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int(round((seconds - int(seconds)) * 100))
        return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"
