
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
        "country_name": "Australia",
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
        "country_name": "Italy",
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
        "country_name": "Greece",
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
        "country_name": "Italy",
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
        "country_name": "Australia",
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
        "country_name": "France",
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
        "country_name": "Italy",
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
        "country_name": "Italy",
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
    },
    "london": {
        "display_name": "London, United Kingdom",
        "country_name": "United Kingdom",
        "aliases": ["london", "big ben", "westminster", "england"],
        "main_landmark": "Elizabeth Tower and the Palace of Westminster",
        "secondary_elements": [
            "London Eye",
            "red double-decker bus",
            "River Thames"
        ],
        "important_features": [
            "recognisable clock tower",
            "ornate Gothic stonework",
            "London Eye silhouette",
            "British riverfront streetscape"
        ],
        "terrain": "historic city beside the River Thames",
        "water": True
    },
    "new york": {
        "display_name": "New York City, United States",
        "country_name": "United States",
        "aliases": ["new york", "new york city", "nyc", "manhattan", "statue of liberty"],
        "main_landmark": "the Manhattan skyline",
        "secondary_elements": [
            "Statue of Liberty",
            "Empire State Building",
            "New York harbour ferry"
        ],
        "important_features": [
            "recognisable Art Deco skyscraper silhouettes",
            "Manhattan waterfront skyline",
            "Statue of Liberty",
            "dense layered city architecture"
        ],
        "terrain": "waterfront metropolis beside New York harbour",
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
        "country_name": "",
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


def make_recipe(destinations, horizon_y, label_settings):
    style = deepcopy(STYLE_PRESET)
    style["canvas"]["horizon_y"] = horizon_y

    # Permit only the requested destination labels when the option is enabled.
    if label_settings.get("enabled"):
        style["negative_rules"] = [
            rule for rule in style["negative_rules"]
            if rule not in ("text", "labels")
        ]
        style["negative_rules"].append(
            "any extra wording, captions or text other than the approved destination labels"
        )

    width = style["canvas"]["width"]
    height = style["canvas"]["height"]
    regions = build_regions(len(destinations), width, height, horizon_y)

    final_destinations = []
    for index, destination in enumerate(destinations):
        item = deepcopy(destination)
        item["position"] = position_name(index, len(destinations))
        item["region"] = regions[index]

        if label_settings.get("enabled"):
            label_text = destination.get(
                "label_text",
                destination["display_name"].split(",")[0]
            )
            if label_settings.get("uppercase", True):
                label_text = label_text.upper()

            item["destination_label"] = {
                "text": label_text,
                "country_name": destination.get("country_name", ""),
                "placement": label_settings["placement"],
                "font_style": label_settings["font_style"],
                "colour": label_settings["colour"],
                "include_flag": label_settings.get("include_country_flags", True),
                "flag_placement": label_settings["flag_placement"],
                "flag_scale": label_settings["flag_scale"]
            }

        final_destinations.append(item)

    return {
        "recipe_version": "1.2",
        "build_name": "Destination Labels + Country Flags",
        "style_preset": style,
        "scene_type": "single seamless panoramic combined-destination travel artwork",
        "destination_label_style": label_settings,
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
    label_style = recipe.get("destination_label_style", {})
    labels_enabled = bool(label_style.get("enabled"))

    destination_lines = []
    approved_labels = []

    for item in recipe["destinations"]:
        destination_lines.append(
            f"{item['display_name']} on the {item['position']}: "
            f"feature {item['main_landmark']}. "
            f"Include {joined(item['secondary_elements'])}. "
            f"Preserve {joined(item['important_features'])}."
        )

        if labels_enabled and item.get("destination_label"):
            label = item["destination_label"]
            flag_instruction = ""
            if label.get("include_flag"):
                flag_instruction = (
                    f", with the correct {label.get('country_name', '')} national flag "
                    f"{label.get('flag_placement', '')}"
                )

            approved_labels.append(
                f'- "{label["text"]}" {label["placement"]}{flag_instruction}'
            )

    label_block = ""
    if labels_enabled:
        label_block = f"""
DESTINATION LABELS AND COUNTRY FLAGS:
Add only the following approved destination labels:
{chr(10).join(approved_labels)}

Use {label_style['font_style']}. Use {label_style['colour']} lettering, in a refined medium size that remains secondary to the landmarks. Keep every label clean, correctly spelled, evenly spaced and centred over its matching destination. Do not place the words inside boxes, banners or badges.
"""
        if label_style.get("include_country_flags"):
            label_block += (
                f"Attach a small, geographically correct national flag to each label. "
                f"Flag treatment: {label_style['flag_placement']}. "
                f"Use {label_style['flag_scale']} flags with crisp correct colours and proportions. "
                "Each flag must match the country of the destination directly beneath it. "
                "Do not substitute flags, invent flags or add extra symbols.\n"
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
{label_block}
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


def get_serif_font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed.ttf"
    ]

    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass

    return ImageFont.load_default()


def normalise_country(country):
    value = normalise(country)
    aliases = {
        "usa": "united states",
        "us": "united states",
        "america": "united states",
        "united states of america": "united states",
        "uk": "united kingdom",
        "england": "united kingdom",
        "great britain": "united kingdom",
        "britain": "united kingdom"
    }
    return aliases.get(value, value)


def draw_union_jack(draw, box):
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    draw.rectangle(box, fill=(20, 45, 105), outline=(255, 245, 220), width=1)

    # Broad white diagonals.
    draw.line((x1, y1, x2, y2), fill=(255, 255, 255), width=max(2, h // 5))
    draw.line((x1, y2, x2, y1), fill=(255, 255, 255), width=max(2, h // 5))

    # Red diagonals.
    draw.line((x1, y1, x2, y2), fill=(190, 25, 45), width=max(1, h // 10))
    draw.line((x1, y2, x2, y1), fill=(190, 25, 45), width=max(1, h // 10))

    # Central white and red cross.
    draw.rectangle((x1, y1 + h * 0.36, x2, y1 + h * 0.64), fill=(255, 255, 255))
    draw.rectangle((x1 + w * 0.36, y1, x1 + w * 0.64, y2), fill=(255, 255, 255))
    draw.rectangle((x1, y1 + h * 0.43, x2, y1 + h * 0.57), fill=(190, 25, 45))
    draw.rectangle((x1 + w * 0.43, y1, x1 + w * 0.57, y2), fill=(190, 25, 45))


def draw_country_flag(draw, country, box):
    """Draw a compact flag approximation in the composition guide."""
    x1, y1, x2, y2 = [int(v) for v in box]
    w = x2 - x1
    h = y2 - y1
    name = normalise_country(country)

    draw.rectangle((x1, y1, x2, y2), fill=(250, 250, 245), outline=(90, 75, 55), width=2)

    if name == "italy":
        third = w / 3
        draw.rectangle((x1, y1, x1 + third, y2), fill=(0, 146, 70))
        draw.rectangle((x1 + third, y1, x1 + 2 * third, y2), fill=(255, 255, 255))
        draw.rectangle((x1 + 2 * third, y1, x2, y2), fill=(206, 43, 55))

    elif name == "france":
        third = w / 3
        draw.rectangle((x1, y1, x1 + third, y2), fill=(20, 60, 150))
        draw.rectangle((x1 + third, y1, x1 + 2 * third, y2), fill=(255, 255, 255))
        draw.rectangle((x1 + 2 * third, y1, x2, y2), fill=(220, 35, 55))

    elif name == "greece":
        stripe = h / 9
        for i in range(9):
            colour = (30, 95, 175) if i % 2 == 0 else (255, 255, 255)
            draw.rectangle((x1, y1 + i * stripe, x2, y1 + (i + 1) * stripe), fill=colour)
        canton = int(h * 0.56)
        draw.rectangle((x1, y1, x1 + canton, y1 + canton), fill=(30, 95, 175))
        cross = max(2, canton // 5)
        draw.rectangle((x1 + canton * 0.4, y1, x1 + canton * 0.6, y1 + canton), fill=(255, 255, 255))
        draw.rectangle((x1, y1 + canton * 0.4, x1 + canton, y1 + canton * 0.6), fill=(255, 255, 255))

    elif name == "united kingdom":
        draw_union_jack(draw, (x1, y1, x2, y2))

    elif name == "united states":
        stripe = h / 13
        for i in range(13):
            colour = (190, 25, 45) if i % 2 == 0 else (255, 255, 255)
            draw.rectangle((x1, y1 + i * stripe, x2, y1 + (i + 1) * stripe), fill=colour)
        draw.rectangle((x1, y1, x1 + w * 0.43, y1 + h * 0.54), fill=(25, 55, 120))
        star_font = get_font(max(8, int(h * 0.26)))
        draw.text((x1 + 3, y1 - 1), "✦", fill=(255, 255, 255), font=star_font)

    elif name == "australia":
        draw.rectangle((x1, y1, x2, y2), fill=(15, 45, 115))
        draw_union_jack(draw, (x1, y1, x1 + w * 0.47, y1 + h * 0.52))
        star_font = get_font(max(8, int(h * 0.25)))
        for sx, sy in [
            (x1 + w * 0.66, y1 + h * 0.16),
            (x1 + w * 0.78, y1 + h * 0.38),
            (x1 + w * 0.62, y1 + h * 0.63),
            (x1 + w * 0.82, y1 + h * 0.75)
        ]:
            draw.text((sx, sy), "✦", fill=(255, 255, 255), font=star_font)

    else:
        # Generic fallback for countries not in the built-in flag renderer.
        initials = "".join(word[0] for word in country.split() if word)[:3].upper() or "FLAG"
        draw.rectangle((x1, y1, x2, y2), fill=(235, 225, 195))
        fallback_font = get_font(max(10, int(h * 0.32)))
        bbox = draw.textbbox((0, 0), initials, font=fallback_font)
        tx = x1 + (w - (bbox[2] - bbox[0])) / 2
        ty = y1 + (h - (bbox[3] - bbox[1])) / 2 - 2
        draw.text((tx, ty), initials, fill=(75, 55, 35), font=fallback_font)

    draw.rectangle((x1, y1, x2, y2), outline=(85, 67, 45), width=2)


def make_guide(recipe):
    canvas = recipe["style_preset"]["canvas"]
    width = canvas["width"]
    height = canvas["height"]
    horizon_y = canvas["horizon_y"]
    label_style = recipe.get("destination_label_style", {})
    labels_enabled = bool(label_style.get("enabled"))

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

    guide_title_font = get_font(42)
    guide_body_font = get_font(25)
    small_font = get_font(20)

    destination_count = len(recipe["destinations"])
    label_font_size = 50 if destination_count <= 3 else 38
    label_font = get_serif_font(label_font_size)

    colour_lookup = {
        "warm cream-gold": (255, 227, 157),
        "warm cream": (255, 242, 214),
        "soft white": (255, 255, 245),
        "golden yellow": (244, 196, 80)
    }
    label_rgb = colour_lookup.get(label_style.get("colour"), (255, 227, 157))

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

        building_count = 5 if destination_count <= 3 else 4
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

        if labels_enabled and item.get("destination_label"):
            label = item["destination_label"]
            label_text = label["text"]
            centre_x = x + w / 2
            label_y = 58

            bbox = draw.textbbox((0, 0), label_text, font=label_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = centre_x - text_w / 2

            # Soft painterly shadow behind warm serif label.
            draw.text(
                (text_x + 2, label_y + 2),
                label_text,
                fill=(65, 62, 58),
                font=label_font
            )
            draw.text(
                (text_x, label_y),
                label_text,
                fill=label_rgb,
                font=label_font
            )

            if label.get("include_flag") and label.get("country_name"):
                pole_top = label_y + text_h + 12
                pole_bottom = pole_top + 52
                draw.line(
                    (centre_x, pole_top, centre_x, pole_bottom),
                    fill=(222, 181, 83),
                    width=3
                )

                flag_w = 64 if destination_count <= 3 else 52
                flag_h = int(flag_w * 0.62)
                flag_x1 = centre_x + 2
                flag_y1 = pole_top + 4
                draw_country_flag(
                    draw,
                    label["country_name"],
                    (flag_x1, flag_y1, flag_x1 + flag_w, flag_y1 + flag_h)
                )

        else:
            # Informational guide card when actual artwork labels are disabled.
            label_right = min(width - 20, x + w - 20)
            draw.rounded_rectangle(
                (x + 20, 30, label_right, 140),
                radius=18,
                fill=(255, 250, 237),
                outline=(63, 49, 36),
                width=4
            )
            draw.text(
                (x + 38, 45),
                item["display_name"],
                fill=(48, 38, 28),
                font=guide_title_font
            )

            landmark = item["main_landmark"]
            if len(landmark) > 48:
                landmark = landmark[:45] + "..."
            draw.text(
                (x + 38, 96),
                landmark,
                fill=(83, 65, 47),
                font=guide_body_font
            )

        draw.text(
            (x + 28, height - 48),
            item["position"].upper(),
            fill=(35, 35, 35),
            font=small_font
        )

    draw.line((0, horizon_y, width, horizon_y), fill=(255, 255, 255), width=5)
    draw.text(
        (22, horizon_y + 14),
        "ONE CONTINUOUS HORIZON",
        fill=(255, 255, 255),
        font=guide_body_font
    )
    draw.text(
        (22, 170),
        "OPEN SKY + UPPER-LEFT SUNLIGHT",
        fill=(255, 255, 255),
        font=guide_body_font
    )

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


st.title("🎨 Place Blend Recipe Builder — Labels + Flags")
st.write(
    "Type one to four destinations. The app creates a JSON recipe, "
    "a visual 3:2 layout guide, optional destination labels with country flags, and a locked ChatGPT prompt."
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
            st.warning(
                "Custom place: check the landmark, country and supporting elements."
            )

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

        default_label = destination["display_name"].split(",")[0].upper()
        label_text = st.text_input(
            "Destination label text",
            value=default_label,
            key=f"label_text_{index}",
            help="Example: ROME, LONDON or NEW YORK"
        )

        country_name = st.text_input(
            "Country for the attached flag",
            value=destination.get("country_name", ""),
            key=f"country_name_{index}",
            help="Example: Italy, United Kingdom, United States, Australia or Greece"
        )

        updated = deepcopy(destination)
        updated["main_landmark"] = landmark.strip()
        updated["secondary_elements"] = [
            item.strip() for item in extras.split(",") if item.strip()
        ]
        updated["water"] = water
        updated["label_text"] = label_text.strip() or default_label
        updated["country_name"] = country_name.strip()
        edited.append(updated)

st.subheader("Destination label options")

include_labels = st.checkbox(
    "Include destination names in the finished artwork",
    value=False,
    help="Creates the elegant ROME / LONDON / NEW YORK label style shown in your reference."
)

if include_labels:
    include_country_flags = st.checkbox(
        "Attach the correct country flag to every destination label",
        value=True
    )

    label_colour = st.selectbox(
        "Label lettering colour",
        [
            "warm cream-gold",
            "warm cream",
            "soft white",
            "golden yellow"
        ],
        index=0
    )

    label_placement = st.selectbox(
        "Label placement",
        [
            "centred in the open sky directly above its matching main landmark",
            "high in the open sky above its matching destination",
            "close above the top of its matching main landmark"
        ],
        index=0
    )

    flag_placement = st.selectbox(
        "Country flag attachment style",
        [
            "directly beneath the label on a thin vertical warm-gold flagpole",
            "immediately to the right of the label on a short warm-gold pole",
            "directly beneath the label without a pole"
        ],
        index=0
    )

    flag_scale = st.selectbox(
        "Flag size",
        [
            "small and refined",
            "small-to-medium",
            "very small and subtle"
        ],
        index=0
    )

    uppercase_labels = st.checkbox(
        "Use uppercase destination names",
        value=True
    )
else:
    include_country_flags = False
    label_colour = "warm cream-gold"
    label_placement = "centred in the open sky directly above its matching main landmark"
    flag_placement = "directly beneath the label on a thin vertical warm-gold flagpole"
    flag_scale = "small and refined"
    uppercase_labels = True

label_settings = {
    "enabled": include_labels,
    "font_style": (
        "elegant classic high-contrast serif lettering inspired by premium vintage travel posters"
    ),
    "colour": label_colour,
    "size": "refined medium size",
    "placement": label_placement,
    "uppercase": uppercase_labels,
    "no_background_box": True,
    "include_country_flags": include_country_flags,
    "flag_placement": flag_placement,
    "flag_scale": flag_scale,
    "flag_accuracy": (
        "use the correct national flag colours, layout and proportions for each destination country"
    )
}

horizon_y = st.slider(
    "Horizon height",
    420,
    700,
    STYLE_PRESET["canvas"]["horizon_y"]
)

if st.button("Build recipe and guide", type="primary", use_container_width=True):
    if not edited:
        st.error("Enter at least one destination.")
    elif include_labels and include_country_flags and any(
        not item.get("country_name", "").strip() for item in edited
    ):
        st.error(
            "Add a country name for every destination so the recipe can attach the correct flag."
        )
    else:
        recipe = make_recipe(edited, horizon_y, label_settings)
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
        height=560
    )

    st.download_button(
        "Download prompt TXT",
        prompt.encode("utf-8"),
        "place_blend_prompt.txt",
        "text/plain",
        use_container_width=True
    )

    if recipe.get("destination_label_style", {}).get("enabled"):
        st.success(
            "The recipe now includes the elegant destination names and the correct country flags."
        )

    st.info(
        "Upload the approved reference image, the layout guide PNG and this prompt together."
    )
