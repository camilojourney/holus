"""GIF encoding with gifski/gifsicle optimization and Pillow fallback.

Encodes a list of PIL Image frames into an animated GIF. Tries gifski first
for highest quality, falls back to Pillow's built-in GIF encoder. Applies
gifsicle compression if available. Enforces a 5MB size limit by reducing
fps and dimensions as needed.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

_MAX_GIF_SIZE = 5 * 1024 * 1024  # 5 MB


def encode_gif(
    frames: list[Image.Image],
    output_path: Path,
    fps: int = 10,
    optimize: bool = True,
) -> Path:
    """Encode frames into an animated GIF.

    Encoding pipeline:
    1. Try gifski (highest quality, per-frame palette).
    2. Fall back to Pillow ``save(save_all=True)`` if gifski is not installed.
    3. Optimize with gifsicle if available.
    4. If result > 5MB: retry at 8fps, then retry at 720x720.

    Args:
        frames: List of PIL Images (RGBA or RGB).
        output_path: Destination path for the GIF file.
        fps: Frames per second (default 10).
        optimize: Whether to attempt gifsicle optimization.

    Returns:
        The output path of the written GIF file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _encode_frames(frames, output_path, fps)

    if optimize:
        _optimize_gifsicle(output_path)

    # Size check — if > 5MB, try reducing fps
    if output_path.stat().st_size > _MAX_GIF_SIZE:
        logger.warning("GIF is %d bytes, reducing to 8fps", output_path.stat().st_size)
        reduced_fps = min(fps, 8)
        # Subsample frames to match reduced fps
        if reduced_fps < fps:
            ratio = reduced_fps / fps
            indices = [int(i / ratio) for i in range(int(len(frames) * ratio))]
            indices = sorted(set(indices))
            reduced_frames = [frames[i] for i in indices if i < len(frames)]
        else:
            reduced_frames = frames
        _encode_frames(reduced_frames, output_path, reduced_fps)
        if optimize:
            _optimize_gifsicle(output_path)

    # Still too large — reduce dimensions to 720x720
    if output_path.stat().st_size > _MAX_GIF_SIZE:
        logger.warning("GIF still %d bytes, reducing to 720x720", output_path.stat().st_size)
        resized = [f.resize((720, 720), Image.LANCZOS) for f in frames]  # type: ignore[attr-defined]
        _encode_frames(resized, output_path, min(fps, 8))
        if optimize:
            _optimize_gifsicle(output_path)

    logger.info("GIF encoded: %s (%d bytes)", output_path, output_path.stat().st_size)
    return output_path


def _encode_frames(frames: list[Image.Image], output_path: Path, fps: int) -> None:
    """Encode frames using gifski if available, otherwise Pillow."""
    if shutil.which("gifski"):
        _encode_gifski(frames, output_path, fps)
    else:
        _encode_pillow(frames, output_path, fps)


def _encode_gifski(frames: list[Image.Image], output_path: Path, fps: int) -> None:
    """Encode using gifski subprocess for highest quality GIF output."""
    with tempfile.TemporaryDirectory(prefix="holus_gif_") as tmpdir:
        tmp = Path(tmpdir)
        # Write frames as PNG files
        for i, frame in enumerate(frames):
            # gifski needs RGB PNGs
            rgb_frame = frame.convert("RGBA") if frame.mode != "RGBA" else frame
            rgb_frame.save(tmp / f"frame_{i:05d}.png")

        cmd = [
            "gifski",
            "--fps", str(fps),
            "--output", str(output_path),
            "--quality", "80",
        ]
        # Add all frame paths
        frame_paths = sorted(tmp.glob("frame_*.png"))
        cmd.extend(str(p) for p in frame_paths)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.warning("gifski failed (%s), falling back to Pillow", result.stderr.strip())
            _encode_pillow(frames, output_path, fps)


def _encode_pillow(frames: list[Image.Image], output_path: Path, fps: int) -> None:
    """Encode using Pillow's built-in GIF encoder."""
    if not frames:
        msg = "No frames to encode"
        raise ValueError(msg)

    # Convert RGBA to P (palette) mode for GIF compatibility
    converted: list[Image.Image] = []
    for frame in frames:
        rgb = frame.convert("RGB") if frame.mode != "RGB" else frame
        quantized = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        converted.append(quantized)

    duration_ms = int(1000 / fps)
    converted[0].save(
        str(output_path),
        save_all=True,
        append_images=converted[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )


def _optimize_gifsicle(output_path: Path) -> None:
    """Run gifsicle lossy compression if available."""
    if not shutil.which("gifsicle"):
        logger.debug("gifsicle not found, skipping optimization")
        return

    if not output_path.exists():
        return

    try:
        result = subprocess.run(
            ["gifsicle", "--lossy=80", "-O3", str(output_path), "-o", str(output_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("gifsicle optimization failed: %s", result.stderr.strip())
    except subprocess.TimeoutExpired:
        logger.warning("gifsicle timed out")
