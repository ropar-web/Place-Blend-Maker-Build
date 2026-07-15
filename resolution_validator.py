from __future__ import annotations

from dataclasses import dataclass, asdict
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

from PIL import Image


A_SERIES_RATIO = 1 / (2 ** 0.5)  # width / height for portrait A-series


@dataclass
class PrintValidationResult:
    target_print_standard: str
    target_width_px: int
    target_height_px: int
    source_width_px: int
    source_height_px: int
    final_width_px: int
    final_height_px: int
    source_megapixels: float
    final_megapixels: float
    effective_dpi_width: float
    effective_dpi_height: float
    effective_dpi: float
    source_aspect_ratio: float
    target_aspect_ratio: float
    aspect_ratio_difference_percent: float
    processing_method: str
    classification: str
    passes_minimum_240_dpi: bool
    passes_target_300_dpi: bool
    native_target_met: bool
    final_target_pixels_met: bool
    warnings: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def read_image_size(image_input: Any) -> Tuple[int, int]:
    """
    Accepts a file path, Streamlit UploadedFile, bytes, bytearray, or BytesIO.
    """
    if isinstance(image_input, (bytes, bytearray)):
        image_input = BytesIO(image_input)

    if hasattr(image_input, "seek"):
        image_input.seek(0)

    with Image.open(image_input) as image:
        return int(image.width), int(image.height)


def _megapixels(width: int, height: int) -> float:
    return round((width * height) / 1_000_000, 2)


def classify_print_output(
    *,
    source_size: Tuple[int, int],
    final_size: Optional[Tuple[int, int]] = None,
    physical_size_mm: Tuple[float, float] = (594.0, 841.0),
    target_size_px: Tuple[int, int] = (7016, 9933),
    minimum_dpi: int = 240,
    target_dpi: int = 300,
    processing_method: str = "none",
    target_print_standard: str = "A1",
) -> PrintValidationResult:
    """
    processing_method must be one of:
      - none
      - ai_super_resolution
      - standard_interpolation
      - metadata_only
      - unknown
    """
    allowed = {
        "none",
        "ai_super_resolution",
        "standard_interpolation",
        "metadata_only",
        "unknown",
    }
    if processing_method not in allowed:
        raise ValueError(f"Unsupported processing_method: {processing_method}")

    source_w, source_h = source_size
    final_w, final_h = final_size or source_size
    target_w, target_h = target_size_px
    physical_w_mm, physical_h_mm = physical_size_mm

    if min(source_w, source_h, final_w, final_h) <= 0:
        raise ValueError("Pixel dimensions must be positive.")

    dpi_w = final_w / (physical_w_mm / 25.4)
    dpi_h = final_h / (physical_h_mm / 25.4)
    effective_dpi = min(dpi_w, dpi_h)

    source_ratio = source_w / source_h
    target_ratio = target_w / target_h
    ratio_diff = abs(source_ratio - target_ratio) / target_ratio * 100

    native_target_met = source_w >= target_w and source_h >= target_h
    final_target_met = final_w >= target_w and final_h >= target_h
    warnings: list[str] = []

    if ratio_diff > 0.25:
        warnings.append(
            "The source aspect ratio differs from the A-series target by more than 0.25%. "
            "Crop or pad without stretching."
        )

    if processing_method == "metadata_only":
        classification = "page_only"
        warnings.append(
            "DPI metadata was changed without adding real pixels. "
            "This is not a genuine high-resolution A1 output."
        )
    elif native_target_met and processing_method in {"none", "unknown"}:
        classification = "native"
    elif final_target_met and processing_method == "ai_super_resolution":
        classification = "ai_upscaled"
    elif final_target_met and processing_method == "standard_interpolation":
        classification = "standard_resized"
        warnings.append(
            "The file reaches the target dimensions through ordinary interpolation, "
            "not genuine AI super-resolution."
        )
    else:
        classification = "page_only"
        if not final_target_met:
            warnings.append(
                f"Final artwork is {final_w}×{final_h}px, below the "
                f"{target_w}×{target_h}px target."
            )

    if effective_dpi < minimum_dpi:
        warnings.append(
            f"Effective resolution is only {effective_dpi:.1f} DPI at "
            f"{physical_w_mm:g}×{physical_h_mm:g} mm."
        )
    elif effective_dpi < target_dpi:
        warnings.append(
            f"Effective resolution is {effective_dpi:.1f} DPI: acceptable at the "
            f"{minimum_dpi} DPI minimum, but below the {target_dpi} DPI target."
        )

    return PrintValidationResult(
        target_print_standard=target_print_standard,
        target_width_px=target_w,
        target_height_px=target_h,
        source_width_px=source_w,
        source_height_px=source_h,
        final_width_px=final_w,
        final_height_px=final_h,
        source_megapixels=_megapixels(source_w, source_h),
        final_megapixels=_megapixels(final_w, final_h),
        effective_dpi_width=round(dpi_w, 1),
        effective_dpi_height=round(dpi_h, 1),
        effective_dpi=round(effective_dpi, 1),
        source_aspect_ratio=round(source_ratio, 6),
        target_aspect_ratio=round(target_ratio, 6),
        aspect_ratio_difference_percent=round(ratio_diff, 3),
        processing_method=processing_method,
        classification=classification,
        passes_minimum_240_dpi=effective_dpi >= minimum_dpi,
        passes_target_300_dpi=effective_dpi >= target_dpi,
        native_target_met=native_target_met,
        final_target_pixels_met=final_target_met,
        warnings=warnings,
    )


def validate_uploaded_artwork(
    source_image: Any,
    *,
    final_image: Any | None = None,
    processing_method: str = "none",
) -> PrintValidationResult:
    source_size = read_image_size(source_image)
    final_size = read_image_size(final_image) if final_image is not None else source_size

    return classify_print_output(
        source_size=source_size,
        final_size=final_size,
        processing_method=processing_method,
    )


def classification_label(classification: str) -> str:
    labels = {
        "native": "NATIVE A1",
        "ai_upscaled": "AI UPSCALED A1",
        "standard_resized": "STANDARD RESIZED A1",
        "page_only": "A1 PAGE ONLY — ARTWORK BELOW TARGET",
    }
    return labels.get(classification, classification.upper())
