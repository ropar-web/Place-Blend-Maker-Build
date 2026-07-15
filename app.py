
import io
import json
import hashlib
import re
from copy import deepcopy

import streamlit as st
from PIL import Image, ImageDraw, ImageFont


st.set_page_config(
    page_title="Place Blend Recipe Builder 2.9",
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



A1_PRODUCTION_PRESETS = {
    "A1 Portrait": {
        "print_standard": "A1",
        "orientation": "portrait",
        "physical_size_mm": {"width": 594, "height": 841},
        "target_dpi": 300,
        "target_pixel_dimensions": {"width": 7016, "height": 9933},
        "minimum_acceptable_dpi": 240,
        "minimum_pixel_dimensions": {"width": 5613, "height": 7946},
    },
    "A1 Landscape": {
        "print_standard": "A1",
        "orientation": "landscape",
        "physical_size_mm": {"width": 841, "height": 594},
        "target_dpi": 300,
        "target_pixel_dimensions": {"width": 9933, "height": 7016},
        "minimum_acceptable_dpi": 240,
        "minimum_pixel_dimensions": {"width": 7946, "height": 5613},
    },
}

def build_production_output(print_preset_name, bleed_mm, safe_margin_mm):
    preset = deepcopy(A1_PRODUCTION_PRESETS[print_preset_name])
    preset.update({
        "colour_mode": "RGB",
        "export_format": "PNG or print-ready PDF",
        "bleed_mm": bleed_mm,
        "print_safe_margin_mm": safe_margin_mm,
        "resampling_rule": "Generate at the highest available native resolution, then upscale with a genuine high-quality image upscaler. Do not only change DPI metadata.",
        "aspect_ratio_rule": "Preserve the exact A1 aspect ratio. Do not stretch, squash or distort the artwork or landmark.",
        "quality_rules": [
            "preserve crisp landmark edges",
            "preserve fine architectural details without inventing new features",
            "avoid blurry enlarged textures",
            "avoid pixelation and compression artefacts",
            "avoid invented detail during upscaling",
            "keep typography sharp and correctly spelled",
            "retain the entire artwork canvas without cropping",
            "keep important objects inside the safe margin"
        ],
        "final_validation": {
            "confirm_actual_pixel_dimensions": True,
            "confirm_target_dpi_at_A1": True,
            "confirm_no_stretching": True,
            "confirm_no_blurry_edges_at_100_percent_zoom": True,
            "confirm_dpi_is_not_metadata_only": True
        }
    })
    return preset

ART_STYLE_PRESETS = {
    "Premium Travel Poster": {
        "prompt": "Use a premium illustrated travel-poster style with polished composition, refined painterly detail, crisp recognisable architecture, rich but controlled colour, and a cohesive gift-worthy finish.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset"],
    },
    "Vintage Retro Poster": {
        "prompt": "Use a vintage retro travel-poster style with bold simplified shapes, classic tourism-poster composition, clean sky areas, strong silhouettes, limited harmonious colours, subtle print texture, and nostalgic mid-century charm.",
        "recommended_blends": ["Side by Side", "Smooth Blend", "Poster Grid"],
    },
    "Bold Colour Retro Travel Poster": {
        "prompt": "Use a bold modern retro travel-poster print style inspired by highly saturated illustrated destination posters: crisp hard-edged colour shapes, simplified but recognisable architecture, strong graphic depth, vivid turquoise, teal, green, yellow, pink and deep navy, a dominant landmark, optional decorative foreground foliage, and a clean white poster margin with destination typography beneath the artwork.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Poster Grid"],
    },
    "Soft Watercolour": {
        "prompt": "Use a soft hand-painted watercolour style with delicate washes, natural paper texture, gentle edges, elegant architectural detail, luminous atmosphere, and graceful painterly transitions.",
        "recommended_blends": ["Smooth Blend", "Layered Scene", "Main Place + Memory Inset"],
    },
    "Ink Sketch + Wash": {
        "prompt": "Use an architectural ink-sketch and watercolour-wash style with expressive hand-drawn linework, accurate building proportions, loose transparent colour, and a personal urban-sketchbook character.",
        "recommended_blends": ["Main Place + Memory Inset", "Side by Side", "Layered Scene"],
    },
    "Clean Line Art": {
        "prompt": "Use clean architectural line art with accurate landmark contours, deliberate line hierarchy, generous negative space and optional restrained spot colour. Keep the place recognisable without painterly fills.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset", "Poster Grid"],
    },
    "Loose Hand-Drawn Sketch": {
        "prompt": "Use a loose hand-drawn pen or pencil sketch style with naturally imperfect expressive strokes, observational landmark proportions, selective hatching and visible paper.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset"],
    },
    "Hand-Drawn Cartoon": {
        "prompt": "Use a polished hand-drawn cartoon travel illustration with simplified but recognisable landmarks, friendly shapes, clear outlines, cheerful colour and coherent scenic depth. Avoid childish clipart.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Poster Grid"],
    },
    "Watercolour Cartoon": {
        "prompt": "Use friendly hand-drawn outlines combined with genuine transparent watercolour washes, visible paper texture, soft pigment variation and recognisable simplified landmarks.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset", "Poster Grid"],
    },
    "Children's Storybook Illustration": {
        "prompt": "Use a warm whimsical children's storybook illustration style with rounded hand-drawn forms, gentle painted texture, inviting scenery and recognisable destination features. Keep it premium and not babyish.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset", "Poster Grid"],
    },
    "Vintage Illustrated Cartoon Poster": {
        "prompt": "Use a hand-illustrated vintage cartoon travel-poster style with simplified landmarks, confident drawn outlines, limited retro colours, subtle print texture and nostalgic destination-poster composition.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Poster Grid"],
    },
    "Coloured Pencil Illustration": {
        "prompt": "Use a detailed coloured-pencil travel illustration with visible pencil grain, layered strokes, softly shaded architecture, textured foliage and accurate landmark identity on warm paper.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset", "Poster Grid"],
    },
    "Minimal Continuous-Line Art": {
        "prompt": "Use elegant minimal continuous-line landmark art with a highly reduced flowing contour, abundant negative space and optional tiny restrained accent colour. Preserve the essential landmark silhouette.",
        "recommended_blends": ["Side by Side", "Main Place + Memory Inset", "Poster Grid"],
    },
    "3D Family Animation": {
        "prompt": "Use a premium cinematic 3D family-animation look with appealing rounded forms, expressive but tasteful proportions, richly modelled landmarks, soft tactile materials, warm storytelling light and polished feature-animation depth. Keep it original and do not copy branded characters.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset", "Poster Grid"],
    },
    "Classic Fairytale Animation": {
        "prompt": "Use an original classic fairytale animation look with graceful hand-drawn forms, expressive silhouettes, elegant colour design, luminous painted backgrounds, gentle storybook charm and recognisable destination details. Keep it original and do not copy branded characters.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Layered Scene", "Main Place + Memory Inset", "Poster Grid"],
    },
    "Bold Pop Mosaic": {
        "prompt": "Use an original bold pop mosaic illustration style with joyful segmented colour blocks, strong dark outlines, playful decorative patterns, highly saturated colour, and simplified but recognisable landmarks. Keep it original and avoid copying any specific artist exactly.",
        "recommended_blends": ["Smooth Blend", "Side by Side", "Poster Grid", "Map Connection"],
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
    "Bold Colour Retro Travel Poster": {
        "finish": "Contemporary bold-colour retro destination-poster finish with crisp hard-edged illustrated shapes, simplified but accurate landmarks, strong layered graphic depth, clean contours and polished screen-print-like clarity.",
        "palette": "Highly saturated but coordinated turquoise, cyan, teal, leaf green, lime, sunshine yellow, coral pink, magenta and deep navy, with a clean white print margin. Avoid muddy muted vintage colours.",
        "lighting": "Bright graphic daylight with simplified high-contrast shadow shapes and luminous blue sky; no realistic photographic lighting.",
        "exclude": "Do not use watercolour washes, loose ink sketch lines, painterly brush texture, beige muted vintage grading, photorealism, 3D rendering, childish clipart, map silhouettes or mixed illustration styles."
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
    "Clean Line Art": {
        "finish": "Precise hand-drawn architectural line art with controlled contour weight, clear silhouettes, selective interior detail and generous white space.",
        "palette": "Black, sepia or selected coloured linework on white or warm paper, with optional restrained spot colour only.",
        "lighting": "Suggested sparingly through line weight, hatching or minimal shadow shapes.",
        "exclude": "full painterly fills, watercolour blooms unless spot wash is selected, flat cartoon blocks, glossy 3D rendering, photorealism, dense poster texture, mixed styles"
    },
    "Loose Hand-Drawn Sketch": {
        "finish": "Expressive observational pen or pencil sketch with imperfect natural strokes, varied line pressure, selective hatching, construction marks and visible paper.",
        "palette": "Graphite, charcoal, black ink or sepia with optional light accent wash.",
        "lighting": "Loose hatching and sparse hand-rendered shadow indications.",
        "exclude": "perfect vector contours, flat poster fills, glossy digital rendering, heavy opaque paint, 3D models, childish clipart, mixed styles"
    },
    "Hand-Drawn Cartoon": {
        "finish": "Premium hand-drawn cartoon destination illustration with clean expressive outlines, simplified accurate landmarks, friendly proportions and polished colour fills.",
        "palette": "Cheerful coordinated destination colours with clear contrast and controlled saturation.",
        "lighting": "Simple readable cartoon daylight with soft cel-like or hand-painted shadows.",
        "exclude": "generic clipart, extreme caricature, anime styling, glossy 3D toys, photorealism, loose watercolour bleeding, mixed styles"
    },
    "Watercolour Cartoon": {
        "finish": "Hand-drawn cartoon linework painted with genuine transparent watercolour washes, paper grain, pigment variation, soft edges and selective dry-brush detail.",
        "palette": "Luminous friendly transparent pigments with destination-appropriate colours.",
        "lighting": "Soft cheerful daylight expressed through layered translucent washes.",
        "exclude": "flat vector fills, screen-print hard edges, glossy 3D rendering, photorealism, heavy oil paint, generic clipart, mixed styles"
    },
    "Children's Storybook Illustration": {
        "finish": "Warm premium storybook illustration with rounded hand-drawn forms, gentle gouache or watercolour-like painted texture, layered scenery and inviting narrative detail.",
        "palette": "Warm harmonious storybook colours with soft greens, sky blues, creams, ochres and restrained bright accents.",
        "lighting": "Gentle magical daylight with soft painted shadows and atmospheric depth.",
        "exclude": "cheap clipart, glossy 3D toys, harsh vector geometry, photorealism, frightening mood, excessive visual clutter, mixed styles"
    },
    "Vintage Illustrated Cartoon Poster": {
        "finish": "Hand-illustrated vintage cartoon travel poster with confident outlines, simplified landmark forms, limited flat-to-painted colour, subtle halftone or aged print texture.",
        "palette": "Limited retro teal, cream, mustard, coral, brick red and deep navy with destination-appropriate variation.",
        "lighting": "Graphic vintage poster daylight with simplified shadow shapes.",
        "exclude": "modern neon gradients, photorealism, glossy 3D rendering, soft full watercolour bleeding, generic clipart, mixed styles"
    },
    "Coloured Pencil Illustration": {
        "finish": "Layered coloured-pencil illustration with visible directional strokes, pencil grain, softly blended shading, crisp key contours and detailed architecture on textured paper.",
        "palette": "Rich layered pencil colours with natural paper showing through and controlled saturation.",
        "lighting": "Soft natural light built from layered pencil shading and highlights.",
        "exclude": "flat vector colour, wet watercolour blooms, heavy oil paint, glossy 3D rendering, photorealism, childish clipart, mixed styles"
    },
    "Minimal Continuous-Line Art": {
        "finish": "Elegant highly reduced continuous-line landmark drawing using one flowing contour or a very small number of connected strokes with abundant negative space.",
        "palette": "Single black, charcoal, sepia or selected accent line on white or warm neutral paper.",
        "lighting": "No rendered lighting; form is communicated through contour alone.",
        "exclude": "dense internal detail, filled scenic backgrounds, painterly texture, realistic shading, cartoon colour blocks, 3D rendering, mixed styles"
    },
    "3D Family Animation": {
        "finish": "Premium original 3D family-animation destination illustration with rounded appealing forms, carefully modelled architecture, soft tactile surfaces, expressive scenic staging and polished cinematic depth.",
        "palette": "Rich coordinated feature-animation colour with warm highlights, clear focal contrast, luminous skies and destination-appropriate accents; avoid neon overload.",
        "lighting": "Soft cinematic daylight with warm key light, gentle bounce light, readable volumetric depth and polished but natural shadows.",
        "exclude": "Do not copy branded characters, studio-specific character designs, logos or copyrighted costumes. Do not use flat vector art, loose watercolour, rough sketch lines, photorealism, toy-plastic gloss or mixed rendering styles."
    },
    "Classic Fairytale Animation": {
        "finish": "Original classic fairytale animation destination illustration with elegant hand-drawn contours, expressive simplified forms, luminous painted backgrounds and refined storybook staging.",
        "palette": "Harmonious fairytale colour design with warm creams, jewel-like destination accents, atmospheric blues and gentle painted gradients.",
        "lighting": "Luminous storybook daylight or golden-hour illumination with soft painted shadows and graceful atmospheric depth.",
        "exclude": "Do not copy branded characters, studio-specific princesses, mascots, costumes, logos or exact film designs. Do not use glossy 3D rendering, flat clipart, photorealism, harsh vector geometry or mixed illustration styles."
    },
    "Bold Pop Mosaic": {
        "finish": "Original bold pop mosaic destination illustration with simplified landmark silhouettes, strong dark outlines, segmented colour areas, decorative pattern accents and a cheerful premium gift-art finish.",
        "palette": "Highly saturated celebratory colour with vivid pink, turquoise, cobalt, lime, yellow, orange, purple and red balanced cleanly across the composition.",
        "lighting": "Graphic pop-art lighting with simplified readable contrast rather than realistic modelling.",
        "exclude": "Do not copy any specific copyrighted artwork exactly. Do not use photorealism, loose watercolour, rough sketch rendering, muted vintage grading, glossy 3D modelling or mixed illustration styles."
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
    "Bold Colour Retro Travel Poster": "Smooth Blend",
    "Soft Watercolour": "Smooth Blend",
    "Ink Sketch + Wash": "Main Place + Memory Inset",
    "Clean Line Art": "Side by Side",
    "Loose Hand-Drawn Sketch": "Main Place + Memory Inset",
    "Hand-Drawn Cartoon": "Smooth Blend",
    "Watercolour Cartoon": "Smooth Blend",
    "Children's Storybook Illustration": "Smooth Blend",
    "Vintage Illustrated Cartoon Poster": "Side by Side",
    "Coloured Pencil Illustration": "Smooth Blend",
    "Minimal Continuous-Line Art": "Side by Side",
    "3D Family Animation": "Smooth Blend",
    "Classic Fairytale Animation": "Smooth Blend",
    "Bold Pop Mosaic": "Smooth Blend",
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
    render = deepcopy(STYLE_RENDER_RULES[style_name])

    drawn_styles = {
        "Clean Line Art", "Loose Hand-Drawn Sketch", "Hand-Drawn Cartoon",
        "Watercolour Cartoon", "Children's Storybook Illustration",
        "Vintage Illustrated Cartoon Poster", "Coloured Pencil Illustration",
        "Minimal Continuous-Line Art"
    }
    if style_name in drawn_styles:
        detail = art_settings.get("detail_level", "Balanced")
        background = art_settings.get("background_treatment", "Warm paper")
        line_colour = art_settings.get("line_colour", "Warm charcoal")
        colour = art_settings.get("accent_colour", "Restrained palette")
        shading = art_settings.get("shading_style", "Light hatching")
        outline = art_settings.get("outline_strength", "Balanced")
        realism = art_settings.get("realism_level", "Gently simplified")
        texture = art_settings.get("paper_texture", "Light paper grain")
        framing = art_settings.get("decorative_framing", "None")
        render["finish"] += f" Detail level: {detail}. Outline strength: {outline}. Landmark treatment: {realism}. Shading: {shading}. Paper treatment: {texture}."
        render["palette"] += f" Use {line_colour} linework and {colour.lower()}. Background treatment: {background}. Decorative framing: {framing}."

    # The bold retro family supports distinct, locked visual finishes plus
    # user-controlled detail, edge, texture, colour, typography and framing.
    if style_name in ["3D Family Animation", "Classic Fairytale Animation"]:
        st.subheader("4. Animation-style options")
        animation_mood = st.selectbox("Overall mood", ["Warm and joyful", "Magical and dreamy", "Adventurous", "Elegant and calm", "Playful"], index=0, key="animation_mood")
        character_presence = st.selectbox("People or characters", ["No characters", "Tiny background figures only", "One original family-friendly guide character", "Small original character group"], index=1, key="animation_characters")
        cinematic_depth = st.selectbox("Scene depth", ["Simple poster depth", "Balanced cinematic depth", "Rich cinematic depth"], index=1, key="animation_depth")
        material_finish = st.selectbox("Surface finish", ["Soft matte", "Painterly", "Polished but not glossy", "Storybook textured"], index=0, key="animation_material")
        facial_expression = st.selectbox("Character expression", ["Natural and subtle", "Friendly and expressive", "Highly animated"], index=1, key="animation_expression", disabled=character_presence == "No characters")
        extra_art_settings.update({
            "animation_mood": animation_mood,
            "character_presence": character_presence,
            "cinematic_depth": cinematic_depth,
            "material_finish": material_finish,
            "facial_expression": facial_expression,
        })

    if style_name == "Bold Pop Mosaic":
        st.subheader("3. Bold pop mosaic options")
        pattern_strength = st.selectbox("Pattern strength", ["Light", "Balanced", "Bold"], index=1, key="pop_pattern_strength")
        outline_strength = st.selectbox("Outline strength", ["Medium", "Strong", "Extra bold"], index=1, key="pop_outline_strength")
        colour_intensity = st.selectbox("Colour intensity", ["Bright", "Bold", "Ultra vibrant"], index=1, key="pop_colour_intensity")
        pattern_mix = st.multiselect("Pattern types", ["Dots", "Stripes", "Hearts", "Swirls", "Checks"], default=["Dots", "Stripes", "Swirls"], key="pop_pattern_mix")
        landmark_simplification = st.selectbox("Landmark simplification", ["Gentle", "Balanced", "Strong"], index=1, key="pop_simplification")
        background_style = st.selectbox("Background style", ["Clean white", "Light colour", "Decorative pattern background"], index=0, key="pop_background_style")
        extra_art_settings.update({
            "pattern_strength": pattern_strength,
            "outline_strength": outline_strength,
            "colour_intensity": colour_intensity,
            "pattern_mix": pattern_mix,
            "landmark_simplification": landmark_simplification,
            "background_style": background_style,
        })

    if style_name == "Bold Colour Retro Travel Poster":
        poster_finish = art_settings.get("poster_finish", "Graphic Retro")
        detail_level = art_settings.get("detail_level", "Balanced")
        edge_style = art_settings.get("edge_style", "Balanced")
        texture_strength = art_settings.get("texture_strength", "Light texture")
        colour_mood = art_settings.get("colour_mood", "Bold")

        finish_profiles = {
            "Graphic Retro": {
                "finish": "Bold modern retro travel-poster illustration built from simplified, crisp, flat colour shapes with clean contours, strong graphic depth and highly recognisable landmark silhouettes.",
                "lighting": "Bright graphic daylight with simplified hard-edged shadow shapes and a clean luminous sky.",
                "exclude": "watercolour bleeding, pigment blooms, loose brushwork, paper-grain dominance, sketch lines, photorealism, glossy 3D rendering, childish clipart, mixed illustration styles",
            },
            "Painted Retro": {
                "finish": "Bold retro travel-poster illustration with clean graphic structure, softened hand-painted edges, restrained brush variation and simplified but recognisable architecture.",
                "lighting": "Bright poster daylight with clean shadows softened by subtle painted tonal transitions.",
                "exclude": "flat vector sterility, heavy watercolour blooming, loose ink sketching, photorealism, glossy 3D rendering, childish clipart, mixed illustration styles",
            },
            "Watercolour Retro": {
                "finish": "A genuine hand-painted watercolour destination painting arranged in a bold retro travel-poster layout, using layered transparent washes, visible cold-pressed paper grain, wet-on-wet passages, pigment blooms, soft colour bleeding, dry-brush accents and naturally uneven painted edges while keeping the landmark recognisable.",
                "lighting": "Bright daylight painted through translucent washes, softly diffused shadows, reserved paper highlights and watery sky transitions.",
                "exclude": "flat vector fills, screen-print hard edges, rigid geometric colour blocks, ultra-crisp digital contours, glossy poster rendering, heavy opaque oil paint, photorealism, 3D rendering, childish clipart, mixed illustration styles",
            },
            "Soft Poster Wash": {
                "finish": "A light airy retro poster rendered with soft transparent watercolour washes, broad simplified forms, gentle pigment transitions, generous white paper and minimal fine detail.",
                "lighting": "Soft luminous daylight with pale layered washes and delicate preserved highlights.",
                "exclude": "heavy saturation, dense dark detail, hard vector outlines, screen-print blocks, photorealism, 3D rendering, oily impasto, mixed illustration styles",
            },
            "Detailed Illustrated Retro": {
                "finish": "A richly detailed illustrated retro travel poster with accurate landmark structure, layered architectural detail, clean graphic colour organisation and refined hand-rendered texture.",
                "lighting": "Bright cinematic poster daylight with coherent layered shadows and polished illustrated depth.",
                "exclude": "oversimplified clipart, loose uncontrolled watercolour, flat vector sterility, photorealism, glossy 3D rendering, mixed illustration styles",
            },
        }
        profile = finish_profiles.get(poster_finish, finish_profiles["Graphic Retro"])
        render["finish"] = profile["finish"]
        render["lighting"] = profile["lighting"]
        render["exclude"] = profile["exclude"]

        detail_text = {
            "Simple": "Use broad simplified shapes, minimal small objects and a clear uncluttered landmark silhouette.",
            "Balanced": "Use enough architectural and scenic detail for strong recognisability without making the poster busy.",
            "Detailed": "Preserve richer façade, transport, streetscape and landscape detail while keeping the overall poster hierarchy clean.",
        }.get(detail_level, "Use balanced recognisable detail.")
        edge_text = {
            "Crisp": "Keep edges clean, controlled and clearly separated.",
            "Balanced": "Use mostly controlled edges with selective softening in sky, foliage and distant scenery.",
            "Soft painted": "Use softened hand-painted edges and natural irregularity while preserving the landmark silhouette.",
        }.get(edge_style, "Use balanced controlled edges.")
        texture_text = {
            "Clean / smooth": "Keep surface texture minimal and polished.",
            "Light texture": "Add subtle handmade print or paper texture without obscuring forms.",
            "Painterly texture": "Show visible brush variation and hand-rendered surface character.",
            "Strong watercolour texture": "Show pronounced paper grain, pigment granulation, blooms and layered transparent washes.",
        }.get(texture_strength, "Add light texture.")
        colour_text = {
            "Soft": "Use a softened harmonious palette with reduced contrast.",
            "Balanced": "Use coordinated colour with strong focal contrast but controlled saturation.",
            "Bold": "Use saturated turquoise, teal, green, yellow, coral, pink and deep navy with strong contrast.",
            "Vibrant": "Use highly vivid luminous colour with energetic contrast while avoiding neon imbalance.",
            "Sun-faded vintage": "Use slightly faded sun-worn retro colour while keeping the scene lively and readable.",
        }.get(colour_mood, "Use bold coordinated colour.")
        render["finish"] += f" {detail_text} {edge_text} {texture_text}"
        render["palette"] = f"{colour_text} Maintain a coordinated destination-appropriate palette and clean poster hierarchy."

    if style_name == "Bold Pop Mosaic":
        pattern_strength = art_settings.get("pattern_strength", "Balanced")
        outline_strength = art_settings.get("outline_strength", "Strong")
        colour_intensity = art_settings.get("colour_intensity", "Bold")
        pattern_mix = art_settings.get("pattern_mix", ["Dots", "Stripes", "Swirls"])
        landmark_simplification = art_settings.get("landmark_simplification", "Balanced")
        background_style = art_settings.get("background_style", "Clean white")

        pattern_text = {
            "Light": "Use decorative pattern accents sparingly so the landmark remains dominant.",
            "Balanced": "Use a balanced mix of patterned segments across the artwork.",
            "Bold": "Use abundant decorative patterned segments to create a lively mosaic effect.",
        }.get(pattern_strength, "Use a balanced pattern presence.")
        outline_text = {
            "Medium": "Use clear confident dark outlines.",
            "Strong": "Use bold dark outlines that cleanly separate colour regions.",
            "Extra bold": "Use very bold dark outlines for a striking pop-art effect.",
        }.get(outline_strength, "Use bold outlines.")
        colour_text = {
            "Bright": "Use bright cheerful saturated colour.",
            "Bold": "Use bold saturated colour with strong contrast.",
            "Ultra vibrant": "Use ultra-vibrant celebratory colour while keeping the palette balanced.",
        }.get(colour_intensity, "Use bold saturated colour.")
        simplification_text = {
            "Gentle": "Keep landmark details fairly readable while stylising the colour blocks.",
            "Balanced": "Simplify landmark forms into clean recognisable stylised shapes.",
            "Strong": "Strongly simplify landmark forms into big iconic shapes while preserving recognition.",
        }.get(landmark_simplification, "Keep the landmark recognisable.")
        bg_text = {
            "Clean white": "Use a clean white or very light background to let the colourful subject stand out.",
            "Light colour": "Use a light coordinated background colour behind the pop artwork.",
            "Decorative pattern background": "Use a tasteful decorative patterned background that complements the landmark without overpowering it.",
        }.get(background_style, "Use a clean light background.")
        patterns = ", ".join(pattern_mix) if isinstance(pattern_mix, list) and pattern_mix else "dots and stripes"

        render["finish"] = "Original bold pop mosaic illustration with thick dark outlines, segmented colour-block shapes, playful decorative patterning and a joyful premium gift-art feel."
        render["palette"] = f"{colour_text} Use vivid pink, turquoise, cobalt, lime, yellow, orange, purple and red in a well-balanced arrangement."
        render["lighting"] = "Graphic pop-art lighting with simplified readable shadows and bright cheerful clarity."
        render["exclude"] = "Do not copy any existing copyrighted artwork exactly. Do not use photorealism, loose watercolour, rough sketch rendering, muted vintage grading, glossy 3D modelling, or mixed illustration styles."
        render["finish"] += f" {pattern_text} {outline_text} {simplification_text} Feature playful pattern types such as {patterns}. {bg_text}"

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
        "Bold Colour Retro Travel Poster": [
            "one consistent bold-colour retro destination-poster composition",
            "a dominant recognisable landmark with simplified colourful architecture and strong graphic depth",
            "crisp saturated flat colour shapes, optional foreground foliage framing and a clean white poster margin",
            "when labels are enabled, place the large destination name and smaller country subtitle beneath the artwork rather than in the sky",
            "use the selected blend structure exactly"
        ],
        "Clean Line Art": [
            "one coherent architectural line-art composition",
            "accurate landmark contours with clear line hierarchy and generous negative space",
            "use the selected line colour, shading and background treatment exactly",
            "use the selected blend structure exactly"
        ],
        "Loose Hand-Drawn Sketch": [
            "one coherent loose observational sketch composition",
            "expressive imperfect strokes, varied pressure, selective hatching and visible paper",
            "preserve recognisable landmark proportions without polished vector perfection",
            "use the selected blend structure exactly"
        ],
        "Hand-Drawn Cartoon": [
            "one coherent premium hand-drawn cartoon destination scene",
            "friendly simplified landmarks with clear outlines and polished colour",
            "keep recognisability while following the selected cartoon realism and outline strength",
            "use the selected blend structure exactly"
        ],
        "Watercolour Cartoon": [
            "one coherent hand-drawn watercolour-cartoon composition",
            "friendly outlines with transparent washes, paper texture and pigment variation",
            "keep landmarks simplified, warm and recognisable",
            "use the selected blend structure exactly"
        ],
        "Children's Storybook Illustration": [
            "one coherent warm storybook destination scene",
            "rounded hand-drawn forms, gentle painted depth and inviting decorative scenery",
            "keep destination identity clear and premium rather than babyish",
            "use the selected blend structure exactly"
        ],
        "Vintage Illustrated Cartoon Poster": [
            "one coherent vintage illustrated cartoon-poster composition",
            "simplified recognisable landmarks, confident outlines and limited retro colour",
            "subtle aged print character without modern glossy effects",
            "use the selected blend structure exactly"
        ],
        "Coloured Pencil Illustration": [
            "one coherent coloured-pencil destination illustration",
            "visible layered pencil strokes, softly shaded architecture and textured foliage",
            "retain paper grain and accurate landmark identity",
            "use the selected blend structure exactly"
        ],
        "3D Family Animation": [
            "one coherent premium 3D family-animation destination scene",
            "rounded appealing forms, modelled landmark depth, tactile materials and cinematic staging",
            "keep the destination recognisable and the visual language original rather than copying branded characters",
            "use the selected blend structure exactly"
        ],
        "Classic Fairytale Animation": [
            "one coherent original classic fairytale-animation destination scene",
            "graceful hand-drawn forms, luminous painted backgrounds and elegant storybook staging",
            "keep destination identity clear without copying branded characters or film-specific designs",
            "use the selected blend structure exactly"
        ],
        "Bold Pop Mosaic": [
            "one coherent original bold pop mosaic destination artwork",
            "simplified recognisable landmark shapes, strong outlines, segmented colour blocks and playful decorative patterns",
            "keep the mood joyful, giftable and original rather than copying any specific artist exactly",
            "use the selected blend structure exactly"
        ],
        "Minimal Continuous-Line Art": [
            "one elegant minimal continuous-line composition",
            "reduce each landmark to its essential flowing contour with abundant negative space",
            "use no filled scenic background unless a tiny accent is explicitly selected",
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
    if style_name == "Bold Colour Retro Travel Poster":
        poster_finish = art_settings.get("poster_finish", "Graphic Retro")
        finish_line = {
            "Graphic Retro": "render with crisp simplified graphic colour shapes and strong poster clarity",
            "Painted Retro": "use clean graphic shapes softened by subtle hand-painted edges and restrained brush texture",
            "Watercolour Retro": "render as genuine hand-painted watercolour with paper grain, wet-on-wet washes, pigment blooms, soft bleeding edges and dry-brush detail",
            "Soft Poster Wash": "use light airy transparent washes, simplified forms, generous white paper and minimal fine detail",
            "Detailed Illustrated Retro": "use richly detailed illustrated architecture, polished graphic organisation and refined hand-rendered texture",
        }.get(poster_finish, "render with crisp simplified graphic colour shapes")
        composition_by_style[style_name] = [
            "one consistent bold-colour retro destination-poster composition",
            "a dominant recognisable landmark with clear graphic hierarchy",
            finish_line,
            f"detail level: {art_settings.get('detail_level', 'Balanced')}",
            f"edge treatment: {art_settings.get('edge_style', 'Balanced')}",
            f"surface texture: {art_settings.get('texture_strength', 'Light texture')}",
            f"colour mood: {art_settings.get('colour_mood', 'Bold')}",
            f"decorative framing: {art_settings.get('foliage_framing', 'Light top foliage framing')}",
            f"poster border treatment: {art_settings.get('border_style', 'Wide white poster margin')}",
            "when labels are enabled, follow the selected typography and title placement exactly",
            "use the selected blend structure exactly"
        ]
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
        "recipe_version": "1.5.0",
        "build_name": "Multi-Style Place Blender 3.0",
        "style_family": "scenic_art",
        "production_output": deepcopy(art_settings.get("production_output", {})),
        "style_preset": {
            "collection_name": f"{style_name} Collection",
            "canvas": canvas,
            "finish": render["finish"],
            "palette": render["palette"],
            "lighting": render["lighting"],
            "composition": composition_by_style.get(style_name, composition_by_style["Premium Travel Poster"]),
            "negative_rules": negative_by_style
        },
        "scene_type": "single_destination_retro_poster_artwork" if len(final_destinations) == 1 and style_name == "Bold Colour Retro Travel Poster" else "combined_destination_scenic_artwork",
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
            "fill_treatment": art_settings.get("map_fill_style", "Colourful painterly splash") + " clipped strictly inside the map silhouette",
            "outline_rule": "preserve the correct geographic outline and islands"
        })
    title = art_settings.get("title_text", "").strip() or "Home to Home"
    subtitle = art_settings.get("subtitle_text", "").strip()
    return {
        "recipe_version": "1.5.0",
        "build_name": "Multi-Style Place Blender 3.0",
        "style_family": "map_art",
        "production_output": deepcopy(art_settings.get("production_output", {})),
        "style_preset": {
            "collection_name": "Home to Home Map Art Collection",
            "canvas": canvas,
            "finish": "clean premium personalised map artwork with accurate silhouettes and controlled painterly fills",
            "palette": "warm neutral paper background with " + art_settings.get("map_palette", "coordinated vibrant paint textures") + " and dark elegant lettering",
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
            "type": art_settings.get("connection_motif", "Fine line with a heart loop"),
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
        "recipe_version": "1.5.0",
        "build_name": "Multi-Style Place Blender 3.0",
        "style_family": "poster_grid",
        "production_output": deepcopy(art_settings.get("production_output", {})),
        "style_preset": {
            "collection_name": "Favourite Places Grid Collection",
            "canvas": canvas,
            "finish": "coordinated set of matching mini travel posters using " + art_settings.get("tile_style", "Vintage Retro Poster") + " consistently across every tile",
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


def make_production_prompt(recipe):
    prod = recipe.get("production_output", {})
    physical = prod.get("physical_size_mm", {})
    target_px = prod.get("target_pixel_dimensions", {})
    minimum_px = prod.get("minimum_pixel_dimensions", {})
    return f"""
A1 PRINT-PRODUCTION REQUIREMENTS:
- Print standard: {prod.get('print_standard', 'A1')} {prod.get('orientation', '')}.
- Final physical size: {physical.get('width', 594)} × {physical.get('height', 841)} mm.
- Target: {prod.get('target_dpi', 300)} DPI using real final dimensions of {target_px.get('width', 7016)} × {target_px.get('height', 9933)} pixels.
- Minimum acceptable fallback: {prod.get('minimum_acceptable_dpi', 240)} DPI at {minimum_px.get('width', 5613)} × {minimum_px.get('height', 7946)} pixels.
- Generate at the highest available native resolution, then use genuine high-quality image upscaling to reach the final pixel dimensions. Never claim print quality by changing DPI metadata alone.
- Preserve the exact A1 aspect ratio; do not stretch, squash or distort the artwork.
- Keep essential landmarks, labels and faces inside a {prod.get('print_safe_margin_mm', 15)} mm safe margin. Allow {prod.get('bleed_mm', 3)} mm bleed when printing edge-to-edge.
- Use clean large forms, controlled texture, sharp silhouettes and readable architectural detail that will enlarge well. Avoid excessive tiny clutter, compression artefacts and invented details during upscaling.
- Before export, verify actual pixel dimensions, A1 dimensions, sharpness at 100% zoom, correct spelling and no cropping.
"""

def make_prompt(recipe):
    family = recipe.get("style_family", "scenic_art")
    if family == "map_art":
        return make_map_prompt(recipe)
    if family == "poster_grid":
        return make_grid_prompt(recipe)
    return make_scenic_prompt(recipe)


def make_scenic_prompt(recipe):
    style = recipe["style_preset"]
    production_prompt = make_production_prompt(recipe)
    label_style = recipe.get("destination_label_style", {})
    labels_enabled = bool(label_style.get("enabled"))
    art_settings = recipe.get("art_settings", {})
    style_name = art_settings.get("style", "Premium Travel Poster")
    blend_name = art_settings.get("blend_mode", "Smooth Blend")
    accuracy_name = art_settings.get("accuracy_mode", "Balanced")
    style_direction = ART_STYLE_PRESETS[style_name]["prompt"]
    render_rules = recipe.get("style_preset") or STYLE_RENDER_RULES[style_name]
    render_finish = render_rules.get("finish", STYLE_RENDER_RULES[style_name].get("finish", ""))
    render_palette = render_rules.get("palette", STYLE_RENDER_RULES[style_name].get("palette", ""))
    render_lighting = render_rules.get("lighting", STYLE_RENDER_RULES[style_name].get("lighting", ""))
    render_exclusions = render_rules.get("exclude", render_rules.get("negative_rules", STYLE_RENDER_RULES[style_name].get("exclude", "")))
    if isinstance(render_exclusions, list):
        render_exclusions = "; ".join(str(item) for item in render_exclusions)
    blend_direction = BLEND_MODE_PRESETS.get(blend_name, BLEND_MODE_PRESETS["Smooth Blend"])
    accuracy_direction = ACCURACY_MODE_PRESETS.get(accuracy_name, ACCURACY_MODE_PRESETS["Balanced"])
    title_text = art_settings.get("title_text", "").strip()
    subtitle_text = art_settings.get("subtitle_text", "").strip()

    destination_lines, approved_labels = [], []
    for item in recipe["destinations"]:
        viewpoint_text = f" Viewpoint: {item['viewpoint']}." if item.get('viewpoint') else ""
        destination_lines.append(
            f"{item['display_name']} on the {item['position']}: feature {item['main_landmark']}. "
            f"Include {joined(item.get('secondary_elements', []))}. Preserve {joined(item.get('important_features', []))}."
            f"{viewpoint_text}"
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

    style_specific = ""
    drawn_styles = {
        "Clean Line Art", "Loose Hand-Drawn Sketch", "Hand-Drawn Cartoon",
        "Watercolour Cartoon", "Children's Storybook Illustration",
        "Vintage Illustrated Cartoon Poster", "Coloured Pencil Illustration",
        "Minimal Continuous-Line Art"
    }
    if style_name in drawn_styles:
        style_specific = f"""
DRAWN-STYLE TREATMENT:
- Detail level: {art_settings.get('detail_level', 'Balanced')}.
- Background: {art_settings.get('background_treatment', 'Warm paper')}.
- Line colour: {art_settings.get('line_colour', 'Warm charcoal')}.
- Colour treatment: {art_settings.get('accent_colour', 'Restrained palette')}.
- Shading: {art_settings.get('shading_style', 'Light hatching')}.
- Outline strength: {art_settings.get('outline_strength', 'Balanced')}.
- Landmark treatment: {art_settings.get('realism_level', 'Gently simplified')}.
- Paper / texture: {art_settings.get('paper_texture', 'Light paper grain')}.
- Decorative framing: {art_settings.get('decorative_framing', 'None')}.
- Keep this one selected drawing method consistent across every destination.
"""
    if style_name in {"3D Family Animation", "Classic Fairytale Animation"}:
        style_specific += f"""
ANIMATION-STYLE TREATMENT:
- Overall mood: {art_settings.get('animation_mood', 'Warm and joyful')}.
- Character presence: {art_settings.get('character_presence', 'Tiny background figures only')}.
- Scene depth: {art_settings.get('cinematic_depth', 'Balanced cinematic depth')}.
- Surface finish: {art_settings.get('material_finish', 'Soft matte')}.
- Character expression: {art_settings.get('facial_expression', 'Friendly and expressive')}.
- Use only original characters and original visual design. Do not reproduce branded characters, costumes, logos or film-specific designs.
"""

    if style_name == "Bold Colour Retro Travel Poster":
        style_specific = f"""
BOLD-COLOUR POSTER TREATMENT:
- Rendering finish: {art_settings.get('poster_finish', 'Crisp graphic poster')}.
- Colour strength: {art_settings.get('colour_strength', 'Bold')}.
- Foliage framing: {art_settings.get('foliage_framing', 'Light top foliage framing')}.
- White poster border: {'include it' if art_settings.get('white_poster_border', True) else 'do not include it'}.
- Destination title position: {art_settings.get('destination_title_position', 'Below the artwork in the white margin')}.
- Smaller country subtitle: {'include it' if art_settings.get('country_subtitle', True) else 'omit it'}.
- Keep the landmark dominant and instantly recognisable.
- For Crisp graphic poster, use vivid saturated flat colour shapes and crisp graphic layering.
- For Painted graphic poster, use structured shapes with restrained hand-painted texture.
- For Watercolour retro poster, paint the entire scene with genuine transparent watercolour washes, visible paper grain, pigment blooms, softened edges and natural brush variation; do not use flat vector fills or screen-print-like hard edges.
"""

    return f"""Create one high-quality personalised combined-destination artwork.

LOCKED ART STYLE — USE ONLY {style_name.upper()}:
{style_direction}
Finish: {render_finish}
Palette: {render_palette}
Lighting/treatment: {render_lighting}
STYLE EXCLUSIONS: {render_exclusions}
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
{style_specific}
Use uploaded place references only for geographic identity, architecture and local details. Ignore conflicting art styles in reference photographs. Keep one consistent selected style edge to edge. Do not include mixed styles, warped architecture, duplicate landmarks, unrelated places, logos, watermarks or random text.

{production_prompt}
"""


def make_map_prompt(recipe):
    art = recipe.get("art_settings", {})
    production_prompt = make_production_prompt(recipe)
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
Fill each map silhouette using: {art.get("map_fill_style", "Colourful painterly splash")}, clipped strictly inside the geographic shape. Use this palette: {art.get("map_palette", "coordinated vibrant colours")}. Keep a warm neutral paper background and generous white space. Connect the maps using exactly this motif: {art.get("connection_motif", "Fine line with a heart loop")}. The connection must not obscure either silhouette.

TEXT:
Main title exactly: "{text['title']}".
Subtitle exactly: "{text['subtitle']}" if non-empty.
Spell all place and city labels exactly. Use elegant restrained typography.

DO NOT INCLUDE:
Landmarks, buildings, scenic horizons, sky, water, mountains, travel-poster scenery, mini-poster tiles, 3D maps, incorrect outlines, unrelated decorations, mixed art styles, logos, watermarks or extra text.

{production_prompt}
"""


def make_grid_prompt(recipe):
    art = recipe.get("art_settings", {})
    production_prompt = make_production_prompt(recipe)
    tile_lines = []
    for tile in recipe["poster_tiles"]:
        tile_lines.append(
            f"- Tile {tile['tile_number']}: {tile['display_name']}; feature {tile['main_landmark']}; "
            f"preserve {joined(tile.get('important_features', []))}; title exactly \"{tile['title_text']}\"."
        )
    return f"""Create one premium FAVOURITE PLACES GRID print.

STYLE LOCK:
Use one consistent {art.get("tile_style", "Vintage Retro Poster")} style across every tile. Do not merge the destinations into one panorama and do not mix illustration styles between tiles.

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

{production_prompt}
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

    return image


st.title("🎨 Place Blender 2.2 — Style-Matched Recipe Builder")
st.caption("Build 2.8 — animation styles")
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
)
canvas_settings = deepcopy(CANVAS_PRESETS[format_name])

st.subheader("1. Choose the art style")
style_name = st.selectbox(
    "Artwork style",
    list(ART_STYLE_PRESETS.keys()),
    help="The questions below change automatically to match the selected style."
)

recommended_blends = ART_STYLE_PRESETS[style_name]["recommended_blends"]
default_blend = DEFAULT_BLEND_BY_STYLE[style_name]
blend_mode = st.selectbox(
    "How should the places be combined?",
    recommended_blends,
    index=recommended_blends.index(default_blend),
    help="Only blend structures that suit this style are shown."
)
st.caption(f"Matched combination: {style_name} + {blend_mode}")

accuracy_mode = st.radio(
    "Place accuracy",
    ["Exact Landmark", "Balanced", "Artistic"],
    index=1,
    horizontal=True,
)

reference = st.file_uploader(
    "Optional reference image for place accuracy",
    type=["png", "jpg", "jpeg", "webp"],
    help="The reference is used for the place or building identity only. The selected art style remains locked."
)
if reference is not None:
    try:
        uploaded_image = Image.open(reference)
        st.image(uploaded_image, caption="Place reference", use_container_width=True)
    except Exception as exc:
        st.error(f"That image could not be opened: {exc}")

edited = []
include_labels = False
include_country_flags = False
label_colour = "warm cream-gold"
label_placement = "centred above its matching subject"
flag_anchor = "landmark_roof"
flag_placement = "mounted on the highest suitable architectural point"
flag_attachment_rule = "the flagpole base must visibly touch the matching landmark"
flag_scale = "large and clearly visible"
flag_width_percent = 14
uppercase_labels = True
horizon_y = canvas_settings["default_horizon_y"]
title_text = ""
subtitle_text = ""
extra_st.subheader("A1 print output")
print_preset_name = st.selectbox(
    "A1 format",
    ["A1 Portrait", "A1 Landscape"],
    index=0 if canvas_settings.get("orientation") == "portrait" else 1,
    help="Adds the real A1 physical size and pixel targets to the JSON and prompt."
)
bleed_mm = st.number_input("Bleed (mm)", min_value=0.0, max_value=10.0, value=3.0, step=0.5)
safe_margin_mm = st.number_input("Safe margin (mm)", min_value=0.0, max_value=40.0, value=15.0, step=1.0)
production_output = build_production_output(print_preset_name, bleed_mm, safe_margin_mm)

art_settings = {}

# ── MAP ART QUESTIONS ──────────────────────────────────────────────────────
if style_name == "Home to Home Map Art":
    st.subheader("2. Home-to-Home map details")
    st.info("This style uses map shapes, labels and a connection line. It will not ask for landmarks, water, horizons or flags.")
    count = st.slider("Number of connected places", 2, 4, 2)
    map_defaults = [("Australia", "Melbourne"), ("Great Britain", "London"), ("Italy", "Sicily"), ("Greece", "Santorini")]
    for index in range(count):
        with st.expander(f"Map {index + 1}", expanded=True):
            shape_name = st.text_input(
                "Country, state or region map shape",
                value=map_defaults[index][0],
                key=f"map_shape_{index}",
                help="Example: Australia, Victoria, Sicily, Great Britain or California"
            )
            location_label = st.text_input(
                "Town or city label",
                value=map_defaults[index][1],
                key=f"map_city_{index}"
            )
            display_label = st.text_input(
                "Main label under the map",
                value=shape_name,
                key=f"map_display_{index}"
            )
            edited.append({
                "display_name": display_label.strip() or shape_name.strip(),
                "country_name": shape_name.strip(),
                "typed_name": location_label.strip(),
                "main_landmark": "accurate geographic map silhouette",
                "secondary_elements": [],
                "important_features": ["correct coastline", "correct islands and geographic outline"],
                "terrain": "not applicable",
                "water": False,
                "label_text": display_label.strip() or shape_name.strip(),
                "matched_preset": None,
            })

    connection_motif = st.selectbox(
        "Connection design",
        ["Fine line with a heart loop", "Simple curved travel route", "Dotted flight path with a small heart", "Minimal straight connection line"]
    )
    map_fill_style = st.selectbox(
        "Map fill style",
        ["Colourful painterly splash", "Soft watercolour texture", "Coordinated abstract brush texture", "Solid minimal colours"]
    )
    map_palette = st.text_input(
        "Preferred colours",
        value="coral, teal, mustard, violet and warm pink",
        help="Leave as written or enter your own colour palette."
    )
    with st.expander("Title and wording", expanded=True):
        title_text = st.text_input("Main title", value="Home to Home", key="map_title")
        subtitle_text = st.text_input("Optional subtitle", placeholder="Example: Two homes, one heart", key="map_subtitle")
    extra_art_settings.update({
        "connection_motif": connection_motif,
        "map_fill_style": map_fill_style,
        "map_palette": map_palette.strip(),
    })

# ── GRID QUESTIONS ─────────────────────────────────────────────────────────
elif style_name == "Favourite Places Grid":
    st.subheader("2. Favourite Places grid details")
    st.info("Each place becomes its own matching mini poster tile. The app will not blend them into one panorama.")
    count = st.slider("Number of poster tiles", 2, 4, 4)
    grid_defaults = ["Tokyo", "Venice", "Paris", "Amalfi Coast"]
    tile_style = st.selectbox(
        "Style used consistently across every mini poster",
        ["Vintage Retro Poster", "Premium Travel Poster", "Soft Watercolour"]
    )
    for index in range(count):
        destination = match_destination(st.text_input(
            f"Place for tile {index + 1}", value=grid_defaults[index], key=f"grid_place_{index}"
        ))
        with st.expander(f"Tile {index + 1}: {destination['display_name']}", expanded=True):
            landmark = st.text_input("Main landmark or scene", value=destination["main_landmark"], key=f"grid_landmark_{index}")
            features = st.text_input("Important recognisable details", value=", ".join(destination.get("important_features", [])), key=f"grid_features_{index}")
            tile_title = st.text_input("Title shown on this tile", value=destination["display_name"].split(",")[0].upper(), key=f"grid_title_{index}")
            updated = deepcopy(destination)
            updated["main_landmark"] = landmark.strip()
            updated["important_features"] = [x.strip() for x in features.split(",") if x.strip()]
            updated["label_text"] = tile_title.strip()
            edited.append(updated)
    with st.expander("Overall heading and personalisation", expanded=True):
        title_text = st.text_input("Overall title", placeholder="Example: Our Favourite Places", key="grid_heading")
        subtitle_text = st.text_input("Optional names, date or subtitle", placeholder="Example: Michael & Joanne • Since 2018", key="grid_subheading")
    extra_art_settings["tile_style"] = tile_style

# ── INK SKETCH QUESTIONS ───────────────────────────────────────────────────
elif style_name == "Ink Sketch + Wash":
    st.subheader("2. Building or special-place portrait details")
    st.info("This style focuses on exact buildings, homes, restaurants, cafés or meaningful street scenes.")
    count = st.slider("Number of places or buildings", 1, 3, 1)
    sketch_defaults = ["Favourite restaurant", "Family home", "Wedding venue"]
    for index in range(count):
        with st.expander(f"Portrait subject {index + 1}", expanded=True):
            place_name = st.text_input("Place, venue or building name", value=sketch_defaults[index], key=f"sketch_place_{index}")
            location = st.text_input("Town, suburb or city", placeholder="Example: Carlton, Melbourne", key=f"sketch_location_{index}")
            exact_subject = st.text_input("Exact building or scene to draw", placeholder="Example: front façade of Da Nico Ristorante", key=f"sketch_subject_{index}")
            facade_details = st.text_area("Important details to preserve", placeholder="Example: red awnings, balcony, brick façade, outdoor dining fence", key=f"sketch_details_{index}")
            viewpoint = st.selectbox("Viewpoint", ["Straight-on front view", "Three-quarter street view", "Slightly elevated view", "Close architectural detail"], key=f"sketch_view_{index}")
            caption = st.text_input("Caption beneath this portrait", value=place_name, key=f"sketch_caption_{index}")
            edited.append({
                "display_name": f"{place_name}, {location}" if location else place_name,
                "country_name": "",
                "typed_name": place_name,
                "main_landmark": exact_subject.strip() or place_name,
                "secondary_elements": [x.strip() for x in facade_details.replace("\n", ",").split(",") if x.strip()],
                "important_features": [x.strip() for x in facade_details.replace("\n", ",").split(",") if x.strip()],
                "terrain": "architectural street portrait",
                "water": False,
                "label_text": caption.strip(),
                "viewpoint": viewpoint,
                "matched_preset": None,
            })
    with st.expander("Overall wording"):
        title_text = st.text_input("Optional main title", key="sketch_main_title")
        subtitle_text = st.text_input("Optional subtitle or date", key="sketch_subtitle")
    include_labels = any(item.get("label_text") for item in edited)

# ── SCENIC POSTER / RETRO / WATERCOLOUR QUESTIONS ─────────────────────────
else:
    st.subheader("2. Scenic place details")
    style_help = {
        "Premium Travel Poster": "Polished painterly destination art with recognisable architecture.",
        "Vintage Retro Poster": "Muted classic mid-century travel-poster art.",
        "Bold Colour Retro Travel Poster": "Bright saturated destination-poster art with crisp shapes, strong landmark focus and optional foliage framing.",
        "Soft Watercolour": "Soft hand-painted scenic artwork with gentle washes.",
        "Clean Line Art": "Precise landmark outlines with white space and optional restrained spot colour.",
        "Loose Hand-Drawn Sketch": "Expressive pen or pencil drawing with imperfect natural strokes.",
        "Hand-Drawn Cartoon": "Friendly polished cartoon travel art with recognisable simplified landmarks.",
        "Watercolour Cartoon": "Hand-drawn cartoon outlines painted with transparent watercolour washes.",
        "Children's Storybook Illustration": "Warm whimsical painted destination art with inviting storybook scenery.",
        "Vintage Illustrated Cartoon Poster": "Nostalgic outlined cartoon-poster art with limited retro colours.",
        "Coloured Pencil Illustration": "Textured layered pencil drawing with softly shaded architecture.",
        "Minimal Continuous-Line Art": "Elegant reduced contour drawing with abundant negative space.",
        "3D Family Animation": "Polished cinematic 3D destination art with rounded forms and feature-animation depth.",
        "Classic Fairytale Animation": "Elegant hand-drawn fairytale destination art with luminous painted backgrounds."
    }
    st.info(style_help.get(style_name, "Scenic place artwork"))
    count = st.slider("Number of destinations", 1, 4, 3)
    defaults = ["Melbourne", "Amalfi Coast", "Santorini", "Sicily"]
    typed = [st.text_input(f"Destination {i + 1}", value=defaults[i], key=f"destination_{i}") for i in range(count)]
    resolved = [match_destination(name) for name in typed if name.strip()]
    for index, destination in enumerate(resolved):
        with st.expander(f"{index + 1}. {destination['display_name']}", expanded=True):
            landmark = st.text_input("Main landmark or scenic focus", value=destination["main_landmark"], key=f"landmark_{index}")
            extras = st.text_input("Supporting scenery", value=", ".join(destination["secondary_elements"]), key=f"extras_{index}")
            features = st.text_input("Important recognisable details", value=", ".join(destination.get("important_features", [])), key=f"features_{index}")
            water = st.checkbox("Include water in this destination zone", value=destination["water"], key=f"water_{index}")
            default_label = destination["display_name"].split(",")[0].upper()
            label_text = st.text_input("Optional destination label", value=default_label, key=f"label_text_{index}")
            country_name = st.text_input("Country", value=destination.get("country_name", ""), key=f"country_name_{index}")
            updated = deepcopy(destination)
            updated["main_landmark"] = landmark.strip()
            updated["secondary_elements"] = [x.strip() for x in extras.split(",") if x.strip()]
            updated["important_features"] = [x.strip() for x in features.split(",") if x.strip()]
            updated["water"] = water
            updated["label_text"] = label_text.strip() or default_label
            updated["country_name"] = country_name.strip()
            edited.append(updated)

    with st.expander("Labels, flags and personalisation"):
        include_labels = st.checkbox("Include destination names", value=False)
        include_country_flags = st.checkbox("Attach a country flag to each landmark", value=False, disabled=not include_labels)
        title_text = st.text_input("Optional main title", placeholder="Example: Our Special Places", key="scenic_title")
        subtitle_text = st.text_input("Optional subtitle", placeholder="Example: Melbourne • Amalfi • Santorini", key="scenic_subtitle")
        if include_labels:
            label_colour = st.selectbox("Label colour", ["warm cream-gold", "warm cream", "soft white", "golden yellow", "deep teal", "deep navy"])
            uppercase_labels = st.checkbox("Use uppercase destination names", value=True)
            if include_country_flags:
                flag_scale = st.selectbox("Flag size", ["large and clearly visible", "extra large and prominent", "medium", "small and refined"])
                flag_width_percent = {"extra large and prominent": 18, "large and clearly visible": 14, "medium": 10, "small and refined": 7}[flag_scale]

    DRAWN_STYLE_NAMES = [
        "Clean Line Art", "Loose Hand-Drawn Sketch", "Hand-Drawn Cartoon",
        "Watercolour Cartoon", "Children's Storybook Illustration",
        "Vintage Illustrated Cartoon Poster", "Coloured Pencil Illustration",
        "Minimal Continuous-Line Art"
    ]
    if style_name in DRAWN_STYLE_NAMES:
        st.subheader("3. Choose exactly how the drawn style should look")
        detail_level = st.selectbox("Detail level", ["Minimal", "Simple", "Balanced", "Detailed"], index=2, key="drawn_detail")
        background_treatment = st.selectbox("Background", ["Clean white", "Warm paper", "Light scenic background", "Full scenic background"], index=1, key="drawn_bg")
        line_colour = st.selectbox("Line colour", ["Black", "Warm charcoal", "Sepia", "Deep navy", "Destination accent colour"], index=1, key="drawn_line_colour")
        accent_colour = st.selectbox("Colour treatment", ["Monochrome", "One spot colour", "Restrained palette", "Full colour"], index=2, key="drawn_colour")
        shading_style = st.selectbox("Shading", ["None", "Light hatching", "Soft painted shadows", "Layered detailed shading"], index=1, key="drawn_shading")
        outline_strength = st.selectbox("Outline strength", ["Delicate", "Balanced", "Bold"], index=1, key="drawn_outline")
        realism_level = st.selectbox("Landmark treatment", ["Accurate and natural", "Gently simplified", "Playfully simplified"], index=1, key="drawn_realism")
        paper_texture = st.selectbox("Paper / texture", ["None / clean", "Light paper grain", "Visible handmade paper", "Strong pencil or pigment texture"], index=1, key="drawn_texture")
        decorative_framing = st.selectbox("Decorative framing", ["None", "Light botanical corners", "Architectural accents", "Storybook foliage", "Simple poster border"], index=0, key="drawn_frame")
        extra_art_settings.update({
            "detail_level": detail_level,
            "background_treatment": background_treatment,
            "line_colour": line_colour,
            "accent_colour": accent_colour,
            "shading_style": shading_style,
            "outline_strength": outline_strength,
            "realism_level": realism_level,
            "paper_texture": paper_texture,
            "decorative_framing": decorative_framing,
        })

    if style_name == "Bold Colour Retro Travel Poster":
        st.subheader("3. Choose exactly how the poster should look")
        poster_finish = st.selectbox(
            "Poster finish",
            ["Graphic Retro", "Painted Retro", "Watercolour Retro", "Soft Poster Wash", "Detailed Illustrated Retro"],
            index=0,
            help="Graphic Retro is closest to the Bristol reference. Watercolour Retro is a true painted version. Painted Retro sits between them."
        )
        detail_level = st.selectbox("Detail level", ["Simple", "Balanced", "Detailed"], index=1)
        edge_style = st.selectbox("Edge style", ["Crisp", "Balanced", "Soft painted"], index=1)
        texture_strength = st.selectbox(
            "Texture strength",
            ["Clean / smooth", "Light texture", "Painterly texture", "Strong watercolour texture"],
            index=1
        )
        colour_mood = st.selectbox(
            "Colour mood",
            ["Soft", "Balanced", "Bold", "Vibrant", "Sun-faded vintage"],
            index=2
        )
        typography_style = st.selectbox(
            "Typography style",
            ["Modern Sans", "Classic Serif", "Vintage Poster", "Minimal Clean"],
            index=0
        )
        border_style = st.selectbox(
            "Border / framing",
            ["No border", "Thin white border", "Wide white poster margin", "Framed print mockup"],
            index=2
        )
        foliage_framing = st.selectbox(
            "Decorative foliage framing",
            ["None", "Light top foliage", "Top corners only", "Top and sides", "Top and bottom", "Architectural framing instead"],
            index=1
        )
        title_position = st.selectbox(
            "Destination title position",
            ["Below the artwork in the white margin", "Inside the lower artwork area", "No destination title"]
        )
        country_subtitle = st.checkbox(
            "Show smaller country name below each destination title",
            value=True,
            disabled=(title_position == "No destination title")
        )
        extra_art_settings.update({
            "poster_finish": poster_finish,
            "detail_level": detail_level,
            "edge_style": edge_style,
            "texture_strength": texture_strength,
            "colour_mood": colour_mood,
            "colour_strength": colour_mood,
            "typography_style": typography_style,
            "border_style": border_style,
            "white_poster_border": border_style != "No border",
            "foliage_framing": foliage_framing,
            "destination_title_position": title_position,
            "country_subtitle": country_subtitle,
        })
        if title_position != "No destination title":
            include_labels = True
            label_placement = "large destination name below the artwork in the selected poster margin, with a smaller country subtitle directly beneath" if title_position.startswith("Below") else "large destination name integrated inside the lower artwork area"
            label_colour = "deep teal or deep navy"
            uppercase_labels = True
            include_country_flags = False

    horizon_y = st.slider(
        "Horizon height",
        canvas_settings["horizon_min"], canvas_settings["horizon_max"], canvas_settings["default_horizon_y"],
        key=f"horizon_{canvas_settings['orientation']}"
    )

label_settings = {
    "enabled": include_labels,
    "font_style": ({
        "Modern Sans": "clean modern uppercase sans-serif poster lettering",
        "Classic Serif": "elegant classic high-contrast serif travel-poster lettering",
        "Vintage Poster": "bold condensed vintage tourism-poster lettering",
        "Minimal Clean": "minimal geometric sans-serif lettering with generous spacing",
    }.get(extra_art_settings.get("typography_style", "Modern Sans"), "clean modern uppercase sans-serif poster lettering") if style_name == "Bold Colour Retro Travel Poster" else "elegant classic high-contrast serif lettering inspired by premium travel prints"),
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
    "flag_accuracy": "use the correct national flag colours, layout and proportions"
}

if st.button("Build artwork recipe and prompt", type="primary", use_container_width=True):
    if not edited:
        st.error("Enter at least one place.")
    elif style_name == "Home to Home Map Art" and any(not item.get("country_name", "").strip() for item in edited):
        st.error("Enter every country, state or region map shape.")
    else:
        art_settings = {
            "style": style_name,
            "blend_mode": blend_mode,
            "accuracy_mode": accuracy_mode,
            "title_text": title_text,
            "subtitle_text": subtitle_text,
            "production_output": production_output,
            **extra_art_settings,
        }
        recipe = make_recipe(edited, horizon_y, label_settings, canvas_settings, art_settings)
        prompt = make_prompt(recipe)
        guide_image = make_guide(recipe)
        if isinstance(guide_image, (bytes, bytearray)):
            guide_png = bytes(guide_image)
        else:
            guide_buffer = io.BytesIO()
            guide_image.save(guide_buffer, format="PNG")
            guide_png = guide_buffer.getvalue()
        st.session_state["recipe"] = recipe
        st.session_state["prompt"] = prompt
        st.session_state["guide_png"] = guide_png

if "recipe" in st.session_state:
    recipe = st.session_state["recipe"]
    prompt = st.session_state["prompt"]
    guide_png = st.session_state["guide_png"]
    recipe_signature = hashlib.sha1(
        json.dumps(recipe, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:12]

    st.divider()
    st.subheader("Visual layout guide")
    st.image(guide_png, use_container_width=True)

    st.download_button(
        label="Download layout guide PNG",
        data=guide_png,
        file_name=f"place_blend_{recipe['style_preset']['canvas']['orientation']}_layout_guide.png",
        mime="image/png",
        key=f"download_layout_guide_png_{recipe_signature}",
        use_container_width=True
    )

    st.subheader("JSON recipe")
    recipe_text = json.dumps(recipe, indent=2, ensure_ascii=False)
    st.code(recipe_text, language="json")

    st.download_button(
        label="Download JSON recipe",
        data=recipe_text.encode("utf-8"),
        file_name=f"place_blend_{recipe['style_preset']['canvas']['orientation']}_recipe.json",
        mime="application/json",
        key=f"download_json_recipe_{recipe_signature}",
        use_container_width=True
    )

    st.subheader("ChatGPT prompt")
    st.text_area(
        "Copy this prompt into ChatGPT",
        value=prompt,
        height=560,
        key="generated_prompt_text"
    )

    st.download_button(
        label="Download prompt TXT",
        data=prompt.encode("utf-8"),
        file_name=f"place_blend_{recipe['style_preset']['canvas']['orientation']}_prompt.txt",
        mime="text/plain",
        key=f"download_prompt_txt_{recipe_signature}",
        use_container_width=True
    )

    if recipe.get("destination_label_style", {}).get("enabled"):
        st.success(
            "The recipe includes the destination names, correct country flags, roof attachment and the selected larger flag size."
        )

    st.info(
        "Upload the approved reference image, the layout guide PNG and this prompt together."
    )
