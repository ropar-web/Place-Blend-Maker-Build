
import io
import json
import re
from copy import deepcopy

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


st.set_page_config(
    page_title="Place Blend Recipe Builder",
    page_icon="🎨",
    layout="wide",
)

STYLE_PRESET = {
    "collection_name": "Premium Painterly Travel Poster Collection",
    "canvas": {
        "ratio": "3:2",
        "width": 1536,
        "height": 1024,
        "horizon_y": 560
    },
    "finish": [
        "premium illustrated travel-poster artwork",
        "detailed hand-painted digital finish",
        "crisp recognisable architecture",
        "clean painterly brush texture",
        "clear outlines and refined architectural detail",
        "polished depth, shadows and atmospheric perspective"
    ],
    "palette": [
        "rich cobalt-blue sky",
        "turquoise water where geographically appropriate",
        "warm cream",
        "golden yellow",
        "terracotta",
        "coral"
    ],
    "lighting": "bright Mediterranean-style sunlight from the upper left",
    "composition": [
        "one seamless panoramic scene",
        "natural foreground, middle ground and distant background",
        "continuous horizon",
        "open sky and clean outer edges",
        "natural transitions using shared sky, water, sunlight, hills, plants and architecture",
        "no separate boxes or panels"
    ],
    "negative_rules": [
        "text",
        "labels",
        "borders",
        "frames",
        "logos",
        "people close to the camera",
        "photographic realism",
        "flat cartoon styling",
        "childish clipart",
        "3D toy styling",
        "pale watercolour washes",
        "excessive grain",
        "random fantasy buildings",
        "landmarks from unrelated countries"
    ]
}

DESTINATIONS = {
    "melbourne": {
        "display_name": "Melbourne, Australia",
        "aliases": ["melbourne", "flinders street", "flinders street station"],
        "main_landmark": "Flinders Street Station",
        "secondary_elements": [
            "classic green-and-gold Melbourne tram",
            "subtle city street foreground"
        ],
        "important_features": [
            "recognisable warm yellow facade",
            "green copper dome",
            "central clocks",
            "arched windows",
            "Federation-era streetscape"
        ],
        "terrain": "urban streetscape",
        "water": False
    },
    "amalfi coast": {
        "display_name": "Amalfi Coast, Italy",
        "aliases": ["amalfi", "amalfi coast", "positano"],
        "main_landmark": "sunlit cliffside Amalfi coastal village",
        "secondary_elements": [
            "lemon trees",
            "Mediterranean water",
            "small boats",
            "stone terraces"
        ],
        "important_features": [
            "terracotta roofs",
            "warm cream and golden stone buildings",
            "steep green cliffs",
            "layered hillside homes",
            "curving coastal shoreline"
        ],
        "terrain": "steep Mediterranean cliffs descending into turquoise water",
        "water": True
    },
    "santorini": {
        "display_name": "Santorini, Greece",
        "aliases": ["santorini", "oia", "greece", "greek islands"],
        "main_landmark": "whitewashed Santorini cliffside village",
        "secondary_elements": [
            "blue-domed churches",
            "stone steps",
            "bougainvillea",
            "Aegean water"
        ],
        "important_features": [
            "white curved architecture",
            "deep blue domes",
            "layered cliffside terraces",
            "narrow stone paths",
            "bright pink bougainvillea"
        ],
        "terrain": "white cliffside terraces above Aegean water",
        "water": True
    },
    "sicily": {
        "display_name": "Sicily, Italy",
        "aliases": ["sicily", "sicilia", "taormina"],
        "main_landmark": "warm Sicilian coastal village",
        "secondary_elements": [
            "lemon trees",
            "Mediterranean water",
            "stone balconies"
        ],
        "important_features": [
            "terracotta roofs",
            "golden stone buildings",
            "warm cream facades",
            "coastal hills",
            "Mediterranean vegetation"
        ],
        "terrain": "sunlit coastal hills and turquoise Mediterranean shoreline",
        "water": True
    },
    "sydney": {
        "display_name": "Sydney, Australia",
        "aliases": ["sydney", "opera house", "harbour bridge"],
        "main_landmark": "Sydney Opera House",
        "secondary_elements": [
            "Sydney Harbour Bridge",
            "harbour water",
            "ferries"
        ],
        "important_features": [
            "recognisable white sail-like shells",
            "steel harbour bridge arch",
            "blue harbour",
            "coastal city skyline"
        ],
        "terrain": "harbour city shoreline",
        "water": True
    },
    "paris": {
        "display_name": "Paris, France",
        "aliases": ["paris", "eiffel tower"],
        "main_landmark": "Eiffel Tower",
        "secondary_elements": [
            "Haussmann buildings",
            "tree-lined avenue",
            "subtle cafe terraces"
        ],
        "important_features": [
            "recognisable iron tower silhouette",
            "cream limestone facades",
            "mansard roofs",
            "elegant boulevards"
        ],
        "terrain": "formal city avenue with distant skyline",
        "water": False
    },
    "rome": {
        "display_name": "Rome, Italy",
        "aliases": ["rome", "roma", "colosseum"],
        "main_landmark": "the Colosseum",
        "secondary_elements": [
            "umbrella pines",
            "warm stone streets",
            "Italian balconies"
        ],
        "important_features": [
            "recognisable elliptical arches",
            "golden Roman stone",
            "historic layered cityscape"
        ],
        "terrain": "historic city rising over warm stone streets",
        "water": False
    },
    "venice": {
        "display_name": "Venice, Italy",
        "aliases": ["venice", "venezia", "grand canal"],
        "main_landmark": "the Grand Canal with Venetian palazzi",
        "secondary_elements": [
            "gondolas",
            "arched bridges",
            "striped mooring poles"
        ],
        "important_features": [
            "ornate canal-front facades",
            "warm cream and coral palazzi",
            "arched windows",
            "blue-green canal water"
        ],
        "terrain": "historic canal city",
        "water": True
    }
}


def normalise(text):
    return re.sub(r"\s+", " ", text.strip().lower())


def match_destination(text):
    query = normalise(text)

    for key, preset in DESTINATIONS.items():
        candidates = [key] + preset.get("aliases", [])
        if any(query == normalise(item) or query in normalise(item) or normalise(item) in query for item in candidates):
            result = deepcopy(preset)
            result["typed_name"] = text.strip()
            result["matched_preset"] = key
            return result

    title = text.strip().title()
    return {
        "display_name": title,
        "typed_name": text.strip(),
        "matched_preset": None,
        "main_landmark": f"the most recognisable landmark or streetscape of {title}",
        "secondary_elements": [
            "geographically appropriate architecture",
            "local vegetation",
            "a natural foreground"
        ],
        "important_features": [
            "accurate local architecture",
            "recognisable geographic character",
            "authentic materials and colours"
        ],
        "terrain": "geographically appropriate landscape",
        "water": False
    }


def build_regions(count, width, height, horizon_y):
    overlap = int(width * 0.05)
    effective_width = width + overlap * max(0, count - 1)
    zone_width = effective_width // count
    regions = []

    for index in range(count):
        x = max(0, index * (zone_width - overlap))
        w = min(width - x, zone_width)
        regions.append({
            "x": x,
            "y": int(height * 0.14),
            "width": w,
            "height": int(height * 0.72),
            "horizon_y": horizon_y,
            "overlap_px": overlap if index else 0
        })

    return regions


def position_name(index, count):
    options = {
        1: ["middle or slightly left of centre"],
        2: ["left", "right"],
        3: ["left", "centre", "right"],
        4: ["far left", "centre-left", "centre-right", "far right"]
    }
    return options[count][index]


def make_recipe(destinations, horizon_y):
    style = deepcopy(STYLE_PRESET)
    style["canvas"]["horizon_y"] = horizon_y

    width = style["canvas"]["width"]
    height = style["canvas"]["height"]
    regions = build_regions(len(destinations), width, height, horizon_y)

    final_destinations = []
    for index, destination in enumerate(destinations):
        item = deepcopy(destination)
        item["position"] = position_name(index, len(destinations))
        item["region"] = regions[index]
        final_destinations.append(item)

    return {
        "recipe_version": "1.1",
        "style_preset": style,
        "scene_type": "single seamless panoramic combined-destination travel artwork",
        "destinations": final_destinations,
        "transition_rules": {
            "continuous_sky": True,
            "continuous_horizon": True,
            "continuous_water_where_appropriate": True,
            "shared_upper_left_sunlight": True,
            "shared_colour_intensity": True,
            "shared_detail_level": True,
            "blend_with_hills_plants_water_and_architecture": True,
            "no_separate_panels": True,
            "no_hard_vertical_dividers": True
        }
    }


def joined(items):
    items = [str(item) for item in items if str(item).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def make_prompt(recipe):
    style = recipe["style_preset"]

    destination_lines = []
    for item in recipe["destinations"]:
        destination_lines.append(
            f"{item['display_name']} on the {item['position']}: "
            f"feature {item['main_landmark']}. "
            f"Include {joined(item['secondary_elements'])}. "
            f"Preserve {joined(item['important_features'])}."
        )

    return f"""Create one premium painterly travel-poster artwork combining the listed destinations into one seamless panoramic scene.

Use the attached approved artwork as a strict visual-style reference only. Do not copy its exact buildings or composition. Use the attached rendered layout guide as the composition guide.

LOCKED COLLECTION STYLE:
{joined(style['finish'])}.
Use {joined(style['palette'])}.
Lighting: {style['lighting']}.
Composition: {joined(style['composition'])}.
Wide landscape format in an exact {style['canvas']['ratio']} ratio.

DESTINATIONS:
{chr(10).join(destination_lines)}

BLENDING:
Blend all locations naturally using one shared sky, one continuous horizon, consistent upper-left sunlight, related plants, hills, water where appropriate, and soft architectural overlap. Do not create separate boxes, panels, hard dividers or disconnected scenes. Balance the destinations so no one location overwhelms the others.

ACCURACY:
Make each place immediately recognisable and geographically appropriate. Preserve the main landmark's important shape, proportions, materials and defining architectural features.

DO NOT INCLUDE:
{", ".join(style['negative_rules'])}.

The final result must look as though it belongs to the same artist, coordinated collection and printed travel-poster series as the approved reference artwork."""


def get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
    ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def make_guide(recipe):
    canvas = recipe["style_preset"]["canvas"]
    width = canvas["width"]
    height = canvas["height"]
    horizon_y = canvas["horizon_y"]

    image = Image.new("RGB", (width, height), (220, 235, 245))
    draw = ImageDraw.Draw(image)

    for y in range(horizon_y):
        t = y / max(1, horizon_y - 1)
        colour = (
            int(32 + 92 * t),
            int(105 + 75 * t),
            int(195 + 40 * t)
        )
        draw.line((0, y, width, y), fill=colour)

    use_water = any(item.get("water", False) for item in recipe["destinations"])
    lower_colour = (58, 178, 192) if use_water else (220, 196, 156)
    draw.rectangle((0, horizon_y, width, height), fill=lower_colour)

    zone_colours = [
        (230, 171, 85),
        (220, 123, 82),
        (245, 235, 210),
        (126, 157, 117)
    ]

    title_font = get_font(42)
    body_font = get_font(25)
    small_font = get_font(20)

    for index, item in enumerate(recipe["destinations"]):
        region = item["region"]
        x = region["x"]
        w = region["width"]
        colour = zone_colours[index % len(zone_colours)]

        base_y = horizon_y + 95
        terrain = item.get("terrain", "").lower()

        if "cliff" in terrain or "hill" in terrain:
            points = [
                (x, height),
                (x, base_y + 100),
                (x + int(w * 0.18), base_y - 30),
                (x + int(w * 0.42), base_y - 120),
                (x + int(w * 0.66), base_y - 50),
                (x + w, base_y + 100),
                (x + w, height)
            ]
            draw.polygon(points, fill=colour)
        else:
            draw.rounded_rectangle(
                (x + 20, horizon_y - 55, x + w - 20, height - 65),
                radius=35,
                fill=colour
            )

        building_count = 5 if len(recipe["destinations"]) <= 3 else 4
        building_width = max(54, int(w / (building_count + 1.5)))
        gap = max(16, int((w - building_count * building_width) / (building_count + 1)))

        for building_index in range(building_count):
            bx = x + gap + building_index * (building_width + gap)
            bh = 110 + ((building_index * 31 + index * 23) % 140)
            by = horizon_y - bh - 10

            draw.rounded_rectangle(
                (bx, by, bx + building_width, horizon_y + 30),
                radius=10,
                fill=(250, 239, 214),
                outline=(79, 60, 42),
                width=4
            )

            if "dome" in " ".join(item.get("important_features", [])).lower() and building_index in (1, 3):
                draw.ellipse(
                    (bx + 5, by - 32, bx + building_width - 5, by + 30),
                    fill=(34, 92, 172),
                    outline=(79, 60, 42),
                    width=4
                )
            else:
                draw.polygon(
                    [
                        (bx - 4, by + 5),
                        (bx + building_width // 2, by - 33),
                        (bx + building_width + 4, by + 5)
                    ],
                    fill=(198, 96, 59),
                    outline=(79, 60, 42)
                )

        label_right = min(width - 20, x + w - 20)
        draw.rounded_rectangle(
            (x + 20, 30, label_right, 140),
            radius=18,
            fill=(255, 250, 237),
            outline=(63, 49, 36),
            width=4
        )
        draw.text((x + 38, 45), item["display_name"], fill=(48, 38, 28), font=title_font)

        landmark = item["main_landmark"]
        if len(landmark) > 48:
            landmark = landmark[:45] + "..."
        draw.text((x + 38, 96), landmark, fill=(83, 65, 47), font=body_font)

        draw.text(
            (x + 28, height - 48),
            item["position"].upper(),
            fill=(35, 35, 35),
            font=small_font
        )

    draw.line((0, horizon_y, width, horizon_y), fill=(255, 255, 255), width=5)
    draw.text((22, horizon_y + 14), "ONE CONTINUOUS HORIZON", fill=(255, 255, 255), font=body_font)
    draw.text((22, 170), "OPEN SKY + UPPER-LEFT SUNLIGHT", fill=(255, 255, 255), font=body_font)

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


st.title("🎨 Place Blend Recipe Builder")
st.write(
    "Type one to four destinations. The app creates a JSON recipe, "
    "a visual 3:2 layout guide and a locked ChatGPT prompt."
)

with st.expander("How to use it"):
    st.markdown(
        """
1. Upload your approved reference artwork.
2. Enter the destinations.
3. Check or edit the automatic landmark details.
4. Press **Build recipe and guide**.
5. Download the JSON and layout PNG.
6. Upload the approved reference, layout PNG and generated prompt to ChatGPT.
        """
    )

reference = st.file_uploader(
    "Approved collection reference image",
    type=["png", "jpg", "jpeg", "webp"]
)

if reference is not None:
    try:
        uploaded_image = Image.open(reference)
        st.image(uploaded_image, caption="Approved style reference", use_container_width=True)
    except Exception as exc:
        st.error(f"That image could not be opened: {exc}")

count = st.slider("Number of destinations", 1, 4, 3)

defaults = ["Melbourne", "Amalfi Coast", "Santorini", "Sicily"]
typed = []

for index in range(count):
    typed.append(
        st.text_input(
            f"Destination {index + 1}",
            value=defaults[index],
            key=f"destination_{index}"
        )
    )

resolved = [match_destination(name) for name in typed if name.strip()]
edited = []

st.subheader("Check the automatic details")

for index, destination in enumerate(resolved):
    with st.expander(
        f"{index + 1}. {destination['display_name']}",
        expanded=True
    ):
        if destination.get("matched_preset"):
            st.success(f"Matched preset: {destination['matched_preset'].title()}")
        else:
            st.warning("Custom place: check the landmark and supporting elements.")

        landmark = st.text_input(
            "Main landmark or subject",
            value=destination["main_landmark"],
            key=f"landmark_{index}"
        )

        extras = st.text_input(
            "Supporting elements, separated by commas",
            value=", ".join(destination["secondary_elements"]),
            key=f"extras_{index}"
        )

        water = st.checkbox(
            "Use water for this location",
            value=destination["water"],
            key=f"water_{index}"
        )

        updated = deepcopy(destination)
        updated["main_landmark"] = landmark.strip()
        updated["secondary_elements"] = [
            item.strip() for item in extras.split(",") if item.strip()
        ]
        updated["water"] = water
        edited.append(updated)

horizon_y = st.slider(
    "Horizon height",
    420,
    700,
    STYLE_PRESET["canvas"]["horizon_y"]
)

if st.button("Build recipe and guide", type="primary", use_container_width=True):
    if not edited:
        st.error("Enter at least one destination.")
    else:
        recipe = make_recipe(edited, horizon_y)
        prompt = make_prompt(recipe)
        guide_png = make_guide(recipe)

        st.session_state["recipe"] = recipe
        st.session_state["prompt"] = prompt
        st.session_state["guide_png"] = guide_png

if "recipe" in st.session_state:
    recipe = st.session_state["recipe"]
    prompt = st.session_state["prompt"]
    guide_png = st.session_state["guide_png"]

    st.divider()
    st.subheader("Visual layout guide")
    st.image(guide_png, use_container_width=True)

    st.download_button(
        "Download layout guide PNG",
        guide_png,
        "place_blend_layout_guide.png",
        "image/png",
        use_container_width=True
    )

    st.subheader("JSON recipe")
    recipe_text = json.dumps(recipe, indent=2, ensure_ascii=False)
    st.code(recipe_text, language="json")

    st.download_button(
        "Download JSON recipe",
        recipe_text.encode("utf-8"),
        "place_blend_recipe.json",
        "application/json",
        use_container_width=True
    )

    st.subheader("ChatGPT prompt")
    st.text_area(
        "Copy this prompt into ChatGPT",
        value=prompt,
        height=500
    )

    st.download_button(
        "Download prompt TXT",
        prompt.encode("utf-8"),
        "place_blend_prompt.txt",
        "text/plain",
        use_container_width=True
    )

    st.info(
        "Upload the approved reference image, the layout guide PNG and this prompt together."
    )
