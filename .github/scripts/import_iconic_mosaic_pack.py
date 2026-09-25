#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import re
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION = SYSTEM / "collections" / "iconic-destinations"
DESIGNS_PATH = COLLECTION / "designs.json"
QUEUE_PATH = SYSTEM / "iconic_destinations" / "publish_queue.json"
PIXEL_DIR = COLLECTION / "pixel-sources"
PACK_DIR = SYSTEM / "iconic_destinations" / "source-pack"

TITLES = [
    ("Mount Rushmore", "Monte Rushmore", "mount-rushmore"),
    ("Hollywood Sign", "Letrero de Hollywood", "hollywood-sign"),
    ("Times Square New York", "Times Square de Nueva York", "times-square-new-york"),
    ("Brandenburg Gate Berlin", "Puerta de Brandeburgo de Berlín", "brandenburg-gate-berlin"),
    ("Osaka Castle", "Castillo de Osaka", "osaka-castle"),
    ("Toronto CN Tower", "Torre CN de Toronto", "toronto-cn-tower"),
    ("Quebec City Chateau Frontenac", "Château Frontenac de Quebec", "quebec-chateau-frontenac"),
    ("Hallstatt Lakeside Village", "Hallstatt junto al lago", "hallstatt-lakeside-village"),
    ("Dubrovnik Old Town", "Casco antiguo de Dubrovnik", "dubrovnik-old-town"),
    ("Capri Faraglioni", "Faraglioni de Capri", "capri-faraglioni"),
    ("Golden Gate Bridge", "Puente Golden Gate", "golden-gate-bridge"),
    ("London Tower Bridge", "Tower Bridge de Londres", "london-tower-bridge"),
    ("Mont Saint-Michel", "Mont Saint-Michel", "mont-saint-michel"),
    ("Neuschwanstein Castle", "Castillo de Neuschwanstein", "neuschwanstein-castle"),
    ("Athens Acropolis", "Acrópolis de Atenas", "athens-acropolis"),
    ("Angkor Wat", "Angkor Wat", "angkor-wat"),
    ("Ha Long Bay", "Bahía de Ha Long", "ha-long-bay"),
    ("Cappadocia Balloons", "Globos de Capadocia", "cappadocia-balloons"),
    ("Chichen Itza", "Chichén Itzá", "chichen-itza"),
    ("Istanbul Blue Mosque", "Mezquita Azul de Estambul", "istanbul-blue-mosque"),
    ("Barcelona Sagrada Familia", "Sagrada Familia de Barcelona", "barcelona-sagrada-familia"),
    ("Prague Castle", "Castillo de Praga", "prague-castle"),
    ("Niagara Falls", "Cataratas del Niágara", "niagara-falls"),
    ("Mount Fuji", "Monte Fuji", "mount-fuji"),
    ("Machu Picchu", "Machu Picchu", "machu-picchu"),
    ("Petra Treasury", "El Tesoro de Petra", "petra-treasury"),
    ("Dubai Burj Khalifa", "Burj Khalifa de Dubái", "dubai-burj-khalifa"),
    ("Venice Grand Canal", "Gran Canal de Venecia", "venice-grand-canal"),
    ("Prague Charles Bridge", "Puente de Carlos de Praga", "prague-charles-bridge"),
    ("Amsterdam Canals", "Canales de Ámsterdam", "amsterdam-canals"),
    ("Paris Eiffel Tower", "Torre Eiffel de París", "paris-eiffel-tower"),
    ("London Big Ben", "Big Ben de Londres", "london-big-ben"),
    ("Rome Colosseum", "Coliseo de Roma", "rome-colosseum"),
    ("New York Statue of Liberty", "Estatua de la Libertad de Nueva York", "new-york-statue-liberty"),
    ("Taj Mahal", "Taj Mahal", "taj-mahal"),
    ("Great Wall of China", "Gran Muralla China", "great-wall-china"),
    ("Rio Christ the Redeemer", "Cristo Redentor de Río", "rio-christ-redeemer"),
    ("Pyramids of Giza", "Pirámides de Guiza", "pyramids-giza"),
    ("Sydney Opera House", "Ópera de Sídney", "sydney-opera-house"),
    ("Santorini Blue Domes", "Cúpulas azules de Santorini", "santorini-blue-domes"),
    ("Cartagena Colorful Streets", "Calles coloridas de Cartagena", "cartagena-colorful-streets"),
    ("Havana Capitol", "Capitolio de La Habana", "havana-capitol"),
    ("Easter Island Moai", "Moáis de la Isla de Pascua", "easter-island-moai"),
    ("Bali Temple Gate", "Puerta de templo de Bali", "bali-temple-gate"),
    ("Mykonos Windmills", "Molinos de Mykonos", "mykonos-windmills"),
    ("Cape Town Table Mountain", "Montaña de la Mesa de Ciudad del Cabo", "cape-town-table-mountain"),
    ("Vatican St Peter Basilica", "Basílica de San Pedro del Vaticano", "vatican-st-peter-basilica"),
    ("Leaning Tower of Pisa", "Torre inclinada de Pisa", "leaning-tower-pisa"),
    ("Stonehenge", "Stonehenge", "stonehenge"),
    ("Moscow Saint Basil Cathedral", "Catedral de San Basilio de Moscú", "moscow-saint-basil-cathedral"),
    ("Positano Amalfi Coast", "Positano en la Costa Amalfitana", "positano-amalfi-coast"),
    ("Cinque Terre Village", "Pueblo de Cinque Terre", "cinque-terre-village"),
    ("Tokyo Tower and Fuji", "Torre de Tokio y Monte Fuji", "tokyo-tower-fuji"),
    ("Singapore Marina Bay", "Marina Bay de Singapur", "singapore-marina-bay"),
    ("Hong Kong Victoria Harbour", "Victoria Harbour de Hong Kong", "hong-kong-victoria-harbour"),
    ("Shanghai Pudong Skyline", "Skyline de Pudong en Shanghái", "shanghai-pudong-skyline"),
    ("Seoul Gyeongbokgung Palace", "Palacio Gyeongbokgung de Seúl", "seoul-gyeongbokgung-palace"),
    ("Chefchaouen Blue City", "Ciudad azul de Chefchaouen", "chefchaouen-blue-city"),
    ("Marrakech Koutoubia Mosque", "Mezquita Koutoubia de Marrakech", "marrakech-koutoubia-mosque"),
    ("Bagan Temples and Balloons", "Templos y globos de Bagan", "bagan-temples-balloons"),
]

if len(TITLES) != 60:
    raise SystemExit("Expected exactly 60 Iconic Destinations titles")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


parts = sorted(PACK_DIR.glob("part-*.txt"))
if not parts:
    raise SystemExit(f"No source-pack parts found in {PACK_DIR}")

encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
payload = json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))

expected = {f"D{i:04d}.pixz" for i in range(1, 61)}
if set(payload) != expected:
    missing = sorted(expected - set(payload))
    extra = sorted(set(payload) - expected)
    raise SystemExit(f"Source pack mismatch missing={missing} extra={extra}")

PIXEL_DIR.mkdir(parents=True, exist_ok=True)
for i in range(1, 61):
    name = f"D{i:04d}.pixz"
    value = payload[name].strip()
    raw = zlib.decompress(base64.b64decode(value, validate=True))
    if not raw or raw[0] != 50:
        raise SystemExit(f"{name}: expected 50-colour source, got {raw[0] if raw else 'empty'}")
    palette_end = 1 + 50 * 3
    if len(raw) != palette_end + 100 * 120:
        raise SystemExit(f"{name}: malformed exact 100x120 pixel source")
    (PIXEL_DIR / name).write_text(value + "\n", encoding="ascii")

designs_doc = load_json(DESIGNS_PATH)
designs = []
queue_items = []
for i, (title_en, title_es, slug) in enumerate(TITLES, 1):
    base = f"D{i:04d}"
    source_rel = f"collections/iconic-destinations/source-designs/{base}-{slug}.png"
    designs.append({
        "order": i,
        "base_design_id": base,
        "title_en": title_en,
        "title_es": title_es,
        "slug": slug,
        "reference_board": "mosaic-row-major",
        "variants": [f"{base}-CS"],
        "artwork_status": "exact-100x120-source-ready",
        "source_asset": source_rel,
        "planned_source_asset": source_rel,
        "palette_mode": "per-design",
        "palette_status": "awaiting-dmc-map",
        "target_master_grid": {"width": 100, "height": 120, "max_long_side_stitches": 120},
        "target_chart_pages": 4,
        "source_colour_count": 50,
        "dmc_colour_count": None,
    })
    queue_items.append({
        "base_design_id": base,
        "title_en": title_en,
        "title_es": title_es,
        "slug": slug,
        "pixel_source": f"collections/iconic-destinations/pixel-sources/{base}.pixz",
        "status": "pending",
        "attempts": 0,
        "last_run": None,
        "last_error": None,
    })

designs_doc["designs"] = designs
write_json(DESIGNS_PATH, designs_doc)

queue = load_json(QUEUE_PATH)
queue["auto_continue"] = True
queue["max_attempts_per_design"] = 2
queue["items"] = queue_items
write_json(QUEUE_PATH, queue)

# Remove stale generated source previews; the publisher recreates each one from
# the exact pixel source in row-major order.
for directory in (COLLECTION / "approved-pixel-designs", COLLECTION / "source-designs"):
    if directory.is_dir():
        for path in directory.glob("D*.png"):
            if re.match(r"^D\d{4}-", path.name):
                path.unlink()

print("Prepared 60 exact 100x120 Iconic Destinations sources in mosaic row-major order.")
