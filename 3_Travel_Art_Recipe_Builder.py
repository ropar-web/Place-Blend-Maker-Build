import io
import json
import re
from copy import deepcopy
from typing import Dict, List

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="Travel Art Recipe Builder", page_icon="🎨", layout="wide")

STYLE_PRESET = {
    "collection_name": "Premium Painterly Travel Poster Collection",
    "canvas": {"ratio": "3:2", "width": 1536, "height": 1024, "horizon_y": 565},
    "finish": [
        "premium illustrated travel-poster artwork",
        "detailed hand-painted digital finish",
        "clean painterly brush texture",
        "crisp, recognisable architecture",
        "clear outlines and refined architectural detail",
        "polished depth, shadows and atmospheric perspective",
    ],
    "palette": [
        "rich cobalt-blue sky",
        "turquoise water where geographically appropriate",
        "warm cream",
        "golden yellow",
        "terracotta",
        "coral",
    ],
    "lighting": "bright Mediterranean-style sunlight from the upper left",
    "composition": [
        "one seamless panoramic scene",
        "natural foreground, middle ground and distant background",
        "one continuous horizon",
        "open sky and clean outer edges",
        "natural transitions using shared sky, water, sunlight, hills, plants and architecture",
        "no separate boxes or panels",
    ],
    "negative_rules": [
        "text", "labels", "borders", "frames", "logos",
        "people close to the camera", "photographic realism",
        "flat cartoon styling", "childish clipart", "3D toy styling",
        "pale watercolour washes", "excessive grain",
        "random fantasy buildings", "landmarks from unrelated countries",
    ],
}

PRESETS: Dict[str, Dict] = {
    "melbourne": {
        "display_name": "Melbourne, Australia",
        "aliases": ["melbourne", "flinders street", "flinders street station"],
        "main_landmark": "Flinders Street Station",
        "secondary_elements": ["classic green-and-gold Melbourne tram", "subtle city street foreground"],
        "important_features": ["warm yellow facade", "green copper dome", "central clocks", "arched windows"],
        "terrain": "urban streetscape with a softened transition into the shared panorama",
        "water": False,
        "architecture_palette": ["golden yellow", "warm cream", "deep green", "terracotta accents"],
    },
    "amalfi coast": {
        "display_name": "Amalfi Coast, Italy",
        "aliases": ["amalfi", "amalfi coast", "positano", "costiera amalfitana"],
        "main_landmark": "sunlit cliffside Amalfi coastal village",
        "secondary_elements": ["lemon trees", "Mediterranean water", "small boats", "stone terraces"],
        "important_features": ["terracotta roofs", "golden stone buildings", "steep green cliffs", "layered hillside homes"],
        "terrain": "steep Mediterranean cliffs descending into turquoise water",
        "water": True,
        "architecture_palette": ["warm cream", "golden stone", "terracotta", "coral"],
    },
    "santorini": {
        "display_name": "Santorini, Greece",
        "aliases": ["santorini", "oia", "greek islands", "greece"],
        "main_landmark": "whitewashed Santorini cliffside village",
        "secondary_elements": ["blue-domed churches", "stone steps", "bougainvillea", "Aegean water"],
        "important_features": ["white curved architecture", "deep blue domes", "layered cliffside terraces", "narrow stone paths"],
        "terrain": "white cliffside terraces above deep blue Aegean water",
        "water": True,
        "architecture_palette": ["white", "cobalt blue", "warm stone", "bougainvillea pink"],
    },
    "sicily": {
        "display_name": "Sicily, Italy",
        "aliases": ["sicily", "sicilia", "taormina"],
        "main_landmark": "warm Sicilian coastal village",
        "secondary_elements": ["lemon trees", "Mediterranean water", "stone balconies"],
        "important_features": ["terracotta roofs", "golden stone buildings", "warm cream facades", "coastal hills"],
        "terrain": "sunlit coastal hills and turquoise Mediterranean shoreline",
        "water": True,
        "architecture_palette": ["golden stone", "terracotta", "warm cream", "coral"],
    },
    "sydney": {
        "display_name": "Sydney, Australia",
        "aliases": ["sydney", "opera house", "harbour bridge"],
        "main_landmark": "Sydney Opera House",
        "secondary_elements": ["Sydney Harbour Bridge", "harbour water", "ferries"],
        "important_features": ["white sail-like shells", "steel harbour bridge arch", "blue harbour"],
        "terrain": "harbour city shoreline",
        "water": True,
        "architecture_palette": ["white", "sandstone", "cobalt", "warm cream"],
    },
    "paris": {
        "display_name": "Paris, France",
        "aliases": ["paris", "eiffel tower"],
        "main_landmark": "Eiffel Tower",
        "secondary_elements": ["Haussmann buildings", "tree-lined avenue", "subtle café terraces"],
        "important_features": ["recognisable iron tower silhouette", "cream limestone facades", "mansard roofs"],
        "terrain": "formal city avenue with distant skyline",
        "water": False,
        "architecture_palette": ["warm cream", "soft grey", "terracotta accents"],
    },
    "rome": {
        "display_name": "Rome, Italy",
        "aliases": ["rome", "roma", "colosseum"],
        "main_landmark": "the Colosseum",
        "secondary_elements": ["umbrella pines", "warm stone streets", "Italian balconies"],
        "important_features": ["elliptical arches", "golden Roman stone", "historic layered cityscape"],
        "terrain": "historic city rising over warm stone streets",
        "water": False,
        "architecture_palette": ["golden stone", "terracotta", "warm cream"],
    },
    "venice": {
        "display_name": "Venice, Italy",
        "aliases": ["venice", "venezia", "grand canal"],
        "main_landmark": "the Grand Canal with Venetian palazzi",
        "secondary_elements": ["gondolas", "arched bridges", "striped mooring poles"],
        "important_features": ["ornate canal-front facades", "warm cream and coral palazzi", "arched windows"],
        "terrain": "historic canal city",
        "water": True,
        "architecture_palette": ["warm cream", "coral", "terracotta", "golden yellow"],
    },
}


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def resolve_destination(name: str) -> Dict:
    query = normalise(name)
    for key, preset in PRESETS.items():
        candidates = [key] + preset.get("aliases", [])
        if any(normalise(item) in query or query in normalise(item) for item in candidates):
            result = deepcopy(preset)
            result["typed_name"] = name.strip()
            result["matched_preset"] = key
            return result
    title = name.strip().title()
    return {
        "display_name": title,
        "typed_name": name.strip(),
        "matched_preset": None,
        "main_landmark": f"the most recognisable landmark or streetscape of {title}",
        "secondary_elements": ["geographically appropriate architecture", "local vegetation", "a natural foreground"],
        "important_features": ["accurate local architecture", "recognisable geographic character", "authentic materials and colours"],
        "terrain": "geographically appropriate landscape",
        "water": False,
        "architecture_palette": ["warm cream", "golden yellow", "terracotta", "coral accents"],
    }


def zone_layout(count: int, width: int, height: int, horizon_y: int) -> List[Dict]:
    overlap = int(width * 0.05)
    usable = width + overlap * max(0, count - 1)
    zone_width = usable // max(1, count)
    zones = []
    for i in range(count):
        x = max(0, i * (zone_width - overlap))
        zones.append({
            "x": x,
            "y": int(height * 0.14),
            "width": min(width - x, zone_width),
            "height": int(height * 0.72),
            "horizon_y": horizon_y,
            "overlap_px": overlap if i else 0,
        })
    return zones


def build_recipe(destinations: List[Dict], horizon_y: int) -> Dict:
    style = deepcopy(STYLE_PRESET)
    style["canvas"]["horizon_y"] = horizon_y
    zones = zone_layout(len(destinations), style["canvas"]["width"], style["canvas"]["height"], horizon_y)
    positions_by_count = {
        1: ["middle or slightly left of centre"],
        2: ["left", "right"],
        3: ["left", "centre", "right"],
        4: ["far left", "centre-left", "centre-right", "far right"],
    }
    result = []
    for index, destination in enumerate(destinations):
        item = deepcopy(destination)
        item["position"] = positions_by_count[len(destinations)][index]
        item["region"] = zones[index]
        result.append(item)
    return {
        "recipe_version": "1.0",
        "style_preset": style,
        "scene_type": "single seamless panoramic combined-destination travel artwork",
        "destinations": result,
        "transition_rules": {
            "continuous_sky": True,
            "continuous_horizon": True,
            "continuous_water_where_geographically_appropriate": True,
            "shared_upper_left_sunlight": True,
            "shared_colour_intensity": True,
            "shared_architectural_detail_level": True,
            "blend_with_hills_plants_water_and_architectural_overlap": True,
            "no_separate_panels": True,
            "no_hard_vertical_dividers": True,
        },
        "generation_instruction": "Use the approved artwork as the strict style reference and the layout PNG as the composition reference.",
    }


def join_list(items: List[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def build_prompt(recipe: Dict) -> str:
    style = recipe["style_preset"]
    place_lines = []
    for d in recipe["destinations"]:
        place_lines.append(
            f"{d['display_name']} on the {d['position']}: feature {d['main_landmark']}. "
            f"Include {join_list(d['secondary_elements'])}. Preserve {join_list(d['important_features'])}."
        )
    return f"""Create one premium painterly travel-poster artwork combining the listed destinations into one seamless panoramic scene.

Use the attached approved artwork as a strict visual-style reference only. Do not copy its exact buildings or composition. Use the attached rendered layout guide as the composition guide.

LOCKED COLLECTION STYLE:
{join_list(style['finish'])}.
Use {join_list(style['palette'])}.
Lighting: {style['lighting']}.
Composition: {join_list(style['composition'])}.
Wide landscape format in an exact {style['canvas']['ratio']} ratio.

DESTINATIONS:
{chr(10).join(place_lines)}

BLENDING:
Blend all locations naturally using one shared sky, one continuous horizon, consistent upper-left sunlight, related plants, hills, water where appropriate, and soft architectural overlap. Do not create separate boxes, panels, hard dividers or disconnected scenes. Balance the destinations so no single place overwhelms the others.

ACCURACY:
Make each place immediately recognisable and geographically appropriate. Preserve each main landmark's important shape, proportions, materials and defining architectural features.

DO NOT INCLUDE:
{', '.join(style['negative_rules'])}.

The result must look as though it belongs to the exact same artist, coordinated collection and printed travel-poster series as the approved reference artwork."""


def get_font(size: int):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_guide(recipe: Dict) -> bytes:
    width = recipe["style_preset"]["canvas"]["width"]
    height = recipe["style_preset"]["canvas"]["height"]
    horizon = recipe["style_preset"]["canvas"]["horizon_y"]
    image = Image.new("RGB", (width, height), (130, 190, 230))
    draw = ImageDraw.Draw(image)

    for y in range(horizon):
        t = y / max(1, horizon)
        draw.line((0, y, width, y), fill=(int(35 + 95*t), int(95 + 95*t), int(185 + 50*t)))

    has_water = any(d["water"] for d in recipe["destinations"])
    draw.rectangle((0, horizon, width, height), fill=(54, 182, 193) if has_water else (222, 198, 158))
    draw.rectangle((0, horizon - 7, width, horizon + 7), fill=(248, 225, 170))

    colours = [(232, 177, 88), (226, 124, 83), (242, 229, 198), (121, 156, 119)]
    title_font = get_font(38)
    small_font = get_font(24)

    for idx, d in enumerate(recipe["destinations"]):
        region = d["region"]
        x, w = region["x"], region["width"]
        colour = colours[idx % len(colours)]
        base_y = horizon + 105
        if "cliff" in d["terrain"].lower() or "hill" in d["terrain"].lower():
            points = [
                (x, base_y + 140), (x + int(w*.18), base_y),
                (x + int(w*.38), base_y - 95), (x + int(w*.62), base_y - 40),
                (x + w, base_y + 100), (x + w, height), (x, height)
            ]
            draw.polygon(points, fill=colour)
        else:
            draw.rounded_rectangle((x + 20, base_y - 65, x + w - 20, height - 65), radius=28, fill=colour)

        building_y = horizon - 65
        count = 5 if len(recipe["destinations"]) <= 3 else 4
        bw = max(54, int(w / (count + 1.5)))
        gap = max(16, int((w - count*bw)/(count + 1)))
        dome_place = "dome" in " ".join(d["important_features"]).lower()
        for j in range(count):
            bx = x + gap + j*(bw + gap)
            bh = 95 + ((j*41 + idx*29) % 135)
            by = building_y - bh
            draw.rounded_rectangle((bx, by, bx+bw, building_y+38), radius=10, fill=(250, 238, 211), outline=(85, 66, 45), width=4)
            if dome_place and j in (1, 3):
                draw.ellipse((bx+6, by-34, bx+bw-6, by+28), fill=(40, 94, 170), outline=(85, 66, 45), width=4)
            else:
                draw.polygon([(bx-3, by+6), (bx+bw//2, by-31), (bx+bw+3, by+6)], fill=(197, 91, 57), outline=(85, 66, 45))

        box = (x+20, 28, min(width-20, x+w-16), 132)
        draw.rounded_rectangle(box, radius=18, fill=(255, 249, 234), outline=(60, 46, 32), width=4)
        draw.text((box[0]+16, box[1]+12), d["display_name"], fill=(48, 36, 27), font=title_font)
        landmark = d["main_landmark"] if len(d["main_landmark"]) < 50 else d["main_landmark"][:47] + "..."
        draw.text((box[0]+16, box[1]+64), landmark, fill=(82, 63, 46), font=small_font)

    draw.line((0, horizon, width, horizon), fill=(255, 255, 255), width=5)
    draw.text((24, horizon+18), "ONE CONTINUOUS HORIZON", fill=(255, 255, 255), font=small_font)
    draw.text((24, 168), "OPEN SKY • UPPER-LEFT SUNLIGHT", fill=(255, 255, 255), font=small_font)

    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


st.title("🎨 Travel Art Recipe Builder")
st.caption("Creates a JSON recipe, 3:2 visual layout guide and locked ChatGPT prompt. No image API is used.")

with st.expander("How to use it"):
    st.markdown("""
1. Upload your approved style-reference artwork.
2. Type one to four destinations.
3. Check or correct the auto-filled landmark details.
4. Select **Build recipe and guide**.
5. Upload the style reference, layout PNG and generated prompt together in ChatGPT.
""")

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Approved style reference")
    reference = st.file_uploader("Upload artwork", type=["png", "jpg", "jpeg", "webp"])
    if reference:
        st.image(Image.open(reference), use_container_width=True, caption="Approved collection reference")
with col2:
    st.subheader("2. Destinations")
    count = st.slider("Number of destinations", 1, 4, 3)
    defaults = ["Melbourne", "Amalfi Coast", "Santorini", "Sicily"]
    typed = [st.text_input(f"Destination {i+1}", defaults[i], key=f"place_{i}") for i in range(count)]

resolved = [resolve_destination(place) for place in typed if place.strip()]
customised = []
st.subheader("3. Check the automatic place details")
for i, destination in enumerate(resolved):
    label = destination["display_name"] + ("" if destination["matched_preset"] else " — custom place")
    with st.expander(label, expanded=True):
        if destination["matched_preset"]:
            st.success(f"Matched preset: {destination['matched_preset'].title()}")
        else:
            st.warning("No saved preset found. Correct the landmark and supporting elements for best accuracy.")
        landmark = st.text_input("Main landmark or subject", destination["main_landmark"], key=f"landmark_{i}")
        extras = st.text_input("Supporting elements, comma separated", ", ".join(destination["secondary_elements"]), key=f"extras_{i}")
        water = st.checkbox("Use water for this location", destination["water"], key=f"water_{i}")
        updated = deepcopy(destination)
        updated["main_landmark"] = landmark.strip()
        updated["secondary_elements"] = [x.strip() for x in extras.split(",") if x.strip()]
        updated["water"] = water
        customised.append(updated)

with st.expander("Advanced composition settings"):
    horizon_y = st.slider("Horizon height", 420, 700, STYLE_PRESET["canvas"]["horizon_y"])

if st.button("Build recipe and guide", type="primary", use_container_width=True):
    if customised:
        recipe = build_recipe(customised, horizon_y)
        st.session_state["recipe"] = recipe
        st.session_state["prompt"] = build_prompt(recipe)
        st.session_state["guide"] = render_guide(recipe)
    else:
        st.error("Add at least one destination.")

if "recipe" in st.session_state:
    st.divider()
    st.subheader("4. Visual composition guide")
    st.image(st.session_state["guide"], use_container_width=True)
    st.download_button("Download layout guide PNG", st.session_state["guide"], "travel_art_layout_guide.png", "image/png", use_container_width=True)

    st.subheader("5. JSON recipe")
    recipe_text = json.dumps(st.session_state["recipe"], indent=2, ensure_ascii=False)
    st.code(recipe_text, language="json")
    st.download_button("Download JSON recipe", recipe_text.encode(), "travel_art_recipe.json", "application/json", use_container_width=True)

    st.subheader("6. Final ChatGPT prompt")
    st.text_area("Copy this prompt", st.session_state["prompt"], height=520)
    st.download_button("Download prompt TXT", st.session_state["prompt"].encode(), "travel_art_prompt.txt", "text/plain", use_container_width=True)
    st.info("Best result: upload the approved reference artwork, layout guide PNG and generated prompt together.")
