from __future__ import annotations

"""Clean local travel-art renderer for Place Blend Maker.

Build 2.1 deliberately removes the unstable optimisation-based neural texture
transfer used in Build 2.0. The replacement runs fully locally with OpenCV,
Pillow and NumPy. It keeps landmarks recognisable while applying a coordinated
illustrated-poster finish and palette guidance from the uploaded reference.

No paid image-generation API is used.
"""

from typing import Callable

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ProgressCallback = Callable[[float, str], None]


class LocalStyleTransferError(RuntimeError):
    """Raised when local rendering cannot run."""


def _resize_for_work(image: Image.Image, max_side: int) -> tuple[Image.Image, tuple[int, int]]:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    original_size = rgb.size
    if max(rgb.size) <= max_side:
        return rgb.copy(), original_size
    scale = max_side / max(rgb.size)
    resized = rgb.resize(
        (max(64, round(rgb.width * scale)), max(64, round(rgb.height * scale))),
        Image.Resampling.LANCZOS,
    )
    return resized, original_size


def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _bgr_to_pil(image: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(np.clip(image, 0, 255).astype(np.uint8), cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb, "RGB")


def _lab_colour_transfer(source_bgr: np.ndarray, reference_bgr: np.ndarray, amount: float) -> np.ndarray:
    """Reinhard-style colour-statistics transfer in LAB colour space."""

    amount = float(np.clip(amount, 0.0, 1.0))
    if amount <= 0:
        return source_bgr

    src = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    ref = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)

    src_mean, src_std = cv2.meanStdDev(src)
    ref_mean, ref_std = cv2.meanStdDev(ref)
    src_mean = src_mean.reshape(1, 1, 3)
    src_std = np.maximum(src_std.reshape(1, 1, 3), 1.0)
    ref_mean = ref_mean.reshape(1, 1, 3)
    ref_std = np.maximum(ref_std.reshape(1, 1, 3), 1.0)

    transferred = (src - src_mean) * (ref_std / src_std) + ref_mean
    mixed = src * (1.0 - amount) + transferred * amount
    mixed = np.clip(mixed, 0, 255).astype(np.uint8)
    return cv2.cvtColor(mixed, cv2.COLOR_LAB2BGR)


def _quantise(image_bgr: np.ndarray, levels: int, amount: float) -> np.ndarray:
    levels = max(8, min(64, int(levels)))
    amount = float(np.clip(amount, 0.0, 1.0))
    if amount <= 0:
        return image_bgr
    step = max(1, 256 // levels)
    quant = ((image_bgr.astype(np.int16) // step) * step + step // 2).clip(0, 255).astype(np.uint8)
    return cv2.addWeighted(image_bgr, 1.0 - amount, quant, amount, 0)


def _clahe_luminance(image_bgr: np.ndarray, strength: float) -> np.ndarray:
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0:
        return image_bgr
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.3 + 1.7 * strength, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l)
    l = cv2.addWeighted(l, 1.0 - 0.55 * strength, enhanced_l, 0.55 * strength, 0)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def _soft_ink_edges(image_bgr: np.ndarray, edge_strength: float, detail: float) -> np.ndarray:
    """Overlay restrained warm ink lines without creating coloured speckle noise."""

    edge_strength = float(np.clip(edge_strength, 0.0, 1.0))
    if edge_strength <= 0:
        return image_bgr

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 7, 45, 45)
    low = int(45 + 40 * (1.0 - detail))
    high = int(115 + 70 * (1.0 - detail))
    edges = cv2.Canny(gray, low, high)
    edges = cv2.GaussianBlur(edges, (3, 3), 0.6)
    alpha = (edges.astype(np.float32) / 255.0) * (0.42 * edge_strength)
    alpha = alpha[:, :, None]

    # Warm dark brown rather than black, matching illustrated travel posters.
    ink = np.empty_like(image_bgr, dtype=np.float32)
    ink[:, :, 0] = 28.0   # B
    ink[:, :, 1] = 42.0   # G
    ink[:, :, 2] = 60.0   # R
    base = image_bgr.astype(np.float32)
    return np.clip(base * (1.0 - alpha) + ink * alpha, 0, 255).astype(np.uint8)


def _apply_warmth_and_colour(image: Image.Image, *, brightness: float, contrast: float,
                             saturation: float, warmth: float, sharpness: float) -> Image.Image:
    out = ImageEnhance.Brightness(image).enhance(brightness)
    out = ImageEnhance.Contrast(out).enhance(contrast)
    out = ImageEnhance.Color(out).enhance(saturation)

    arr = np.asarray(out, dtype=np.float32)
    arr[:, :, 0] *= 1.0 + 0.13 * warmth
    arr[:, :, 1] *= 1.0 + 0.035 * warmth
    arr[:, :, 2] *= 1.0 - 0.11 * warmth
    out = Image.fromarray(np.uint8(np.clip(arr, 0, 255)), "RGB")

    if sharpness > 0:
        out = out.filter(
            ImageFilter.UnsharpMask(
                radius=1.25,
                percent=int(55 + 85 * sharpness),
                threshold=4,
            )
        )
    return out


_PRESETS = {
    "Painterly Travel Poster": {
        "smooth": 0.54, "stylise": 0.28, "palette": 0.38, "quant_levels": 28,
        "quant_amount": 0.28, "edges": 0.42, "clahe": 0.44,
        "brightness": 1.035, "contrast": 1.10, "saturation": 1.22,
        "warmth": 0.24, "sharpness": 0.72,
    },
    "Sunny Mediterranean": {
        "smooth": 0.48, "stylise": 0.22, "palette": 0.42, "quant_levels": 34,
        "quant_amount": 0.20, "edges": 0.30, "clahe": 0.36,
        "brightness": 1.075, "contrast": 1.06, "saturation": 1.28,
        "warmth": 0.34, "sharpness": 0.62,
    },
    "Bold Landmark Art": {
        "smooth": 0.50, "stylise": 0.32, "palette": 0.34, "quant_levels": 22,
        "quant_amount": 0.38, "edges": 0.58, "clahe": 0.58,
        "brightness": 1.02, "contrast": 1.16, "saturation": 1.32,
        "warmth": 0.18, "sharpness": 0.88,
    },
    "Soft Painted Photo": {
        "smooth": 0.62, "stylise": 0.18, "palette": 0.25, "quant_levels": 44,
        "quant_amount": 0.10, "edges": 0.16, "clahe": 0.22,
        "brightness": 1.045, "contrast": 1.02, "saturation": 1.08,
        "warmth": 0.16, "sharpness": 0.40,
    },
    "Vintage Travel Postcard": {
        "smooth": 0.52, "stylise": 0.24, "palette": 0.34, "quant_levels": 26,
        "quant_amount": 0.28, "edges": 0.38, "clahe": 0.30,
        "brightness": 1.025, "contrast": 1.06, "saturation": 0.90,
        "warmth": 0.52, "sharpness": 0.56,
    },
}


def clean_reference_style_transfer(
    content_image: Image.Image,
    style_image: Image.Image | None,
    *,
    max_side: int = 900,
    style_strength: int = 62,
    preserve_colour_palette: bool = True,
    preset: str = "Painterly Travel Poster",
    progress_callback: ProgressCallback | None = None,
) -> Image.Image:
    """Create a clean, reference-guided illustrated travel-poster treatment.

    The source composition and landmarks remain intact. The reference guides the
    palette; the renderer supplies the clean painterly/poster finish.
    """

    try:
        work, original_size = _resize_for_work(content_image, max_side=max_side)
        strength = float(np.clip(style_strength / 100.0, 0.0, 1.0))
        cfg = _PRESETS.get(preset, _PRESETS["Painterly Travel Poster"])
        bgr = _pil_to_bgr(work)
        original_bgr = bgr.copy()

        if progress_callback:
            progress_callback(0.12, "Preserving landmark detail")

        # Edge-preserving smoothing removes camera noise while keeping architecture.
        sigma_s = 42 + 55 * cfg["smooth"] * strength
        sigma_r = 0.18 + 0.22 * cfg["smooth"] * strength
        smooth = cv2.edgePreservingFilter(
            bgr,
            flags=cv2.RECURS_FILTER,
            sigma_s=float(sigma_s),
            sigma_r=float(np.clip(sigma_r, 0.05, 0.48)),
        )

        if progress_callback:
            progress_callback(0.32, "Building the painted surface")

        # OpenCV stylisation is blended gently; it is never allowed to replace detail.
        stylised = cv2.stylization(
            bgr,
            sigma_s=float(38 + 48 * strength),
            sigma_r=float(0.16 + 0.18 * strength),
        )
        stylise_amount = cfg["stylise"] * (0.35 + 0.65 * strength)
        rendered = cv2.addWeighted(smooth, 1.0 - stylise_amount, stylised, stylise_amount, 0)

        # Re-introduce a controlled amount of original structure.
        detail_return = 0.28 + 0.24 * (1.0 - strength)
        rendered = cv2.addWeighted(rendered, 1.0 - detail_return, original_bgr, detail_return, 0)

        if progress_callback:
            progress_callback(0.52, "Matching the reference colours")

        if preserve_colour_palette and style_image is not None:
            style_work, _ = _resize_for_work(style_image, max_side=max_side)
            style_bgr = _pil_to_bgr(style_work)
            palette_amount = cfg["palette"] * (0.45 + 0.55 * strength)
            rendered = _lab_colour_transfer(rendered, style_bgr, palette_amount)

        if progress_callback:
            progress_callback(0.68, "Creating clean poster colour blocks")

        rendered = _quantise(
            rendered,
            levels=cfg["quant_levels"],
            amount=cfg["quant_amount"] * (0.35 + 0.65 * strength),
        )
        rendered = _clahe_luminance(rendered, cfg["clahe"] * (0.45 + 0.55 * strength))
        rendered = _soft_ink_edges(rendered, cfg["edges"] * strength, detail=0.72)

        if progress_callback:
            progress_callback(0.84, "Applying the final travel-poster finish")

        result = _bgr_to_pil(rendered)
        result = _apply_warmth_and_colour(
            result,
            brightness=1.0 + (cfg["brightness"] - 1.0) * strength,
            contrast=1.0 + (cfg["contrast"] - 1.0) * strength,
            saturation=1.0 + (cfg["saturation"] - 1.0) * strength,
            warmth=cfg["warmth"] * strength,
            sharpness=cfg["sharpness"] * (0.45 + 0.55 * strength),
        )

        if result.size != original_size:
            result = result.resize(original_size, Image.Resampling.LANCZOS)
            # Very light final sharpening after resize—avoids the coloured grain seen in 2.0.
            result = result.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=5))

        if progress_callback:
            progress_callback(1.0, "Finished")
        return result
    except Exception as exc:
        if isinstance(exc, LocalStyleTransferError):
            raise
        raise LocalStyleTransferError(f"The clean local art renderer stopped: {exc}") from exc


def apply_art_finish(image: Image.Image, preset: str, intensity: float = 0.65) -> Image.Image:
    """Backwards-compatible final finish helper."""
    cfg = _PRESETS.get(preset, _PRESETS["Painterly Travel Poster"])
    strength = float(np.clip(intensity, 0.0, 1.0))
    return _apply_warmth_and_colour(
        image.convert("RGB"),
        brightness=1.0 + (cfg["brightness"] - 1.0) * strength,
        contrast=1.0 + (cfg["contrast"] - 1.0) * strength,
        saturation=1.0 + (cfg["saturation"] - 1.0) * strength,
        warmth=cfg["warmth"] * strength,
        sharpness=cfg["sharpness"] * strength,
    )


def fast_travel_finish(
    content_image: Image.Image,
    preset: str,
    style_strength: int,
    reference_image: Image.Image | None = None,
    palette_consistency: bool = True,
) -> Image.Image:
    """Fast clean mode for lower-powered hosting."""
    max_side = 720
    return clean_reference_style_transfer(
        content_image,
        reference_image,
        max_side=max_side,
        style_strength=min(int(style_strength), 72),
        preserve_colour_palette=palette_consistency,
        preset=preset,
        progress_callback=None,
    )


def neural_style_transfer(
    content_image: Image.Image,
    style_image: Image.Image,
    *,
    steps: int = 35,
    max_side: int = 900,
    style_strength: int = 62,
    preserve_colour_palette: bool = True,
    preset: str = "Painterly Travel Poster",
    progress_callback: ProgressCallback | None = None,
    use_pretrained: bool = True,
) -> Image.Image:
    """Compatibility alias for projects created with Build 2.0.

    Build 2.1 no longer uses the noisy optimisation-based neural renderer.
    """
    del steps, use_pretrained
    return clean_reference_style_transfer(
        content_image,
        style_image,
        max_side=max_side,
        style_strength=style_strength,
        preserve_colour_palette=preserve_colour_palette,
        preset=preset,
        progress_callback=progress_callback,
    )
