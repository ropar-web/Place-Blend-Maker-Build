from __future__ import annotations

import hashlib
import io
import json
import math
import zipfile
from dataclasses import dataclass, asdict
from typing import Iterable

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from local_style_transfer import (
    LocalStyleTransferError,
    fast_travel_finish,
    neural_style_transfer,
)

CREAM = "#FDF6EA"
CARD = "#FFF9F0"
SAGE = "#7F946F"
TERRACOTTA = "#CF6F4A"
BROWN = "#3A2C20"
BEIGE = "#E8D9BF"
GOLD = "#D7A128"


@dataclass
class PlaceItem:
    name: str
    subtitle: str
    image_bytes: bytes
    filename: str


def _font(size: int, serif: bool = False, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str] = []
    if serif:
        candidates.extend([
            "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ])
    else:
        candidates.extend([
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ])
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _open_image(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im)
    if getattr(im, "is_animated", False):
        im.seek(0)
    return im.convert("RGB")


def _cover(im: Image.Image, size: tuple[int, int], focal_x: float = 0.5, focal_y: float = 0.5) -> Image.Image:
    w, h = size
    if im.width <= 0 or im.height <= 0:
        return Image.new("RGB", size, "white")
    scale = max(w / im.width, h / im.height)
    nw, nh = max(1, round(im.width * scale)), max(1, round(im.height * scale))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = int(np.clip((nw - w) * focal_x, 0, max(0, nw - w)))
    top = int(np.clip((nh - h) * focal_y, 0, max(0, nh - h)))
    return resized.crop((left, top, left + w, top + h))


def _contain(im: Image.Image, size: tuple[int, int], background: str = CREAM) -> Image.Image:
    canvas = Image.new("RGB", size, background)
    copy = im.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    x = (size[0] - copy.width) // 2
    y = (size[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def _enhance(im: Image.Image, brightness: float, contrast: float, colour: float, blur: float) -> Image.Image:
    out = ImageEnhance.Brightness(im).enhance(brightness)
    out = ImageEnhance.Contrast(out).enhance(contrast)
    out = ImageEnhance.Color(out).enhance(colour)
    if blur > 0:
        out = out.filter(ImageFilter.GaussianBlur(radius=blur))
    return out


def _fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, min_size: int = 18,
              serif: bool = False, bold: bool = False) -> ImageFont.ImageFont:
    size = start_size
    while size > min_size:
        f = _font(size, serif=serif, bold=bold)
        box = draw.textbbox((0, 0), text, font=f)
        if box[2] - box[0] <= max_width:
            return f
        size -= 2
    return _font(min_size, serif=serif, bold=bold)


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return m


def _soft_blend(images: list[Image.Image], size: tuple[int, int], transition: float) -> Image.Image:
    w, h = size
    prepared = [_cover(im, size) for im in images]
    x = np.arange(w, dtype=np.float32)
    centres = np.linspace(0, w - 1, len(prepared), dtype=np.float32)
    sigma = max(20.0, (w / max(1, len(prepared))) * transition)
    weights = np.stack([np.exp(-0.5 * ((x - c) / sigma) ** 2) for c in centres], axis=0)
    weights /= np.maximum(weights.sum(axis=0, keepdims=True), 1e-8)
    out = np.zeros((h, w, 3), dtype=np.float32)
    for idx, im in enumerate(prepared):
        arr = np.asarray(im, dtype=np.float32)
        out += arr * weights[idx][None, :, None]
    return Image.fromarray(np.uint8(np.clip(out, 0, 255)), "RGB")


def _panel_collage(images: list[Image.Image], size: tuple[int, int], gap: int = 8) -> Image.Image:
    w, h = size
    canvas = Image.new("RGB", size, CREAM)
    n = len(images)
    panel_w = max(1, (w - gap * (n - 1)) // n)
    x = 0
    for i, im in enumerate(images):
        width = panel_w if i < n - 1 else w - x
        panel = _cover(im, (width, h))
        canvas.paste(panel, (x, 0))
        x += width + gap
    return canvas


def _vertical_gradient(size: tuple[int, int], start_alpha: int, end_alpha: int) -> Image.Image:
    w, h = size
    grad = np.linspace(start_alpha, end_alpha, h, dtype=np.uint8)[:, None]
    a = np.repeat(grad, w, axis=1)
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 3] = a
    return Image.fromarray(rgba, "RGBA")


def _draw_title(canvas: Image.Image, title: str, subtitle: str, title_colour: str = BROWN,
                top: int = 38, max_width_ratio: float = 0.88) -> None:
    draw = ImageDraw.Draw(canvas)
    max_w = int(canvas.width * max_width_ratio)
    title_font = _fit_text(draw, title, max_w, max(44, canvas.width // 18), serif=True)
    box = draw.textbbox((0, 0), title, font=title_font)
    x = (canvas.width - (box[2] - box[0])) // 2
    draw.text((x, top), title, fill=title_colour, font=title_font)
    if subtitle:
        sub_font = _fit_text(draw, subtitle.upper(), max_w, max(18, canvas.width // 55), bold=False)
        sbox = draw.textbbox((0, 0), subtitle.upper(), font=sub_font)
        sx = (canvas.width - (sbox[2] - sbox[0])) // 2
        draw.text((sx, top + (box[3] - box[1]) + 18), subtitle.upper(), fill=title_colour, font=sub_font)


def _draw_place_labels(canvas: Image.Image, places: list[PlaceItem], bottom_margin: int = 34) -> None:
    draw = ImageDraw.Draw(canvas)
    n = len(places)
    gap = max(10, canvas.width // 100)
    total_gap = gap * (n - 1)
    box_w = max(90, (canvas.width - 2 * gap - total_gap) // n)
    box_h = max(78, canvas.height // 11)
    y = canvas.height - box_h - bottom_margin
    x = gap
    for i, place in enumerate(places):
        if i == n - 1:
            current_w = canvas.width - gap - x
        else:
            current_w = box_w
        draw.rounded_rectangle((x, y, x + current_w, y + box_h), radius=max(14, box_h // 5), fill=CARD,
                               outline=BEIGE, width=max(2, canvas.width // 700))
        name_font = _fit_text(draw, place.name.upper(), current_w - 24, max(20, canvas.width // 60), serif=True, bold=True)
        nb = draw.textbbox((0, 0), place.name.upper(), font=name_font)
        draw.text((x + (current_w - (nb[2] - nb[0])) // 2, y + 10), place.name.upper(), fill=BROWN, font=name_font)
        if place.subtitle:
            sub_font = _fit_text(draw, place.subtitle.upper(), current_w - 24, max(13, canvas.width // 95))
            sb = draw.textbbox((0, 0), place.subtitle.upper(), font=sub_font)
            draw.text((x + (current_w - (sb[2] - sb[0])) // 2, y + box_h - (sb[3] - sb[1]) - 12),
                      place.subtitle.upper(), fill=BROWN, font=sub_font)
        x += current_w + gap


def _travel_poster(images: list[Image.Image], places: list[PlaceItem], size: tuple[int, int], transition: float,
                   title: str, subtitle: str) -> Image.Image:
    base = _soft_blend(images, size, transition)
    canvas = base.convert("RGBA")
    top_overlay = Image.new("RGBA", size, (253, 246, 234, 0))
    top_overlay.putalpha(_vertical_gradient(size, 205, 0).getchannel("A"))
    canvas.alpha_composite(top_overlay)
    # Bottom darkening for readable labels.
    bottom = Image.new("RGBA", size, (58, 44, 32, 0))
    bottom.putalpha(_vertical_gradient(size, 0, 105).getchannel("A"))
    canvas.alpha_composite(bottom)
    result = canvas.convert("RGB")
    _draw_title(result, title, subtitle)
    _draw_place_labels(result, places)
    return result


def _postcard(images: list[Image.Image], places: list[PlaceItem], size: tuple[int, int], transition: float,
              title: str, subtitle: str) -> Image.Image:
    w, h = size
    canvas = Image.new("RGB", size, CREAM)
    margin = max(28, w // 30)
    header_h = max(135, h // 6)
    photo_box = (margin, header_h, w - margin, h - margin)
    photo_size = (photo_box[2] - photo_box[0], photo_box[3] - photo_box[1])
    photo = _soft_blend(images, photo_size, transition)
    mask = _rounded_mask(photo_size, max(20, w // 50))
    canvas.paste(photo, (photo_box[0], photo_box[1]), mask)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(photo_box, radius=max(20, w // 50), outline=BEIGE, width=max(3, w // 500))
    _draw_title(canvas, title, subtitle, top=22)
    return canvas


def _scrapbook(images: list[Image.Image], places: list[PlaceItem], size: tuple[int, int], title: str,
               subtitle: str) -> Image.Image:
    w, h = size
    canvas = Image.new("RGB", size, CREAM)
    draw = ImageDraw.Draw(canvas)
    # subtle paper dots
    for yy in range(20, h, 42):
        for xx in range(20, w, 42):
            draw.ellipse((xx, yy, xx + 2, yy + 2), fill="#EEDFC8")
    _draw_title(canvas, title, subtitle, top=24)
    top = max(150, h // 6)
    n = len(images)
    cols = 2 if n > 2 else n
    rows = math.ceil(n / cols)
    gap = max(24, w // 40)
    card_w = (w - gap * (cols + 1)) // cols
    available_h = h - top - gap * (rows + 1)
    card_h = max(140, available_h // rows)
    angles = [-3.5, 2.5, -1.8, 3.2, -2.2]
    for idx, (im, place) in enumerate(zip(images, places)):
        r, c = divmod(idx, cols)
        x = gap + c * (card_w + gap)
        y = top + gap + r * (card_h + gap)
        frame = Image.new("RGBA", (card_w, card_h), "white")
        inner_margin = max(12, card_w // 25)
        label_h = max(42, card_h // 7)
        photo = _cover(im, (card_w - inner_margin * 2, card_h - inner_margin * 2 - label_h))
        frame.paste(photo, (inner_margin, inner_margin))
        fd = ImageDraw.Draw(frame)
        label = place.name + (f" · {place.subtitle}" if place.subtitle else "")
        f = _fit_text(fd, label, card_w - 2 * inner_margin, max(16, card_w // 18), serif=True)
        tb = fd.textbbox((0, 0), label, font=f)
        fd.text(((card_w - (tb[2] - tb[0])) // 2, card_h - label_h + 5), label, fill=BROWN, font=f)
        frame = frame.rotate(angles[idx % len(angles)], expand=True, resample=Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0))
        shadow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((8, 8, frame.width - 4, frame.height - 4), radius=12, fill=(58, 44, 32, 70))
        shadow = shadow.filter(ImageFilter.GaussianBlur(8))
        px = x + (card_w - frame.width) // 2
        py = y + (card_h - frame.height) // 2
        canvas.paste(shadow, (px + 5, py + 7), shadow)
        canvas.paste(frame, (px, py), frame)
    return canvas


def create_design(places: list[PlaceItem], style: str, size: tuple[int, int], transition: float,
                  title: str, subtitle: str, brightness: float, contrast: float, colour: float,
                  background_blur: float) -> Image.Image:
    images = [_enhance(_open_image(p.image_bytes), brightness, contrast, colour, background_blur) for p in places]
    if style == "Soft blended scene":
        result = _soft_blend(images, size, transition)
        result_rgba = result.convert("RGBA")
        overlay = Image.new("RGBA", size, (253, 246, 234, 0))
        overlay.putalpha(_vertical_gradient(size, 170, 0).getchannel("A"))
        result_rgba.alpha_composite(overlay)
        result = result_rgba.convert("RGB")
        _draw_title(result, title, subtitle)
        _draw_place_labels(result, places)
        return result
    if style == "Panel collage":
        result = _panel_collage(images, size)
        draw = ImageDraw.Draw(result, "RGBA")
        draw.rectangle((0, 0, size[0], max(115, size[1] // 7)), fill=(253, 246, 234, 225))
        _draw_title(result, title, subtitle, top=18)
        return result
    if style == "Travel poster":
        return _travel_poster(images, places, size, transition, title, subtitle)
    if style == "Postcard":
        return _postcard(images, places, size, transition, title, subtitle)
    if style == "Scrapbook":
        return _scrapbook(images, places, size, title, subtitle)
    return _soft_blend(images, size, transition)


def _png_bytes(im: Image.Image, dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True, dpi=(dpi, dpi))
    return buf.getvalue()


def _project_zip(image_bytes: bytes, settings: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("place_blend.png", image_bytes)
        zf.writestr("place_blend_settings.json", json.dumps(settings, indent=2))
        zf.writestr(
            "README.txt",
            "This image was assembled locally from the photos you uploaded. No paid generative-image API was used.\n"
            "Local neural style transfer may have been used to restyle the source photos.\n"
            "Keep records showing that you own or have permission to use each source photo.\n",
        )
    return buf.getvalue()



def _settings_signature(
    places: list[PlaceItem],
    style_reference_bytes: bytes | None,
    settings: dict,
) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(settings, sort_keys=True, default=str).encode("utf-8"))
    if style_reference_bytes:
        digest.update(style_reference_bytes)
    for place in places:
        digest.update(place.name.encode("utf-8"))
        digest.update(place.subtitle.encode("utf-8"))
        digest.update(place.filename.encode("utf-8"))
        digest.update(place.image_bytes)
    return digest.hexdigest()


def _styled_sources_zip(styled_items: list[PlaceItem], dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, item in enumerate(styled_items, start=1):
            safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in item.name.strip()) or f"place_{index}"
            image = _open_image(item.image_bytes)
            zf.writestr(f"{index:02d}_{safe_name}_styled.png", _png_bytes(image, dpi=dpi))
        zf.writestr(
            "README.txt",
            "These images were processed by the Place Blend Maker local style engine.\n"
            "The original source composition remains; the engine transfers visual texture, colour and finish.\n"
            "Use only source and reference images you own or are licensed to use.\n",
        )
    return buf.getvalue()


def _project_zip_v2(
    final_png: bytes,
    styled_items: list[PlaceItem],
    settings: dict,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("final/place_blend.png", final_png)
        for index, item in enumerate(styled_items, start=1):
            safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in item.name.strip()) or f"place_{index}"
            zf.writestr(f"styled_sources/{index:02d}_{safe_name}.png", item.image_bytes)
        zf.writestr("place_blend_settings.json", json.dumps(settings, indent=2))
        zf.writestr(
            "README.txt",
            "Teddie & Lane Place Blend Maker Build 2.0\n\n"
            "The final poster and styled source images are included.\n"
            "The uploaded reference image is NOT copied into this ZIP.\n"
            "Local neural mode uses a pretrained feature network only; it does not call a paid image-generation API.\n"
            "The model keeps the content/layout of each source photo and transfers visual texture and colour.\n"
            "Keep records showing that you own or have permission to use all source and reference images.\n",
        )
    return buf.getvalue()


def _quality_settings(label: str) -> tuple[int, int]:
    values = {
        "Draft — fastest": (256, 18),
        "Balanced — recommended": (320, 32),
        "Detailed — slower": (384, 48),
    }
    return values.get(label, values["Balanced — recommended"])


def _build_styled_items(
    places: list[PlaceItem],
    *,
    engine: str,
    style_reference: Image.Image | None,
    art_preset: str,
    style_strength: int,
    palette_consistency: bool,
    quality_label: str,
    overall_progress=None,
) -> list[PlaceItem]:
    max_side, steps = _quality_settings(quality_label)
    styled: list[PlaceItem] = []
    total = max(1, len(places))

    for index, place in enumerate(places):
        source = _open_image(place.image_bytes)

        def update_inner(frac: float, message: str) -> None:
            if overall_progress is not None:
                overall = (index + frac) / total
                overall_progress.progress(
                    min(1.0, max(0.0, overall)),
                    text=f"{place.name}: {message}",
                )

        if engine == "Local neural style transfer":
            if style_reference is None:
                raise LocalStyleTransferError("Upload a style reference image first.")
            output = neural_style_transfer(
                source,
                style_reference,
                steps=steps,
                max_side=max_side,
                style_strength=style_strength,
                preserve_colour_palette=palette_consistency,
                preset=art_preset,
                progress_callback=update_inner,
            )
        else:
            update_inner(0.2, "Applying fast travel-art finish")
            output = fast_travel_finish(
                source,
                preset=art_preset,
                style_strength=style_strength,
                reference_image=style_reference,
                palette_consistency=palette_consistency,
            )
            update_inner(1.0, "Finished")

        styled.append(
            PlaceItem(
                name=place.name,
                subtitle=place.subtitle,
                image_bytes=_png_bytes(output, dpi=150),
                filename=f"styled_{place.filename.rsplit('.', 1)[0]}.png",
            )
        )

    if overall_progress is not None:
        overall_progress.progress(1.0, text="Styling complete")
    return styled


def render_app() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {CREAM}; }}
        .block-container {{ max-width: 1220px; padding-top: 1.1rem; }}
        .tl-card {{ background:white; border:1px solid {BEIGE}; border-radius:18px; padding:16px; box-shadow:0 5px 16px rgba(58,44,32,.08); }}
        .tl-note {{ background:#FFF9E9; border:1px solid #E9D39B; border-radius:14px; padding:12px; color:{BROWN}; }}
        .tl-local {{ background:#EEF5EA; border:1px solid #BCCCB3; border-radius:14px; padding:12px; color:{BROWN}; }}
        div[data-testid="stDownloadButton"] button {{ border-radius:12px; font-weight:700; }}
        div[data-testid="stButton"] button {{ border-radius:12px; font-weight:700; }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📍 Place Blend Maker — Local Style Transfer")
    st.caption(
        "Upload travel photos and one style-reference image. The local model transfers colour and painterly texture, "
        "then the app combines every place into a consistent poster. No paid image-generation API is used."
    )

    st.markdown(
        "<div class='tl-local'><b>What creates the art style now?</b> In Local neural mode, the app itself uses your uploaded "
        "reference image to restyle each source photo. It keeps the original landmark layout and does not invent a new fantasy scene. "
        "The same reference, preset and strength are applied to every place for consistency.</div>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Art engine")
        engine = st.selectbox(
            "Style method",
            ["Local neural style transfer", "Fast travel-poster finish"],
            help=(
                "Local neural mode is the stronger option and runs a small model on the Streamlit server. "
                "Fast finish uses image processing only and is useful on low-memory hosting."
            ),
        )
        art_preset = st.selectbox(
            "Art preset",
            [
                "Painterly Travel Poster",
                "Sunny Mediterranean",
                "Bold Landmark Art",
                "Soft Painted Photo",
                "Vintage Travel Postcard",
            ],
            index=0,
        )
        style_strength = st.slider("Style strength", 10, 100, 62, 2)
        palette_consistency = st.checkbox(
            "Match all photos to reference colours",
            value=True,
            help="Helps different photos share the same blues, golds, warmth and contrast.",
        )
        quality_label = st.selectbox(
            "Local processing quality",
            ["Draft — fastest", "Balanced — recommended", "Detailed — slower"],
            index=1,
            disabled=engine != "Local neural style transfer",
        )

        st.divider()
        st.header("Poster settings")
        place_count = st.number_input("Number of places", min_value=2, max_value=5, value=3, step=1)
        layout_style = st.selectbox(
            "Layout style",
            ["Soft blended scene", "Panel collage", "Travel poster", "Postcard", "Scrapbook"],
            index=2,
        )
        canvas_preset = st.selectbox(
            "Canvas size",
            [
                "Landscape — 1600 × 1000",
                "Square — 1200 × 1200",
                "Portrait — 1200 × 1600",
                "A4 landscape — 1754 × 1240",
                "A4 portrait — 1240 × 1754",
            ],
        )
        size_map = {
            "Landscape — 1600 × 1000": (1600, 1000),
            "Square — 1200 × 1200": (1200, 1200),
            "Portrait — 1200 × 1600": (1200, 1600),
            "A4 landscape — 1754 × 1240": (1754, 1240),
            "A4 portrait — 1240 × 1754": (1240, 1754),
        }
        canvas_size = size_map[canvas_preset]
        title = st.text_input("Main title", value="Melbourne · Sicily · Greece")
        subtitle = st.text_input("Subtitle", value="Three places, one beautiful journey")
        transition = st.slider("Blend softness", 0.35, 1.6, 0.8, 0.05)
        export_dpi = st.selectbox("PNG DPI metadata", [150, 300], index=1)

        with st.expander("Final poster adjustments"):
            brightness = st.slider("Brightness", 0.7, 1.3, 1.0, 0.05)
            contrast = st.slider("Contrast", 0.7, 1.4, 1.0, 0.05)
            colour = st.slider("Colour strength", 0.0, 1.6, 1.0, 0.05)
            background_blur = st.slider("Soft blur", 0.0, 3.0, 0.0, 0.25)

    st.subheader("1. Upload the look you want")
    style_upload = st.file_uploader(
        "Style-reference image",
        type=["png", "jpg", "jpeg", "webp"],
        help=(
            "Use the bright painterly travel image you showed as the reference. The app transfers its visual texture, "
            "colour mood and finish—not its exact landmarks or composition."
        ),
        key="style_reference_upload",
    )
    style_reference_bytes: bytes | None = None
    style_reference: Image.Image | None = None
    if style_upload:
        try:
            style_reference_bytes = style_upload.getvalue()
            style_reference = _open_image(style_reference_bytes)
            st.image(style_reference, caption="Style reference", width=420)
        except Exception as exc:
            st.error(f"Could not read the style-reference image: {exc}")
    elif engine == "Local neural style transfer":
        st.info("Upload the style image before creating the neural result.")
    else:
        st.caption("The reference image is optional in Fast finish mode, but adding it improves colour consistency.")

    st.subheader("2. Add your places and source photos")
    defaults = [("Melbourne", "Australia"), ("Sicily", "Italy"), ("Greece", "")]
    places: list[PlaceItem] = []
    for idx in range(int(place_count)):
        default_name, default_sub = defaults[idx] if idx < len(defaults) else (f"Place {idx + 1}", "")
        with st.expander(f"Place {idx + 1}", expanded=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Place name", value=default_name, key=f"place_name_{idx}")
            subtitle_place = c2.text_input("Country / short label", value=default_sub, key=f"place_sub_{idx}")
            uploaded = st.file_uploader(
                "Upload a photo you own or may use",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"place_image_{idx}",
            )
            if uploaded:
                try:
                    raw = uploaded.getvalue()
                    preview = _open_image(raw)
                    st.image(preview, caption=uploaded.name, use_container_width=True)
                    places.append(
                        PlaceItem(
                            name=name.strip() or f"Place {idx + 1}",
                            subtitle=subtitle_place.strip(),
                            image_bytes=raw,
                            filename=uploaded.name,
                        )
                    )
                except Exception as exc:
                    st.error(f"Could not read this image: {exc}")

    st.subheader("3. Create the consistent art set and poster")
    complete = len(places) == int(place_count)
    style_ready = style_reference is not None or engine == "Fast travel-poster finish"
    if not complete:
        st.info(f"Upload all {int(place_count)} source photos.")
    if not style_ready:
        st.info("Upload the style-reference image for Local neural mode.")

    settings = {
        "format": "teddie_lane_place_blend_v2",
        "build": "2.0",
        "engine": engine,
        "paid_api_used": False,
        "art_preset": art_preset,
        "style_strength": style_strength,
        "palette_consistency": palette_consistency,
        "processing_quality": quality_label,
        "layout_style": layout_style,
        "canvas_size": {"width": canvas_size[0], "height": canvas_size[1]},
        "title": title,
        "subtitle": subtitle,
        "transition": transition,
        "brightness": brightness,
        "contrast": contrast,
        "colour": colour,
        "blur": background_blur,
        "export_dpi": export_dpi,
        "style_reference_filename": style_upload.name if style_upload else None,
        "places": [
            {"name": p.name, "subtitle": p.subtitle, "source_filename": p.filename}
            for p in places
        ],
    }
    signature = _settings_signature(places, style_reference_bytes, settings)

    create_clicked = st.button(
        "🎨 Create styled images + final poster",
        type="primary",
        use_container_width=True,
        disabled=not (complete and style_ready),
    )

    if create_clicked:
        progress = st.progress(0.0, text="Preparing local style transfer…")
        try:
            styled_items = _build_styled_items(
                places,
                engine=engine,
                style_reference=style_reference,
                art_preset=art_preset,
                style_strength=style_strength,
                palette_consistency=palette_consistency,
                quality_label=quality_label,
                overall_progress=progress,
            )
            progress.progress(1.0, text="Building the final poster…")
            final = create_design(
                places=styled_items,
                style=layout_style,
                size=canvas_size,
                transition=transition,
                title=title,
                subtitle=subtitle,
                brightness=brightness,
                contrast=contrast,
                colour=colour,
                background_blur=background_blur,
            )
            final_png = _png_bytes(final, dpi=export_dpi)
            st.session_state["pbm_v2_result"] = {
                "signature": signature,
                "styled_items": [asdict(item) for item in styled_items],
                "final_png": final_png,
                "settings": settings,
            }
            progress.empty()
        except LocalStyleTransferError as exc:
            progress.empty()
            st.error(str(exc))
            if engine == "Local neural style transfer":
                st.caption("The Fast travel-poster finish remains available if the free server cannot run the local model.")
        except Exception as exc:
            progress.empty()
            st.exception(exc)

    stored = st.session_state.get("pbm_v2_result")
    if stored and stored.get("signature") == signature:
        styled_items = [PlaceItem(**item) for item in stored["styled_items"]]
        final_png = stored["final_png"]
        final_image = _open_image(final_png)

        st.success("The same local style settings were applied to every place.")
        st.markdown("#### Styled source images")
        columns = st.columns(min(3, len(styled_items)))
        for index, item in enumerate(styled_items):
            columns[index % len(columns)].image(
                _open_image(item.image_bytes),
                caption=f"{item.name} — {art_preset}",
                use_container_width=True,
            )

        st.markdown("#### Final combined poster")
        st.image(final_image, caption="Consistent local-style travel design", use_container_width=True)

        styled_zip = _styled_sources_zip(styled_items, dpi=export_dpi)
        project_zip = _project_zip_v2(final_png, styled_items, stored["settings"])
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "⬇️ Final PNG",
            data=final_png,
            file_name="place_blend_local_style.png",
            mime="image/png",
            use_container_width=True,
        )
        d2.download_button(
            "🖼️ Styled sources ZIP",
            data=styled_zip,
            file_name="styled_place_images.zip",
            mime="application/zip",
            use_container_width=True,
        )
        d3.download_button(
            "📦 Full project ZIP",
            data=project_zip,
            file_name="place_blend_project_v2.zip",
            mime="application/zip",
            use_container_width=True,
        )
    elif stored:
        st.warning("A setting or uploaded image changed. Press Create again to update the result.")

    st.markdown(
        "<div class='tl-note'><b>Accuracy note:</b> Local style transfer restyles your photographs; it does not generate "
        "new buildings, move landmarks into a new scene or reproduce the exact fantasy collage shown in a generated mock-up. "
        "For best consistency, use clear photos with similar viewpoints and process all of them with the same reference image.</div>",
        unsafe_allow_html=True,
    )
