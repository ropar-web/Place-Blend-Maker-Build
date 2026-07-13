
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

CANVAS_PRESETS = {
    "Landscape 3:2": {
        "orientation": "landscape",
        "format_description": "wide landscape travel-poster format",
        "ratio": "3:2",
        "width": 1536,
        "height": 1024,
        "default_horizon_y": 560,
        "horizon_min": 420,
        "horizon_max": 700
    },
    "Portrait 2:3": {
        "orientation": "portrait",
        "format_description": "tall portrait travel-poster format",
        "ratio": "2:3",
        "width": 1024,
        "height": 1536,
        "default_horizon_y": 900,
        "horizon_min": 700,
        "horizon_max": 1120
    }
}


ART_STYLE_PRESETS = {
    "Premium Travel Poster": {
        "prompt": "Use a premium illustrated travel-poster style with polished composition, refined painterly detail, crisp recognisable architecture, rich but controlled colour, and a cohesive gift-worthy finish.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset"],
    },
    "Vintage Retro Poster": {
        "prompt": "Use a vintage retro travel-poster style with bold simplified shapes, classic tourism-poster composition, clean sky areas, strong silhouettes, limited harmonious colours, subtle print texture, and nostalgic mid-century charm.",
        "recommended_blends": ["Side by Side", "Smooth Blend", "Poster Grid"],
    },
    "Soft Watercolour": {
        "prompt": "Use a soft hand-painted watercolour style with delicate washes, natural paper texture, gentle edges, elegant architectural detail, luminous atmosphere, and graceful painterly transitions.",
        "recommended_blends": ["Smooth Blend", "Layered Scene", "Main Place + Memory Inset"],
    },
    "Ink Sketch + Wash": {
        "prompt": "Use an architectural ink-sketch and watercolour-wash style with expressive hand-drawn linework, accurate building proportions, loose transparent colour, and a personal urban-sketchbook character.",
        "recommended_blends": ["Main Place + Memory Inset", "Side by Side", "Layered Scene"],
    },
    "Home to Home Map Art": {
        "prompt": "Use clean personalised map art with accurate country, state or region silhouettes, tasteful painterly colour inside the shapes, an elegant emotional connection motif, and uncluttered premium gift-print styling.",
        "recommended_blends": ["Map Connection"],
    },
    "Favourite Places Grid": {
        "prompt": "Create a coordinated collection of matching mini destination posters in one polished print, with consistent typography, colour harmony, spacing, visual weight, and a premium personalised wall-art finish.",
        "recommended_blends": ["Poster Grid"],
    },
}

BLEND_MODE_PRESETS = {
    "Smooth Blend": "Blend the destinations into one continuous artwork using shared sky, light, water, terrain, plants and overlapping architecture. Avoid a visible seam while keeping every place recognisable.",
    "Side by Side": "Compose the destinations side by side with a graceful transition. Give each location a clear visual zone and comparable importance, without a harsh divider or disconnected collage effect.",
    "Layered Scene": "Use a natural foreground, middle ground and background arrangement. Let one destination lead in the foreground while the others remain clearly recognisable in supporting depth layers.",
    "Main Place + Memory Inset": "Create one main hero destination and integrate the other place or places as smaller elegant memory insets, medallions or framed sketch elements that feel deliberately designed into the artwork.",
    "Map Connection": "Use accurate map silhouettes for the selected locations and connect them with an elegant line, heart path or travel route. Prioritise emotional storytelling and clean composition rather than a scenic panorama.",
    "Poster Grid": "Give each destination its own matching mini-poster tile inside one balanced grid. Keep all tiles consistent in style, scale, margins, typography and colour treatment.",
}

ACCURACY_MODE_PRESETS = {
    "Exact Landmark": "Prioritise landmark and geographic accuracy. Preserve defining shapes, proportions, materials, rooflines, domes, windows, terrain and local features. Do not substitute, duplicate or invent major structures.",
    "Balanced": "Balance recognisability with artistic beauty. Preserve the defining identity of each place while allowing tasteful simplification and harmonious composition.",
    "Artistic": "Prioritise mood and visual harmony while retaining enough landmark identity for each destination to remain recognisable.",
}


STYLE_RENDER_RULES = {
    "Premium Travel Poster": {
        "finish": "Detailed hand-painted digital travel-poster finish, crisp recognisable architecture, refined painterly texture, polished depth and atmospheric perspective.",
        "palette": "Rich but controlled destination-appropriate colours; cobalt sky, turquoise water where appropriate, warm cream, golden yellow, terracotta and coral may be used when geographically suitable.",
        "lighting": "Bright natural travel-poster sunlight with coherent shadows.",
        "exclude": "Do not use retro flat-vector simplification, pale watercolour washes, loose ink sketching, map silhouettes, poster tiles, photographic realism, 3D toy styling or childish clipart."
    },
    "Vintage Retro Poster": {
        "finish": "Authentic mid-century tourism-poster finish with simplified geometric forms, bold silhouettes, clean hard-edged colour shapes and subtle aged print texture.",
        "palette": "A limited harmonious retro palette chosen for the destinations; use muted teal, warm cream, ochre, burnt orange, dusty red and deep navy rather than glossy modern gradients.",
        "lighting": "Graphic poster lighting with simplified shadow shapes and strong readable contrast.",
        "exclude": "Do not use painterly digital brushwork, soft watercolour bleeding, loose ink outlines, photorealism, 3D rendering, map silhouettes or mixed mini-poster tiles unless Poster Grid is selected."
    },
    "Soft Watercolour": {
        "finish": "Genuine hand-painted watercolour appearance on lightly textured paper, translucent layered washes, soft controlled edges and delicate architectural detail.",
        "palette": "Luminous transparent destination-appropriate pigments with soft blues, sea greens, warm stone, terracotta and restrained floral accents.",
        "lighting": "Gentle natural light expressed through transparent washes and preserved paper highlights.",
        "exclude": "Do not use bold retro vector shapes, thick digital outlines, heavy oil-paint texture, glossy 3D rendering, map silhouettes, poster-grid framing or photographic realism."
    },
    "Ink Sketch + Wash": {
        "finish": "Architectural urban-sketch finish with confident hand-drawn ink lines, accurate proportions, selective loose watercolour washes and visible white paper.",
        "palette": "Restrained natural watercolour accents over warm black or sepia linework.",
        "lighting": "Suggested with sparse wash shadows and line hatching, not cinematic rendering.",
        "exclude": "Do not use retro vector poster shapes, polished digital-painterly rendering, full-coverage oil paint, map silhouettes, 3D models, photographic realism or a tiled poster grid unless explicitly selected."
    },
    "Home to Home Map Art": {
        "finish": "Clean premium personalised map artwork with accurate map silhouettes, controlled painterly fills and a simple elegant connection motif.",
        "palette": "A coordinated restrained gift-print palette with clear contrast between the map shapes and background.",
        "lighting": "Flat print-design treatment; no scenic sunlight or dimensional landscape lighting.",
        "exclude": "Do not create scenic landmark panoramas, painterly city blends, retro tourism posters, watercolour village scenes, ink architectural portraits, 3D maps or unrelated decorative objects."
    },
    "Favourite Places Grid": {
        "finish": "A clean coordinated grid of separate matching mini travel posters, each with consistent margins, scale, typography and art treatment.",
        "palette": "One shared coordinated palette across all tiles while allowing each destination its own recognisable local colours.",
        "lighting": "Consistent lighting treatment across every mini poster.",
        "exclude": "Do not merge all places into one continuous panorama, do not use map silhouettes unless requested, do not mix different illustration styles between tiles, and do not create irregular collage overlaps."
    },
}

DEFAULT_BLEND_BY_STYLE = {
    "Premium Travel Poster": "Smooth Blend",
    "Vintage Retro Poster": "Side by Side",
    "Soft Watercolour": "Smooth Blend",
    "Ink Sketch + Wash": "Main Place + Memory Inset",
    "Home to Home Map Art": "Map Connection",
    "Favourite Places Grid": "Poster Grid",
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


def build_regions(count, width, height, horizon_y, orientation):
    """
    Create overlapping horizontal destination zones.

    Portrait keeps the same left-to-right destination order used in the
    approved portrait examples, but uses stronger overlap and taller
    architectural masses so the result reads as one vertical poster rather
    than narrow separate columns.
    """
    overlap_ratio = 0.09 if orientation == "portrait" else 0.05
    overlap = int(width * overlap_ratio)
    effective_width = width + overlap * max(0, count - 1)
    zone_width = effective_width // count
    regions = []

    for index in range(count):
        x = max(0, index * (zone_width - overlap))
        w = min(width - x, zone_width)
        regions.append({
            "x": x,
            "y": int(height * (0.10 if orientation == "portrait" else 0.14)),
            "width": w,
            "height": int(height * (0.82 if orientation == "portrait" else 0.72)),
            "horizon_y": horizon_y,
            "overlap_px": overlap if index else 0,
            "orientation": orientation
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


def make_recipe(destinations, horizon_y, label_settings, canvas_settings, art_settings):
    """Build a genuinely style-specific recipe instead of relabelling one scenic template."""
    style_name = art_settings.get("style", "Premium Travel Poster")
    blend_name = art_settings.get("blend_mode", DEFAULT_BLEND_BY_STYLE.get(style_name, "Smooth Blend"))
    canvas = deepcopy(canvas_settings)
    canvas.pop("default_horizon_y", None)
    canvas.pop("horizon_min", None)
    canvas.pop("horizon_max", None)

    if style_name == "Home to Home Map Art":
        return make_map_recipe(destinations, label_settings, canvas, art_settings)
    if style_name == "Favourite Places Grid":
        return make_grid_recipe(destinations, label_settings, canvas, art_settings)
    return make_scenic_recipe(destinations, horizon_y, label_settings, canvas, art_settings)


def make_scenic_recipe(destinations, horizon_y, label_settings, canvas, art_settings):
    style_name = art_settings.get("style", "Premium Travel Poster")
    render = STYLE_RENDER_RULES[style_name]
    canvas = deepcopy(canvas)
    canvas["horizon_y"] = horizon_y

    composition_by_style = {
        "Premium Travel Poster": [
            "one cohesive combined-destination illustrated scene",
            "recognisable architecture with refined painterly depth",
            "natural foreground, middle ground and distant background",
            "use the selected blend structure exactly"
        ],
        "Vintage Retro Poster": [
            "one consistent mid-century travel-poster composition",
            "bold simplified silhouettes and clean graphic depth",
            "limited colour shapes with no painterly or watercolour mixing",
            "use the selected blend structure exactly"
        ],
        "Soft Watercolour": [
            "one coherent hand-painted watercolour composition",
            "soft controlled transitions and visible paper highlights",
            "delicate architectural detail without vector-poster shapes",
            "use the selected blend structure exactly"
        ],
        "Ink Sketch + Wash": [
            "one coherent architectural sketch composition",
            "confident ink linework with selective transparent washes",
            "visible white paper and accurate building proportions",
            "use the selected blend structure exactly"
        ]
    }
    negative_by_style = [x.strip() for x in render["exclude"].split(",") if x.strip()]
    if label_settings.get("enabled"):
        negative_by_style.append("any text other than the approved labels and requested personalisation")
    else:
        negative_by_style.append("unrequested text or labels")

    regions = build_regions(len(destinations), canvas["width"], canvas["height"], horizon_y, canvas["orientation"])
    final_destinations = []
    for index, destination in enumerate(destinations):
        item = deepcopy(destination)
        item["position"] = position_name(index, len(destinations))
        item["region"] = regions[index]
        if label_settings.get("enabled"):
            label_text = destination.get("label_text", destination["display_name"].split(",")[0])
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
                "flag_anchor": label_settings["flag_anchor"],
                "flag_scale": label_settings["flag_scale"],
                "flag_width_percent_of_destination_zone": label_settings["flag_width_percent_of_destination_zone"],
                "flag_attachment_rule": label_settings["flag_attachment_rule"]
            }
        final_destinations.append(item)

    blend_name = art_settings.get("blend_mode", "Smooth Blend")
    transition_rules = {
        "blend_mode": blend_name,
        "single_locked_style": True,
        "no_mixed_rendering_methods": True,
        "no_unrelated_landmarks": True
    }
    if blend_name == "Smooth Blend":
        transition_rules.update({"continuous_scene": True, "no_hard_dividers": True, "shared_atmosphere": True})
    elif blend_name == "Side by Side":
        transition_rules.update({"distinct_destination_zones": True, "graceful_transition": True, "equal_visual_weight": True})
    elif blend_name == "Layered Scene":
        transition_rules.update({"foreground_middle_background_layers": True, "no_panels": True})
    elif blend_name == "Main Place + Memory Inset":
        transition_rules.update({"primary_hero_scene": True, "secondary_memory_insets": True})

    return {
        "recipe_version": "1.4.0",
        "build_name": "Multi-Style Place Blender 2.1",
        "style_family": "scenic_art",
        "style_preset": {
            "collection_name": f"{style_name} Collection",
            "canvas": canvas,
            "finish": render["finish"],
            "palette": render["palette"],
            "lighting": render["lighting"],
            "composition": composition_by_style.get(style_name, composition_by_style["Premium Travel Poster"]),
            "negative_rules": negative_by_style
        },
        "scene_type": "combined_destination_scenic_artwork",
        "destination_label_style": label_settings,
        "art_settings": art_settings,
        "destinations": final_destinations,
        "transition_rules": transition_rules
    }


def make_map_recipe(destinations, label_settings, canvas, art_settings):
    count = len(destinations)
    width, height = canvas["width"], canvas["height"]
    margin = int(width * 0.07)
    gap = int(width * 0.05)
    subject_width = (width - 2 * margin - gap * max(0, count - 1)) // max(1, count)
    subjects = []
    for i, destination in enumerate(destinations):
        city = destination.get("typed_name") or destination["display_name"].split(",")[0]
        country = destination.get("country_name") or destination["display_name"]
        subjects.append({
            "type": "accurate_geographic_map_silhouette",
            "place_name": country,
            "city_or_location_label": city,
            "display_name": destination["display_name"],
            "position": position_name(i, count),
            "region": {
                "x": margin + i * (subject_width + gap),
                "y": int(height * 0.18),
                "width": subject_width,
                "height": int(height * 0.52)
            },
            "fill_treatment": "controlled colourful painterly texture clipped strictly inside the map silhouette",
            "outline_rule": "preserve the correct geographic outline and islands"
        })
    title = art_settings.get("title_text", "").strip() or "Home to Home"
    subtitle = art_settings.get("subtitle_text", "").strip()
    return {
        "recipe_version": "1.4.0",
        "build_name": "Multi-Style Place Blender 2.1",
        "style_family": "map_art",
        "style_preset": {
            "collection_name": "Home to Home Map Art Collection",
            "canvas": canvas,
            "finish": "clean premium personalised map artwork with accurate silhouettes and controlled painterly fills",
            "palette": "warm neutral paper background with coordinated vibrant paint textures and dark elegant lettering",
            "lighting": "flat print-design treatment with no scenic lighting",
            "composition": [
                f"{count} accurate map silhouettes arranged with generous white space",
                "an elegant connecting line, travel route or heart loop between the map subjects",
                "place labels beneath their matching silhouettes",
                "title centred beneath or between the connected maps"
            ],
            "negative_rules": [
                "scenic landscapes", "buildings", "landmark panoramas", "horizon line", "sky", "water scene",
                "travel-poster scenery", "architectural sketch scene", "poster grid", "3D maps", "incorrect map outlines",
                "unrelated decorative objects", "mixed art styles"
            ]
        },
        "scene_type": "home_to_home_map_connection_artwork",
        "art_settings": art_settings,
        "map_subjects": subjects,
        "connection_element": {
            "type": "elegant heart-line or travel-route connection",
            "connects": [s["place_name"] for s in subjects],
            "must_not_obscure_maps": True
        },
        "text_elements": {
            "title": title,
            "subtitle": subtitle,
            "place_labels": [{"place": s["place_name"], "location": s["city_or_location_label"]} for s in subjects],
            "spelling_must_be_exact": True
        },
        "transition_rules": {
            "map_connection_only": True,
            "no_scenic_blending": True,
            "single_locked_style": True
        }
    }


def make_grid_recipe(destinations, label_settings, canvas, art_settings):
    count = len(destinations)
    cols = 2 if count <= 4 else 3
    rows = (count + cols - 1) // cols
    margin = int(canvas["width"] * 0.06)
    gap = int(canvas["width"] * 0.025)
    tile_w = (canvas["width"] - 2 * margin - gap * (cols - 1)) // cols
    tile_h = int((canvas["height"] * 0.72 - gap * (rows - 1)) / max(1, rows))
    tiles = []
    for i, destination in enumerate(destinations):
        row, col = divmod(i, cols)
        tiles.append({
            "tile_number": i + 1,
            "display_name": destination["display_name"],
            "country_name": destination.get("country_name", ""),
            "main_landmark": destination.get("main_landmark", "recognisable local landmark"),
            "important_features": destination.get("important_features", []),
            "region": {"x": margin + col * (tile_w + gap), "y": margin + row * (tile_h + gap), "width": tile_w, "height": tile_h},
            "title_text": destination.get("label_text", destination["display_name"].split(",")[0]).upper()
        })
    return {
        "recipe_version": "1.4.0",
        "build_name": "Multi-Style Place Blender 2.1",
        "style_family": "poster_grid",
        "style_preset": {
            "collection_name": "Favourite Places Grid Collection",
            "canvas": canvas,
            "finish": "coordinated set of matching mini travel posters with consistent illustration treatment",
            "palette": "one shared coordinated palette across every tile with destination-specific accents",
            "lighting": "consistent graphic lighting across all mini posters",
            "composition": [f"{count} evenly spaced poster tiles in a {rows} by {cols} grid", "consistent margins, typography, scale and visual weight", "optional personalised heading below the grid"],
            "negative_rules": ["seamless panorama", "overlapping collage", "map silhouettes", "different art styles between tiles", "irregular tile sizes", "unrequested text"]
        },
        "scene_type": "favourite_places_multi_poster_grid",
        "art_settings": art_settings,
        "poster_tiles": tiles,
        "text_elements": {"title": art_settings.get("title_text", "").strip(), "subtitle": art_settings.get("subtitle_text", "").strip()},
        "transition_rules": {"separate_equal_tiles": True, "consistent_style_across_tiles": True, "no_scenic_merge": True}
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
    family = recipe.get("style_family", "scenic_art")
    if family == "map_art":
        return make_map_prompt(recipe)
    if family == "poster_grid":
        return make_grid_prompt(recipe)
    return make_scenic_prompt(recipe)


def make_scenic_prompt(recipe):
    style = recipe["style_preset"]
    label_style = recipe.get("destination_label_style", {})
    labels_enabled = bool(label_style.get("enabled"))
    art_settings = recipe.get("art_settings", {})
    style_name = art_settings.get("style", "Premium Travel Poster")
    blend_name = art_settings.get("blend_mode", "Smooth Blend")
    accuracy_name = art_settings.get("accuracy_mode", "Balanced")
    style_direction = ART_STYLE_PRESETS[style_name]["prompt"]
    render_rules = STYLE_RENDER_RULES[style_name]
    blend_direction = BLEND_MODE_PRESETS.get(blend_name, BLEND_MODE_PRESETS["Smooth Blend"])
    accuracy_direction = ACCURACY_MODE_PRESETS.get(accuracy_name, ACCURACY_MODE_PRESETS["Balanced"])
    title_text = art_settings.get("title_text", "").strip()
    subtitle_text = art_settings.get("subtitle_text", "").strip()

    destination_lines, approved_labels = [], []
    for item in recipe["destinations"]:
        destination_lines.append(
            f"{item['display_name']} on the {item['position']}: feature {item['main_landmark']}. "
            f"Include {joined(item.get('secondary_elements', []))}. Preserve {joined(item.get('important_features', []))}."
        )
        if labels_enabled and item.get("destination_label"):
            approved_labels.append(f'- "{item["destination_label"]["text"]}" {item["destination_label"]["placement"]}')

    label_block = ""
    if labels_enabled:
        label_block = "APPROVED DESTINATION LABELS ONLY:\n" + "\n".join(approved_labels) + "\nSpell every label exactly. Do not add any other words."

    requested = []
    if title_text:
        requested.append(f'main title exactly: "{title_text}"')
    if subtitle_text:
        requested.append(f'subtitle exactly: "{subtitle_text}"')
    personalisation = "Include only " + "; ".join(requested) + "." if requested else "Do not add unrequested wording."

    return f"""Create one high-quality personalised combined-destination artwork.

LOCKED ART STYLE — USE ONLY {style_name.upper()}:
{style_direction}
Finish: {render_rules['finish']}
Palette: {render_rules['palette']}
Lighting/treatment: {render_rules['lighting']}
STYLE EXCLUSIONS: {render_rules['exclude']}
Do not combine or borrow characteristics from any other art style.

SELECTED BLEND STRUCTURE — {blend_name.upper()}:
{blend_direction}

ACCURACY — {accuracy_name.upper()}:
{accuracy_direction}

CANVAS:
{style['canvas']['format_description'].capitalize()}, exact {style['canvas']['ratio']} ratio, {style['canvas']['width']} × {style['canvas']['height']} pixels.

DESTINATIONS:
{chr(10).join(destination_lines)}

{label_block}
PERSONALISATION: {personalisation}

Use uploaded place references only for geographic identity, architecture and local details. Ignore conflicting art styles in reference photographs. Keep one consistent selected style edge to edge. Do not include mixed styles, warped architecture, duplicate landmarks, unrelated places, logos, watermarks or random text.
"""


def make_map_prompt(recipe):
    art = recipe.get("art_settings", {})
    accuracy = art.get("accuracy_mode", "Balanced")
    subjects = recipe["map_subjects"]
    subject_lines = []
    for subject in subjects:
        subject_lines.append(
            f"- Accurate map silhouette of {subject['place_name']} positioned {subject['position']}; "
            f"label beneath it with {subject['place_name']} and {subject['city_or_location_label']}."
        )
    text = recipe["text_elements"]
    return f"""Create a premium personalised HOME TO HOME MAP ART print.

STYLE LOCK:
Use only clean map-connection artwork. Do not create a scenic travel poster, skyline, buildings, landscape, water scene, architectural sketch or poster grid.

CANVAS:
{recipe['style_preset']['canvas']['format_description'].capitalize()}, exact {recipe['style_preset']['canvas']['ratio']} ratio, {recipe['style_preset']['canvas']['width']} × {recipe['style_preset']['canvas']['height']} pixels.

MAP SUBJECTS:
{chr(10).join(subject_lines)}
Preserve correct national, state or regional outlines, coastlines and important islands. Accuracy mode: {accuracy}.

DESIGN:
Fill each map silhouette with coordinated colourful painterly texture clipped strictly inside the geographic shape. Keep a warm neutral paper background and generous white space. Connect the maps with one elegant fine line, travel route or heart loop. The connection must not obscure either silhouette.

TEXT:
Main title exactly: "{text['title']}".
Subtitle exactly: "{text['subtitle']}" if non-empty.
Spell all place and city labels exactly. Use elegant restrained typography.

DO NOT INCLUDE:
Landmarks, buildings, scenic horizons, sky, water, mountains, travel-poster scenery, mini-poster tiles, 3D maps, incorrect outlines, unrelated decorations, mixed art styles, logos, watermarks or extra text.
"""


def make_grid_prompt(recipe):
    art = recipe.get("art_settings", {})
    tile_lines = []
    for tile in recipe["poster_tiles"]:
        tile_lines.append(
            f"- Tile {tile['tile_number']}: {tile['display_name']}; feature {tile['main_landmark']}; "
            f"preserve {joined(tile.get('important_features', []))}; title exactly \"{tile['title_text']}\"."
        )
    return f"""Create one premium FAVOURITE PLACES GRID print.

STYLE LOCK:
Use one consistent coordinated mini travel-poster style across every tile. Do not merge the destinations into one panorama and do not mix illustration styles between tiles.

CANVAS:
{recipe['style_preset']['canvas']['format_description'].capitalize()}, exact {recipe['style_preset']['canvas']['ratio']} ratio, {recipe['style_preset']['canvas']['width']} × {recipe['style_preset']['canvas']['height']} pixels.

POSTER TILES:
{chr(10).join(tile_lines)}

LAYOUT:
Use equal clean tiles, consistent margins, typography, scale, border treatment, colour harmony and visual weight. Keep every destination clearly recognisable. Accuracy mode: {art.get('accuracy_mode', 'Balanced')}.

PERSONALISATION:
Overall title exactly: "{recipe['text_elements'].get('title', '')}" if non-empty.
Overall subtitle exactly: "{recipe['text_elements'].get('subtitle', '')}" if non-empty.

DO NOT INCLUDE:
A seamless scenic panorama, map silhouettes, overlapping collage pieces, irregular tile sizes, different styles between tiles, duplicate landmarks, unrelated destinations, logos, watermarks or extra wording.
"""

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
    # Pillow drawing methods require integer pixel coordinates.
    x1, y1, x2, y2 = [int(round(value)) for value in box]
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    def px(value):
        return int(round(value))

    draw.rectangle(
        (x1, y1, x2, y2),
        fill=(20, 45, 105),
        outline=(255, 245, 220),
        width=1
    )

    draw.line(
        (x1, y1, x2, y2),
        fill=(255, 255, 255),
        width=max(2, int(h // 5))
    )
    draw.line(
        (x1, y2, x2, y1),
        fill=(255, 255, 255),
        width=max(2, int(h // 5))
    )
    draw.line(
        (x1, y1, x2, y2),
        fill=(190, 25, 45),
        width=max(1, int(h // 10))
    )
    draw.line(
        (x1, y2, x2, y1),
        fill=(190, 25, 45),
        width=max(1, int(h // 10))
    )

    draw.rectangle(
        (x1, px(y1 + h * 0.36), x2, px(y1 + h * 0.64)),
        fill=(255, 255, 255)
    )
    draw.rectangle(
        (px(x1 + w * 0.36), y1, px(x1 + w * 0.64), y2),
        fill=(255, 255, 255)
    )
    draw.rectangle(
        (x1, px(y1 + h * 0.43), x2, px(y1 + h * 0.57)),
        fill=(190, 25, 45)
    )
    draw.rectangle(
        (px(x1 + w * 0.43), y1, px(x1 + w * 0.57), y2),
        fill=(190, 25, 45)
    )


def draw_country_flag(draw, country, box):
    """Draw a compact flag approximation in the composition guide."""
    x1, y1, x2, y2 = [int(round(value)) for value in box]
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    name = normalise_country(country)

    def px(value):
        return int(round(value))

    def rect(coords, **kwargs):
        draw.rectangle(tuple(px(value) for value in coords), **kwargs)

    draw.rectangle(
        (x1, y1, x2, y2),
        fill=(250, 250, 245),
        outline=(90, 75, 55),
        width=2
    )

    if name == "italy":
        third = w / 3
        rect((x1, y1, x1 + third, y2), fill=(0, 146, 70))
        rect((x1 + third, y1, x1 + 2 * third, y2), fill=(255, 255, 255))
        rect((x1 + 2 * third, y1, x2, y2), fill=(206, 43, 55))

    elif name == "france":
        third = w / 3
        rect((x1, y1, x1 + third, y2), fill=(20, 60, 150))
        rect((x1 + third, y1, x1 + 2 * third, y2), fill=(255, 255, 255))
        rect((x1 + 2 * third, y1, x2, y2), fill=(220, 35, 55))

    elif name == "greece":
        stripe = h / 9
        for i in range(9):
            colour = (30, 95, 175) if i % 2 == 0 else (255, 255, 255)
            rect(
                (x1, y1 + i * stripe, x2, y1 + (i + 1) * stripe),
                fill=colour
            )
        canton = px(h * 0.56)
        rect((x1, y1, x1 + canton, y1 + canton), fill=(30, 95, 175))
        rect(
            (x1 + canton * 0.4, y1, x1 + canton * 0.6, y1 + canton),
            fill=(255, 255, 255)
        )
        rect(
            (x1, y1 + canton * 0.4, x1 + canton, y1 + canton * 0.6),
            fill=(255, 255, 255)
        )

    elif name == "united kingdom":
        draw_union_jack(draw, (x1, y1, x2, y2))

    elif name == "united states":
        stripe = h / 13
        for i in range(13):
            colour = (190, 25, 45) if i % 2 == 0 else (255, 255, 255)
            rect(
                (x1, y1 + i * stripe, x2, y1 + (i + 1) * stripe),
                fill=colour
            )
        rect(
            (x1, y1, x1 + w * 0.43, y1 + h * 0.54),
            fill=(25, 55, 120)
        )
        star_font = get_font(max(8, int(h * 0.26)))
        draw.text((x1 + 3, y1 - 1), "✦", fill=(255, 255, 255), font=star_font)

    elif name == "australia":
        draw.rectangle((x1, y1, x2, y2), fill=(15, 45, 115))
        draw_union_jack(
            draw,
            (
                x1,
                y1,
                px(x1 + w * 0.47),
                px(y1 + h * 0.52)
            )
        )
        star_font = get_font(max(8, int(h * 0.25)))
        for sx, sy in [
            (x1 + w * 0.66, y1 + h * 0.16),
            (x1 + w * 0.78, y1 + h * 0.38),
            (x1 + w * 0.62, y1 + h * 0.63),
            (x1 + w * 0.82, y1 + h * 0.75)
        ]:
            draw.text(
                (px(sx), px(sy)),
                "✦",
                fill=(255, 255, 255),
                font=star_font
            )

    else:
        initials = "".join(
            word[0] for word in country.split() if word
        )[:3].upper() or "FLAG"
        draw.rectangle((x1, y1, x2, y2), fill=(235, 225, 195))
        fallback_font = get_font(max(10, int(h * 0.32)))
        bbox = draw.textbbox((0, 0), initials, font=fallback_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        tx = px(x1 + (w - text_width) / 2)
        ty = px(y1 + (h - text_height) / 2 - 2)
        draw.text(
            (tx, ty),
            initials,
            fill=(75, 55, 35),
            font=fallback_font
        )

    draw.rectangle(
        (x1, y1, x2, y2),
        outline=(85, 67, 45),
        width=2
    )


def make_guide(recipe):
    family = recipe.get("style_family", "scenic_art")
    if family == "map_art":
        canvas = recipe["style_preset"]["canvas"]
        width, height = canvas["width"], canvas["height"]
        image = Image.new("RGB", (width, height), (247, 242, 232))
        draw = ImageDraw.Draw(image)
        title_font = get_serif_font(max(30, int(height * 0.055)))
        label_font = get_serif_font(max(20, int(height * 0.03)))
        subjects = recipe.get("map_subjects", [])
        centres = []
        for i, subject in enumerate(subjects):
            r = subject["region"]
            x1, y1 = r["x"], r["y"]
            x2, y2 = x1 + r["width"], y1 + r["height"]
            draw.rounded_rectangle((x1, y1, x2, y2), radius=28, fill=(225, 188, 158), outline=(85, 70, 55), width=4)
            cx, cy = (x1+x2)//2, (y1+y2)//2
            centres.append((cx, cy))
            name = subject["place_name"]
            city = subject["city_or_location_label"]
            bbox = draw.textbbox((0,0), name, font=label_font)
            draw.text((cx-(bbox[2]-bbox[0])//2, y2+18), name, fill=(55,45,35), font=label_font)
            bbox2 = draw.textbbox((0,0), city, font=label_font)
            draw.text((cx-(bbox2[2]-bbox2[0])//2, y2+55), city, fill=(90,75,60), font=label_font)
        if len(centres) >= 2:
            for a,b in zip(centres, centres[1:]):
                draw.line((a[0], a[1]-35, b[0], b[1]-35), fill=(95,55,55), width=4)
        title = recipe.get("text_elements",{}).get("title", "Home to Home")
        bbox = draw.textbbox((0,0), title, font=title_font)
        draw.text(((width-(bbox[2]-bbox[0]))//2, int(height*0.84)), title, fill=(55,45,35), font=title_font)
        return image
    if family == "poster_grid":
        canvas = recipe["style_preset"]["canvas"]
        width, height = canvas["width"], canvas["height"]
        image = Image.new("RGB", (width, height), (247, 242, 232))
        draw = ImageDraw.Draw(image)
        font = get_font(max(18, int(height * 0.025)))
        for tile in recipe.get("poster_tiles", []):
            r = tile["region"]
            x1,y1=r["x"],r["y"]
            x2,y2=x1+r["width"],y1+r["height"]
            draw.rounded_rectangle((x1,y1,x2,y2), radius=20, fill=(213,228,226), outline=(70,70,65), width=3)
            txt=tile["title_text"]
            bbox=draw.textbbox((0,0),txt,font=font)
            draw.text((x1+(r["width"]-(bbox[2]-bbox[0]))//2, y1+14), txt, fill=(45,55,60), font=font)
        return image
    canvas = recipe["style_preset"]["canvas"]
    width = canvas["width"]
    height = canvas["height"]
    horizon_y = canvas["horizon_y"]
    orientation = canvas.get("orientation", "landscape")
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

    scale = height / 1024
    destination_count = len(recipe["destinations"])

    guide_title_font = get_font(max(26, int(42 * min(scale, 1.35))))
    guide_body_font = get_font(max(18, int(25 * min(scale, 1.35))))
    small_font = get_font(max(15, int(20 * min(scale, 1.25))))

    if orientation == "portrait":
        label_font_size = 43 if destination_count <= 3 else 31
        top_label_y = 82
    else:
        label_font_size = 50 if destination_count <= 3 else 38
        top_label_y = 58

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

        vertical_scale = 1.45 if orientation == "portrait" else 1.0
        base_y = horizon_y + int(95 * vertical_scale)
        terrain = item.get("terrain", "").lower()

        if "cliff" in terrain or "hill" in terrain:
            points = [
                (x, height),
                (x, base_y + int(100 * vertical_scale)),
                (x + int(w * 0.18), base_y - int(30 * vertical_scale)),
                (x + int(w * 0.42), base_y - int(120 * vertical_scale)),
                (x + int(w * 0.66), base_y - int(50 * vertical_scale)),
                (x + w, base_y + int(100 * vertical_scale)),
                (x + w, height)
            ]
            draw.polygon(points, fill=colour)
        else:
            draw.rounded_rectangle(
                (
                    x + 14,
                    horizon_y - int(55 * vertical_scale),
                    x + w - 14,
                    height - int(65 * vertical_scale)
                ),
                radius=28,
                fill=colour
            )

        building_count = 4 if orientation == "portrait" else (5 if destination_count <= 3 else 4)
        building_width = max(
            38 if orientation == "portrait" else 54,
            int(w / (building_count + 1.35))
        )
        gap = max(
            8 if orientation == "portrait" else 16,
            int((w - building_count * building_width) / (building_count + 1))
        )

        landmark_anchor_x = int(x + w / 2)
        landmark_anchor_y = int(horizon_y - 245 * vertical_scale)

        for building_index in range(building_count):
            bx = x + gap + building_index * (building_width + gap)
            base_height = 135 if orientation == "portrait" else 110
            variation = 190 if orientation == "portrait" else 140
            bh = int(
                (base_height + ((building_index * 31 + index * 23) % variation))
                * vertical_scale
            )
            by = horizon_y - bh - int(10 * vertical_scale)

            draw.rounded_rectangle(
                (bx, by, bx + building_width, horizon_y + int(30 * vertical_scale)),
                radius=8,
                fill=(250, 239, 214),
                outline=(79, 60, 42),
                width=3
            )

            has_dome = (
                "dome" in " ".join(item.get("important_features", [])).lower()
                and building_index in (1, 3)
            )

            roof_extension = int(42 * vertical_scale)
            if has_dome:
                draw.ellipse(
                    (
                        bx + 4,
                        by - roof_extension,
                        bx + building_width - 4,
                        by + int(30 * vertical_scale)
                    ),
                    fill=(34, 92, 172),
                    outline=(79, 60, 42),
                    width=3
                )
                roof_y = by - roof_extension
            else:
                draw.polygon(
                    [
                        (bx - 3, by + 4),
                        (bx + building_width // 2, by - roof_extension),
                        (bx + building_width + 3, by + 4)
                    ],
                    fill=(198, 96, 59),
                    outline=(79, 60, 42)
                )
                roof_y = by - roof_extension

            if building_index == building_count // 2:
                landmark_anchor_x = int(bx + building_width / 2)
                landmark_anchor_y = int(roof_y)

        if labels_enabled and item.get("destination_label"):
            label = item["destination_label"]
            label_text = label["text"]
            centre_x = x + w / 2
            label_y = top_label_y

            bbox = draw.textbbox((0, 0), label_text, font=label_font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            text_x = centre_x - text_w / 2

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
                requested_percent = label.get(
                    "flag_width_percent_of_destination_zone",
                    label_style.get("flag_width_percent_of_destination_zone", 14)
                )
                flag_w = max(
                    52 if orientation == "portrait" else 58,
                    int(w * requested_percent / 100)
                )
                flag_w = min(flag_w, int(w * (0.28 if orientation == "portrait" else 0.24)))
                flag_h = int(flag_w * 0.62)
                flag_anchor = label.get("flag_anchor", "label")

                if flag_anchor == "landmark_roof":
                    pole_bottom = landmark_anchor_y + 2
                    pole_top = max(
                        label_y + text_h + 30,
                        pole_bottom - max(
                            int(105 * vertical_scale),
                            int(flag_h * 1.9)
                        )
                    )

                    draw.line(
                        (
                            landmark_anchor_x,
                            pole_bottom,
                            landmark_anchor_x,
                            pole_top
                        ),
                        fill=(222, 181, 83),
                        width=4
                    )
                    draw.ellipse(
                        (
                            landmark_anchor_x - 5,
                            pole_bottom - 4,
                            landmark_anchor_x + 5,
                            pole_bottom + 5
                        ),
                        fill=(222, 181, 83),
                        outline=(86, 65, 38)
                    )
                    flag_x1 = landmark_anchor_x + 3
                    flag_y1 = pole_top + 5

                elif flag_anchor == "beside_label":
                    pole_top = label_y + 8
                    pole_bottom = pole_top + 58
                    pole_x = int(text_x + text_w + 18)
                    draw.line(
                        (pole_x, pole_top, pole_x, pole_bottom),
                        fill=(222, 181, 83),
                        width=3
                    )
                    flag_x1 = pole_x + 2
                    flag_y1 = pole_top + 4

                else:
                    pole_top = label_y + text_h + 12
                    pole_bottom = pole_top + 52
                    draw.line(
                        (centre_x, pole_top, centre_x, pole_bottom),
                        fill=(222, 181, 83),
                        width=3
                    )
                    flag_x1 = centre_x + 2
                    flag_y1 = pole_top + 4

                draw_country_flag(
                    draw,
                    label["country_name"],
                    (
                        flag_x1,
                        flag_y1,
                        flag_x1 + flag_w,
                        flag_y1 + flag_h
                    )
                )

        else:
            card_y = 36 if orientation == "landscape" else 52
            card_height = 110 if orientation == "landscape" else 132
            label_right = min(width - 12, x + w - 12)
            draw.rounded_rectangle(
                (x + 12, card_y, label_right, card_y + card_height),
                radius=16,
                fill=(255, 250, 237),
                outline=(63, 49, 36),
                width=3
            )

            display_text = item["display_name"]
            if orientation == "portrait" and len(display_text) > 22:
                display_text = display_text[:20] + "…"

            draw.text(
                (x + 24, card_y + 14),
                display_text,
                fill=(48, 38, 28),
                font=guide_title_font
            )

            landmark = item["main_landmark"]
            max_chars = 30 if orientation == "portrait" else 48
            if len(landmark) > max_chars:
                landmark = landmark[:max_chars - 3] + "..."
            draw.text(
                (x + 24, card_y + 68),
                landmark,
                fill=(83, 65, 47),
                font=guide_body_font
            )

        draw.text(
            (x + 16, height - 42),
            item["position"].upper(),
            fill=(35, 35, 35),
            font=small_font
        )

    draw.line((0, horizon_y, width, horizon_y), fill=(255, 255, 255), width=5)
    draw.text(
        (18, horizon_y + 14),
        "ONE CONTINUOUS HORIZON",
        fill=(255, 255, 255),
        font=guide_body_font
    )
    draw.text(
        (18, int(height * 0.18)),
        (
            "TALL PORTRAIT DEPTH + UPPER-LEFT SUNLIGHT"
            if orientation == "portrait"
            else "OPEN SKY + UPPER-LEFT SUNLIGHT"
        ),
        fill=(255, 255, 255),
        font=guide_body_font
    )

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


st.title("🎨 Place Blender 2.0 — Multi-Style Recipe Builder")
st.write(
    "Choose one to four destinations, an art style, a blend method and an accuracy level. "
    "The app builds a JSON recipe, layout guide and a stronger ready-to-use image prompt."
)

with st.expander("How to use it"):
    st.markdown(
        """
1. Upload your approved reference artwork.
2. Enter the destinations.
3. Check or edit the automatic landmark details.
4. Choose **Landscape 3:2** or **Portrait 2:3**, then press **Build recipe and guide**.
5. Download the JSON and layout PNG.
6. Upload the approved reference, layout PNG and generated prompt to ChatGPT.
        """
    )

st.subheader("Artwork format")

format_name = st.radio(
    "Choose the finished artwork orientation",
    ["Landscape 3:2", "Portrait 2:3"],
    horizontal=True,
    help=(
        "Landscape creates a 1536 × 1024 panoramic guide. "
        "Portrait creates a 1024 × 1536 tall travel-poster guide."
    )
)

canvas_settings = deepcopy(CANVAS_PRESETS[format_name])

st.subheader("Art style and blend")
style_name = st.selectbox(
    "Artwork style",
    list(ART_STYLE_PRESETS.keys()),
    help="Choose the finished visual style. The app automatically recommends the best matching blend."
)

recommended_blends = ART_STYLE_PRESETS[style_name]["recommended_blends"]
default_blend = DEFAULT_BLEND_BY_STYLE[style_name]
all_blends = list(BLEND_MODE_PRESETS.keys())
blend_options = recommended_blends + [name for name in all_blends if name not in recommended_blends]
blend_mode = st.selectbox(
    "How should the places be blended?",
    blend_options,
    index=blend_options.index(default_blend),
    help="Recommended blends appear first. You can still choose any method."
)

if blend_mode in recommended_blends:
    st.caption(f"Recommended match for {style_name}: {blend_mode}")
else:
    st.warning(f"{blend_mode} can be used, but {', '.join(recommended_blends)} usually gives a better result for {style_name}.")

accuracy_mode = st.radio(
    "Place accuracy",
    ["Exact Landmark", "Balanced", "Artistic"],
    index=1,
    horizontal=True,
    help="Exact Landmark follows real features most closely. Balanced is the recommended default."
)

with st.expander("Optional title and personalisation"):
    title_text = st.text_input("Main title", placeholder="Example: Our Special Places")
    subtitle_text = st.text_input("Subtitle", placeholder="Example: Melbourne • Santorini • Amalfi")

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

    flag_attachment_choice = st.selectbox(
        "Where should each country flagpole be attached?",
        [
            "Mounted on top of the matching main landmark or building",
            "Hanging beneath the destination label",
            "Beside the destination label"
        ],
        index=0,
        help=(
            "The first option tells ChatGPT that the lower end of the pole must "
            "physically touch the landmark roof, dome or tower."
        )
    )

    if flag_attachment_choice.startswith("Mounted"):
        flag_anchor = "landmark_roof"
        flag_placement = (
            "mounted on the highest suitable roof, dome, tower or architectural "
            "point of the matching main landmark"
        )
        flag_attachment_rule = (
            "the flagpole base must visibly touch and be fixed to the landmark; "
            "never float the pole in the sky and never attach it to the label"
        )
    elif flag_attachment_choice.startswith("Beside"):
        flag_anchor = "beside_label"
        flag_placement = (
            "immediately to the right of the destination label on a short warm-gold pole"
        )
        flag_attachment_rule = (
            "keep the flag beside the label without covering the landmark"
        )
    else:
        flag_anchor = "label"
        flag_placement = (
            "directly beneath the destination label on a thin vertical warm-gold flagpole"
        )
        flag_attachment_rule = (
            "keep the flag aligned beneath the destination wording"
        )

    flag_scale = st.selectbox(
        "Flag size",
        [
            "large and clearly visible",
            "extra large and prominent",
            "medium",
            "small and refined"
        ],
        index=0,
        help=(
            "Large is recommended. Extra large makes each flag a strong visual feature "
            "while keeping it attached to the matching landmark."
        )
    )

    flag_width_percent = {
        "extra large and prominent": 18,
        "large and clearly visible": 14,
        "medium": 10,
        "small and refined": 7
    }[flag_scale]

    uppercase_labels = st.checkbox(
        "Use uppercase destination names",
        value=True
    )
else:
    include_country_flags = False
    label_colour = "warm cream-gold"
    label_placement = "centred in the open sky directly above its matching main landmark"
    flag_anchor = "landmark_roof"
    flag_placement = (
        "mounted on the highest suitable roof, dome, tower or architectural "
        "point of the matching main landmark"
    )
    flag_attachment_rule = (
        "the flagpole base must visibly touch and be fixed to the landmark; "
        "never float the pole in the sky and never attach it to the label"
    )
    flag_scale = "large and clearly visible"
    flag_width_percent = 14
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
    "flag_anchor": flag_anchor,
    "flag_placement": flag_placement,
    "flag_attachment_rule": flag_attachment_rule,
    "flag_scale": flag_scale,
    "flag_width_percent_of_destination_zone": flag_width_percent,
    "flag_accuracy": (
        "use the correct national flag colours, layout and proportions for each destination country"
    )
}

horizon_y = st.slider(
    "Horizon height",
    canvas_settings["horizon_min"],
    canvas_settings["horizon_max"],
    canvas_settings["default_horizon_y"],
    key=f"horizon_{canvas_settings['orientation']}",
    help=(
        "Lower values create more foreground. Higher values create more open sky. "
        "The portrait range is adjusted automatically."
    )
)

if st.button("Build artwork recipe and prompt", type="primary", use_container_width=True):
    if not edited:
        st.error("Enter at least one destination.")
    elif include_labels and include_country_flags and any(
        not item.get("country_name", "").strip() for item in edited
    ):
        st.error(
            "Add a country name for every destination so the recipe can attach the correct flag."
        )
    else:
        art_settings = {
            "style": style_name,
            "blend_mode": blend_mode,
            "accuracy_mode": accuracy_mode,
            "title_text": title_text,
            "subtitle_text": subtitle_text,
        }
        recipe = make_recipe(edited, horizon_y, label_settings, canvas_settings, art_settings)
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
        f"place_blend_{recipe['style_preset']['canvas']['orientation']}_layout_guide.png",
        "image/png",
        use_container_width=True
    )

    st.subheader("JSON recipe")
    recipe_text = json.dumps(recipe, indent=2, ensure_ascii=False)
    st.code(recipe_text, language="json")

    st.download_button(
        "Download JSON recipe",
        recipe_text.encode("utf-8"),
        f"place_blend_{recipe['style_preset']['canvas']['orientation']}_recipe.json",
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
        f"place_blend_{recipe['style_preset']['canvas']['orientation']}_prompt.txt",
        "text/plain",
        use_container_width=True
    )

    if recipe.get("destination_label_style", {}).get("enabled"):
        st.success(
            "The recipe includes the destination names, correct country flags, roof attachment and the selected larger flag size."
        )

    st.info(
        "Upload the approved reference image, the layout guide PNG and this prompt together."
    )
