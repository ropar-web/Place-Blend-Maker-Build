from __future__ import annotations

"""Lightweight local neural style transfer for the Place Blend Maker.

The engine uses the feature layers of torchvision's pretrained SqueezeNet 1.1.
The 4.7 MB ImageNet checkpoint is downloaded by torchvision on the first neural
run, then cached by PyTorch. No paid image-generation API is called.
"""

from functools import lru_cache
from typing import Callable

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ProgressCallback = Callable[[float, str], None]

# SqueezeNet feature block indices. These are stable for torchvision's
# SqueezeNet 1.1 feature extractor.
STYLE_LAYERS = (1, 3, 4, 6, 7, 9, 10, 11, 12)
CONTENT_LAYER = 8


class LocalStyleTransferError(RuntimeError):
    """Raised when local style transfer cannot run."""


def _lazy_torch():
    try:
        import torch
        import torch.nn.functional as F
        from torchvision.models import SqueezeNet1_1_Weights, squeezenet1_1
    except Exception as exc:  # pragma: no cover - depends on deployment packages
        raise LocalStyleTransferError(
            "Local neural style transfer needs torch and torchvision. "
            "Check requirements.txt and redeploy the app."
        ) from exc
    return torch, F, SqueezeNet1_1_Weights, squeezenet1_1


@lru_cache(maxsize=2)
def load_feature_extractor(use_pretrained: bool = True):
    """Load and cache the lightweight feature extractor.

    use_pretrained=False exists only for local smoke tests. The app always uses
    pretrained weights because untrained features cannot produce useful art.
    """

    torch, _, weights_enum, squeezenet1_1 = _lazy_torch()
    try:
        weights = weights_enum.DEFAULT if use_pretrained else None
        model = squeezenet1_1(weights=weights, progress=False).features.eval()
    except Exception as exc:
        raise LocalStyleTransferError(
            "The local model could not be loaded. On the first neural run the app "
            "downloads a small PyTorch checkpoint. Check the internet connection, "
            "then try again."
        ) from exc

    for parameter in model.parameters():
        parameter.requires_grad_(False)

    torch.set_num_threads(max(1, min(2, torch.get_num_threads())))
    return model


def _resize_for_work(image: Image.Image, max_side: int) -> tuple[Image.Image, tuple[int, int]]:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    original_size = rgb.size
    if max(rgb.size) <= max_side:
        return rgb.copy(), original_size
    scale = max_side / max(rgb.size)
    resized = rgb.resize(
        (max(32, round(rgb.width * scale)), max(32, round(rgb.height * scale))),
        Image.Resampling.LANCZOS,
    )
    return resized, original_size


def _pil_to_tensor(image: Image.Image, torch):
    arr = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    return torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).contiguous()


def _tensor_to_pil(tensor, original_size: tuple[int, int]) -> Image.Image:
    arr = (
        tensor.detach()
        .clamp(0.0, 1.0)
        .squeeze(0)
        .permute(1, 2, 0)
        .cpu()
        .numpy()
    )
    out = Image.fromarray(np.uint8(np.clip(arr * 255.0, 0, 255)), "RGB")
    if out.size != original_size:
        out = out.resize(original_size, Image.Resampling.LANCZOS)
    return out


def _normalise(x, torch):
    mean = torch.tensor((0.485, 0.456, 0.406), dtype=x.dtype, device=x.device).view(1, 3, 1, 1)
    std = torch.tensor((0.229, 0.224, 0.225), dtype=x.dtype, device=x.device).view(1, 3, 1, 1)
    return (x - mean) / std


def _extract_features(x, model, torch) -> dict[int, object]:
    outputs: dict[int, object] = {}
    current = _normalise(x, torch)
    wanted = set(STYLE_LAYERS) | {CONTENT_LAYER}
    for index, layer in enumerate(model):
        current = layer(current)
        if index in wanted:
            outputs[index] = current
    return outputs


def _gram_matrix(features, torch):
    n, c, h, w = features.shape
    flattened = features.reshape(n, c, h * w)
    gram = torch.bmm(flattened, flattened.transpose(1, 2))
    return gram / max(1, c * h * w)


def _total_variation(x, torch):
    horizontal = torch.mean(torch.abs(x[:, :, :, 1:] - x[:, :, :, :-1]))
    vertical = torch.mean(torch.abs(x[:, :, 1:, :] - x[:, :, :-1, :]))
    return horizontal + vertical


def _match_colour_statistics(source: Image.Image, reference: Image.Image, amount: float) -> Image.Image:
    """Gently align RGB colour statistics to the reference image."""

    amount = float(np.clip(amount, 0.0, 1.0))
    if amount <= 0:
        return source

    src = np.asarray(source.convert("RGB"), dtype=np.float32)
    ref = np.asarray(reference.convert("RGB"), dtype=np.float32)
    src_flat = src.reshape(-1, 3)
    ref_flat = ref.reshape(-1, 3)

    src_mean = src_flat.mean(axis=0)
    ref_mean = ref_flat.mean(axis=0)
    src_std = np.maximum(src_flat.std(axis=0), 1.0)
    ref_std = np.maximum(ref_flat.std(axis=0), 1.0)

    matched = (src - src_mean) * (ref_std / src_std) + ref_mean
    mixed = src * (1.0 - amount) + matched * amount
    return Image.fromarray(np.uint8(np.clip(mixed, 0, 255)), "RGB")


def apply_art_finish(image: Image.Image, preset: str, intensity: float = 0.65) -> Image.Image:
    """Apply a deterministic travel-art finish after neural transfer."""

    intensity = float(np.clip(intensity, 0.0, 1.0))
    out = image.convert("RGB")

    settings = {
        "Painterly Travel Poster": dict(brightness=1.04, contrast=1.14, colour=1.26, warmth=0.16, poster=0.20, sharp=1.15),
        "Sunny Mediterranean": dict(brightness=1.08, contrast=1.08, colour=1.30, warmth=0.24, poster=0.10, sharp=1.00),
        "Bold Landmark Art": dict(brightness=1.02, contrast=1.22, colour=1.38, warmth=0.12, poster=0.28, sharp=1.35),
        "Soft Painted Photo": dict(brightness=1.05, contrast=1.02, colour=1.10, warmth=0.10, poster=0.04, sharp=0.75),
        "Vintage Travel Postcard": dict(brightness=1.02, contrast=1.05, colour=0.86, warmth=0.32, poster=0.14, sharp=0.85),
    }
    cfg = settings.get(preset, settings["Painterly Travel Poster"])

    def mix_factor(target: float) -> float:
        return 1.0 + (target - 1.0) * intensity

    out = ImageEnhance.Brightness(out).enhance(mix_factor(cfg["brightness"]))
    out = ImageEnhance.Contrast(out).enhance(mix_factor(cfg["contrast"]))
    out = ImageEnhance.Color(out).enhance(mix_factor(cfg["colour"]))

    arr = np.asarray(out, dtype=np.float32)
    warmth = cfg["warmth"] * intensity
    arr[:, :, 0] *= 1.0 + 0.18 * warmth
    arr[:, :, 1] *= 1.0 + 0.05 * warmth
    arr[:, :, 2] *= 1.0 - 0.16 * warmth
    out = Image.fromarray(np.uint8(np.clip(arr, 0, 255)), "RGB")

    poster_amount = cfg["poster"] * intensity
    if poster_amount > 0.01:
        poster = ImageOps.posterize(out, bits=6)
        out = Image.blend(out, poster, poster_amount)

    sharp_amount = cfg["sharp"] * intensity
    out = out.filter(
        ImageFilter.UnsharpMask(
            radius=1.4,
            percent=max(20, int(60 + 90 * sharp_amount)),
            threshold=3,
        )
    )

    if preset == "Vintage Travel Postcard":
        # Deterministic fine paper grain.
        rng = np.random.default_rng(20260708)
        arr = np.asarray(out, dtype=np.int16)
        grain = rng.normal(0, 4.0 * intensity, size=arr.shape[:2]).astype(np.int16)
        arr = arr + grain[:, :, None]
        out = Image.fromarray(np.uint8(np.clip(arr, 0, 255)), "RGB")

    return out


def fast_travel_finish(
    content_image: Image.Image,
    preset: str,
    style_strength: int,
    reference_image: Image.Image | None = None,
    palette_consistency: bool = True,
) -> Image.Image:
    """A quick non-neural fallback that keeps the app usable on low resources."""

    amount = float(np.clip(style_strength / 100.0, 0.0, 1.0))
    original = ImageOps.exif_transpose(content_image).convert("RGB")
    smoothed = original.filter(ImageFilter.SMOOTH_MORE)
    detailed = smoothed.filter(ImageFilter.DETAIL)
    out = Image.blend(original, detailed, 0.20 + 0.45 * amount)
    if palette_consistency and reference_image is not None:
        out = _match_colour_statistics(out, reference_image, 0.18 + 0.34 * amount)
    return apply_art_finish(out, preset, amount)


def neural_style_transfer(
    content_image: Image.Image,
    style_image: Image.Image,
    *,
    steps: int = 35,
    max_side: int = 320,
    style_strength: int = 62,
    preserve_colour_palette: bool = True,
    preset: str = "Painterly Travel Poster",
    progress_callback: ProgressCallback | None = None,
    use_pretrained: bool = True,
) -> Image.Image:
    """Transfer visual style from one image to another on the local CPU.

    The algorithm keeps the content/layout of the source photo. It transfers
    texture and colour statistics; it does not add missing landmarks or invent
    a new composition.
    """

    torch, F, _, _ = _lazy_torch()
    model = load_feature_extractor(use_pretrained=use_pretrained)
    device = torch.device("cpu")
    model = model.to(device)

    content_work, original_size = _resize_for_work(content_image, max_side=max_side)
    style_work, _ = _resize_for_work(style_image, max_side=max_side)

    content = _pil_to_tensor(content_work, torch).to(device)
    style = _pil_to_tensor(style_work, torch).to(device)

    with torch.no_grad():
        content_features = _extract_features(content, model, torch)
        style_features = _extract_features(style, model, torch)
        content_target = content_features[CONTENT_LAYER].detach()
        style_targets = {
            layer: _gram_matrix(style_features[layer], torch).detach()
            for layer in STYLE_LAYERS
        }

    strength = float(np.clip(style_strength / 100.0, 0.0, 1.0))
    generated = content.clone().detach().requires_grad_(True)
    optimiser = torch.optim.Adam([generated], lr=0.035)

    # Normalised Gram losses are small, so the style multiplier is deliberately
    # larger than the content multiplier.
    style_weight = 35_000.0 + 260_000.0 * (strength ** 1.7)
    content_weight = 1.0 + 1.4 * (1.0 - strength)
    tv_weight = 2.0e-5
    steps = max(5, int(steps))

    try:
        for step in range(steps):
            optimiser.zero_grad(set_to_none=True)
            generated_features = _extract_features(generated, model, torch)

            content_loss = F.mse_loss(generated_features[CONTENT_LAYER], content_target)
            style_loss = torch.zeros((), dtype=generated.dtype, device=device)
            for layer in STYLE_LAYERS:
                style_loss = style_loss + F.mse_loss(
                    _gram_matrix(generated_features[layer], torch),
                    style_targets[layer],
                )
            style_loss = style_loss / len(STYLE_LAYERS)
            tv_loss = _total_variation(generated, torch)

            loss = content_weight * content_loss + style_weight * style_loss + tv_weight * tv_loss
            loss.backward()
            optimiser.step()
            with torch.no_grad():
                generated.clamp_(0.0, 1.0)

            if progress_callback and (step == 0 or (step + 1) % max(1, steps // 12) == 0 or step + 1 == steps):
                progress_callback((step + 1) / steps, f"Style pass {step + 1} of {steps}")
    except RuntimeError as exc:
        message = str(exc).lower()
        if "out of memory" in message or "memory" in message:
            raise LocalStyleTransferError(
                "The local style model ran out of memory. Choose Draft quality or upload a smaller image."
            ) from exc
        raise LocalStyleTransferError(f"The local style model stopped: {exc}") from exc

    neural = _tensor_to_pil(generated, original_size=original_size)
    original = ImageOps.exif_transpose(content_image).convert("RGB")
    if original.size != neural.size:
        original = original.resize(neural.size, Image.Resampling.LANCZOS)

    # Blending some original detail back in gives clearer buildings and signs.
    neural_alpha = 0.42 + 0.52 * strength
    result = Image.blend(original, neural, float(np.clip(neural_alpha, 0.0, 1.0)))

    if preserve_colour_palette:
        result = _match_colour_statistics(result, style_image, 0.22 + 0.38 * strength)

    result = apply_art_finish(result, preset, intensity=0.45 + 0.55 * strength)
    return result
