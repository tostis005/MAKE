#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import sys
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SYSTEM = ROOT / "content" / "pattern-system"
COLLECTION_ID = "iconic-destinations"
COL_DIR = SYSTEM / "collections" / COLLECTION_ID
COLLECTION_PATH = COL_DIR / "collection.json"
SOURCE = COL_DIR / "approved-pixel-designs" / "D0001-paris-eiffel-tower.png"
PATTERN_PATH = SYSTEM / "patterns" / "D0001-CS" / "pattern.json"
PRODUCT_PATH = SYSTEM / "products" / "D0001-CS" / "product.json"
CATALOG_PATH = ROOT / "content" / "products" / "catalog.json"
STORE_ASSETS = ROOT / "content" / "products" / "assets"
STORE_FILES = ROOT / "content" / "products" / "files"
MOCKUP = COL_DIR / "assets" / "iconic-room.jpg"

D0001_PALETTE = [[20,155,252],[13,150,252],[12,148,251],[4,148,252],[12,153,252],[27,157,253],[56,150,190],[34,160,253],[85,173,176],[167,228,242],[148,194,212],[35,166,251],[63,94,61],[63,58,37],[61,179,252],[111,89,62],[146,144,119],[74,189,250],[147,105,77],[89,194,254],[45,170,251],[111,62,38],[70,20,21],[183,110,100],[69,187,254],[23,18,15],[80,40,28],[145,212,254],[169,231,254],[156,218,248],[203,142,130],[64,183,254],[100,196,232],[225,244,255],[239,254,255],[49,178,252],[108,204,254],[235,235,241],[105,200,249],[154,212,237],[232,174,188],[235,205,235],[243,179,219],[233,199,200],[244,134,182],[248,153,196],[228,106,149],[238,112,179],[184,84,107],[182,60,103]]
D0001_INDEX_ZLIB_B64 = "eNqNWoliolyzNBlFILIqEAER48IiAr7/y92qPoCacf779STKdrp67z5kZh+KZkIfH5+kP28IF+ez2Sd+56TPj/eP/bUIHx9kO4H8G2P+8THnEwttKcd/BOO/4Lxi8Esu/A+Mpa5Rn/mfP/9W+TfG7ONjstZ0+DfCnBg0kWaYc9oMGB//EePPg/ETvcMQms00Uwfe7IOa/VcMJc17jPn8z5xfnx8DwmLxpa003qBD/gOG3F5M/niriOKtzARjEsPSCC1PfQ5M/h8Me7TVLxzgivQUeYJgVOmOqy0I8vlfMIS82cQTXn/2u3D+GM0kGPOltnJ8f6XB5R+fCIA/6vY74Z9O1qMSnx9PATxC0O4Pd89mGy0IgyDQFsRgdgxP/cJ49hIOvYnjlCaizJj282eMubaKSLDWH2XLR7zgQIXIp8qbJ5jv0Tzzj5eiIlDEetICgbvyieFrsz+zT2K8LP2cf77HUBDy9OwdjfVpPl8sZtpWkUYjCcZDS+EwH2z+lD2fn95MeXOImweB4xOMXFkutG0Yh0G8hdNn89GQg1URMfMZa+UQhlP2fHoLAfmYS1AN3BXJwXBJrjJ0LT8MnNUXHp6/VXumHKqUVyifNlZ+ggfE+JxNDBX7xWwAEfYLMt04JF0q/GzxDwzFaD4fi6b9ZSdpurOXYLL8HHVYLt4Qob5WQeY4mgJQV2cvzzz0Xn5u1qDvz8+9nR9+fn5ybfbMffkAWaqTJelrtlkFfkCMxf+gmbKBph1A6fLj+KPocFpuBk4Dfb2cDLSx4HNHAweF/BDo8UF7LQRBOO+S9c/PWQ5Te/mWFhN/hRH4/oCxnDCWSrpJEWDMTsko/WE8+jmkl83XZpL+a9LkAYBDbRUE0YixXIxiTAKpaMRd7fAzUfI43Nlf5LoBLzIm9+WLEgOGg5r4tVz8rTAxVBQu1ruftxiptnldRdt8vZLyuQ5Bv94bdrDWE9ufn9PPw1j2hixns8WLozebF4zYD3wNveodxhSWi+TJVE/+MBJwW3zZdr5Rmo8Qf2E4Gp5TpnyrBw5Oh/Pg8IPY6pwS9GDm9maxYbbggMbfvMHQrDAKYu1rJt5Z/A7ApSQhDlXWwTaGcTicoICRnnla5PZyZ9AxCRkvx49fGBn1UBHw9bDoUgJluRDbzma2NmGkxSkFGcZguDHiNly6Gfi/YjjMj82A8RRzQ6gz9RJEbioI6W4H5snugfFzKAYzaipuN+LwCQOnGiD8eLV5E3KCsbnA+Gmeq0AFAjAOiZFOmpzHnP9JTvbmHR31EP4IVuru4CuRQw6XtpY+wvRg7HY7+ONnZxyIsSsOEgPnMf+1dwjHV4xfhCqxzo0JYrcrAMF42glHACqcUZODbuKxtRhr5A/ydD+I/HBlfx2PvDZxH+h0GCMWlgHTHSvvQX0CEagp1DsPXi+g9OHyqsTxqOlBHAWOuzk+AEYU73LKVeqdDQUAnghaBJYQTwsohl8Y8HwmEoyXJsnGs48D2fZRSmIQ+N7GtqfrSoI1+dPch/MAoFBwcsJ3QlMVjLAdvX8oCphRMvSQaun6OLKzbR0YWRA7+fEJAzc2mpdSNINi40dCNh1g0lNRJEkCQyXJ2luvEyiSJjhJE8+zbYi7tvfkJxyBEcV+nAW6/Yxhr5PkckoG2hn4l1zWOUUvUupRyHUok9tgmjNd8tPpklzEyrAzARRH+6g7ATCCEcOerGiLPLYHShinibfULrtU0Yl9/SIgp2889Q1t1JIpmORUfRIjC4hxtB/Yr+Tl67XnbU4JE3B3ueT5WsLCu4DW9vfLos2zlKTv3I3o8yjQ4ZD9frrx7JlxMW13uqwfgT3w2R+P++Nglqd1w03vO/czxm4Qufpx/xZDlioOYjmbYff1JO3I+mGc4WQPoff7733uBBK7wYoOERCFdBzEGuQbsbFIQnuEx7NQgg/sRwAFO2HsgRESA0VRV1cmDHtkrYCGi/snJvyFmPZ7Eh1Anpc7ErmZv9K/98/GGjV+9t5DxQFdSWoP6/YiuRw8IRDD99GjfN8VjAf/Me7s46toe5Vb+ML6729h9P09ID2Ruk4IT3fQzB3YynW94yCELDjak4WfV4ugcIMH7lw/gOwFRj6eIUaMwI3iuHQCxxvdMbBSAg+xMWEI8hE5560vKQrJACM68Xi/91618DwXVkIWun4Q5OShHhNdvDyXs9EYDxhkJfI63/3scm+tNCDG97B4xPAmjAwQTogQzm0K/K2Q8JskRXLyvr9/YzB6qYSMPtBE9BS7jZZ7sIcsXu7GcHpMXYDxPVgVjO21NPC0WD9QRiR8oViproTKNajgqQdVhXvFcCwX824Jz+fKUErj70S18UP+y6/KEGsUrgP70WFHi040bn0Uf6FcR1Ch6jqum/mmt5+i0TsZQ4/dJaMiE3E5uhFGE3bgNMnXnlIDMpvScc31iCAY4vLIWUWRS4zB5bZoIRY/wFqe9xsDAcH1OQsvizKDAGEwzsT5BAEM33VL7GvdcxBbym/747eXykhzELem2mgIJIWn2D04rC+AoUvEOBPGQXUYwXCDcOvHVuxu3cyRWPUuSYG5QJlB+jNbEpManC65ScOsvcvI4STNcq2slaRPk/34hI4pFDBW6DtR5FB7sTQG5R2UkO6X5GaSnjzByHmP/Wp9EVo/E6y3wzSntowHPU8GTXQH3o7jLRTxHSfnotNFGflCI6Cli7mVnKdCojVH405GEMGh6XKqzx2DIZMJDCFL4Q7H1bH9cCzHdTIHdrichpX4oFqX03qwPdRIlbWNImXD5aOTU2BEmlVGmJ0x6IJpqLgULnaCiF0rdFGwAte8DBhvKE+Lp73a4cVWFwwVBUcjjtmciMfZkoOTH8SBzy7oIwmBUZwubzEw9uSHwzMG5hz88FcEyBNRDFdk/FKTGELGtByHnRYIPj8c31npl/XpN8blJKtkvJWBDp43TyONT3vKqPk45nH8SlNzuw1/kaX9ZSucJwdFRaK2NvjQTw+QlwUXXpKo4UdubmMo4j9RYOli59PTmiSdKBGGpwuw8tPpGeVFJDH3RZ0UFjbmyk40VQBbWfrpGYPHMjOrkXTkmcgPPorHtclol8sDBpyQGtjTopKEMfY5oRVjkOMzgwUkPU5/ERGgBzALsyqSF6P9phMwAsy6KLsYd0POvAEyZP284pQIxxf2Mk1fEPpmVZalWTxrqJ5KRgb4LDN57ZpF6jtC2zUvJ6WHlKFpcE+GhUli1lV9LQq9rEH4KAvTTMabj4WjTIWrHD34I1JZOD33QjLqwgFFWVZNWVX6rWlvdV1VJYCKQqn7NxVGHG63sT+8ew1xEMbuLvk3FQWFv9bVtTKrqmpqGKtuurb+56LimoGt4wwYlhtuEWSyP3pDZGP2XX1rwL06C8atgjJt21b/wtgZbuRsLX/lmiBdX7lOGPuB+RZDJa6Z9V3bw0B1bd7qG6lp2xpbrGRX1Ubx16LCxaTrxr5l0ghJsUK2uPh5h7Ezr9eKBaXM2u5WN03jNl1DlLap+WKjMGDDYvcbw3BZouJoZSoxsfeMndjJjDcqGGZ5rVCoiqoExq253dwObqjrrm2bCjXseoXvK2O3e4Uw3MyFOyJdtsWoQCvaKo5+eV1VwQo8zkZ1LnuYHxC12dw6qtHeabuqlDiuzGdVKBpbUxj4pmAYhm5xsEb5gnkfT+5SxA6Y1E19PldVK4SgdauaJ/e2ltvlFSDQr6rGugMeO+OKycp1otBUO2/DdLLYYrWn72SDrzwhciNGK+zVq5JOvt262qkqhXEG2BnBjGcauKocYoxhkJhsrnEQhboUfDRI1w+tFRqKWSgnjBjdrWlgCQRsdYYLEKrIDAf+aHvyhHZn3OxbXLjhdzfG1K7IAtddYd9hmaqpGKnJ1ybAyJ7fW9CKkBYeAFIlBKPVtd/e721bQoMr9AMGMdum68zdFLiFG/kWWTp8bSDNzbQwwaPEu+YrSNETA/HaXpl9dAv8ATt1PLmC4JoepuuJIEZSwpkBZmlkR+AOvREolh87wHF8ebPDYJOIK8ymbejpFhpQaDiojhQG1Civ8Hp7Bw4uS1wN6hslxk8kSBBOGIZhQY2QHV7ew+zktYX0VkTsHabp6JLrgEHTMHpviFkEQYtgqKs0nZQ3Tdf1o4ydL5BKosjKMtV6r1dTjTGclpBiJi1zbxCerLJIiq7xuw6ZjkCq8QMtBbJ+YGAkRD/C3gYDu7USchz8WjKbBNgguo5LCIY008MA4/4ONyihEQNdz0Rs7vA0HNVJFLdZaQwEjHBrsY5vA9RcpceVHwFmiJAtcRtuV/IaF1whJNIbsoN7zzC+NTTb/Vbfw7CSYnJjjN27gwq7K8vO7ur7ZYQy7keY3rIsw+4gQ2GBesN0gu+MxqqYfbSNyAnLgD1TAD/3260Pg4qxAF3uKDFIdwSAKHs1diZ6XjSOO8wIVJVANunBYwziLqlSydcJxp0JDoz2jihuAxQOOIL8MZbFQ+OtO5Z82syNeTmM498TXPiY6ayUO7GyzEqEP+Ly3kpo3Ukw0z1oWH3pinsIC7PM1w2LJOvJFck2Dm7O0MqpgVAcqy8EhMTVtWLaAePWDuzpDHgDetw6aALdENDOtrt1pBpfqC7nQ3omF75Roi5CMNegmxohsPHBFueAGigQKnDusDqrU9WIP2CnRkKBGL0qyKxmrM/G4apkdzKaywKxylsWAdltFZkGqxDyDfHUwcuQv4fQLLNUJhAHUQtWrDII7goFcdex1juKT+RLCaR9fNFMfiKJLshQ12gODcppI2ulwqI6AfbWDZ6h0HKt7DN5lhiNRJgfyVYgwzfiC87whyiLVDwTw4/wMNgP4qFPtKpcIZTZ/lR1OaM7oroAhYVSGaxrqhLRT95RhhxE1A4jolDIyXfE8tHi+qzvKXKLsa0R91Y3gnSdL/wwzmFWkNKI6OhGjEyZPc7AEb5mGg5zIgdFXAuigGEQBD3KUwmBgdGL6+Hemo2EzdYVO5XMe3YU3kOrEowuA4eQUyFfhcImcjIMiiGBMMBjsov5piaDYW8qouhqAiCW2MerKuuoVi3IKDiM7ysf7rr+HmAfHjo+JkKo4BABVVEKo0WcQFwRbh35LsFWlQoWLumFHccrZHiGLEC1pBSSelCLY2lX18DosyyAMkoHa+WuTNmPsoC7LnBEgQhtF885CMRGJIWgDcKs7hgJtJZ/Pv8g1BpBlEBjmWekS/FCVIXYDfjUQTeK8Q9Lhmm4yBLM1vR+FPtRHPQsDZUYG/X3ztRgm4DdHWqmspMFBd2qPVNTsSjyBy4RhJVuqkY0EnBgMubLNgyiBiEFIc/K5uwbzY3hiRbbdI7qgo0UXsmfvlSzC63XNvz709ayVvrhBYF0AAqHxzjMuBY+5hRYSTUiJ6nxMBkwcOXWSFmXdKwwg5WVehqE8Ua0KKTXsWnb+UMVl3sSP2AjQm0tJWjZsMEdyQJq6PlAjNR26HJ3pW49OETq8e2aBYAwD4a8NkrTXFsubXN0ywGKWFEEJ2IlogdGpr3YNlg3wTC4E6OTghUjFpn493PdsbHfBANEZ7gV/1B2SIt0x79/a9AEMMaBQynXtbfBhZ0IieU0DKTumtARjN6J+nu4jekTdHsOeTeGSMUI7toozOpO5/CRa2mqaUvNS/KcOAamFn27zZgDoDNHq06NInewD8K+acIYNoI7HKfHrITJDXUjuAkEnmWP50BxDcquc3XdzDUtTzTQRj5No+DXdot4lKyoxA/iDXbCrg8xNzjxvYceLYLD38JJTbiF8zAJIceRQI00SHSViKGCWQQcc20gbtm0lZOV7p3zscw4w7SA1gdZcTmO+34btrRVh/JjbTOH/5WHky5ivWcwcn/VtD62GRCqww5e1/IJw7ia2BXCGCXbRkfpKVvcM9P6ADkDG4W9swWAI9HMrSrCUAY4msyhPOyX3W27vZYZynbXZDCYbuqy6zRdbDsdhASmIYjKEA38tumDuL/LTkCmA7CFrF1PjEYKqo+NqHRzB2UVz0MtxAn2yRyoHDDDrpZDcYmPK2qj7+IQo9aWFm77EC6us214Z7cFTiD1mRU8k6Tkvls0ip2udSzBR38I2t7CxO5mGabPyAFb1MDr1Wf5tSzfza4uttPW1r/fKbSb+TEDFu7kR6gwegzGfd+37ALUqN9aTaPudTGvQRgXfF3sy1hooRS2EHKEGy5asMNCb93vHFk5CVGpFjMGxOdLibjtsYdgN+AsC7GwCCtL4RDHUzvifGg5KyqErTecc5VZlH8F8VHJ+LijUOU7zHw6F/jqDj8piGo/K55jmzd1Oz4bsKP7vrtSRoNvgEDK2OAxk1iBjN3q+REQuqlGhnlJripA6W9QxhmehoiwdcQGhCZi8b0rt2u+qwZf9aEmBuyqVz5dhL0uxniHh7xLPjQROZBpJCNGFpWldFFhx1Eqgu95xn2Ho676Io/iCVMiNvwokEsBez4SEwbFpJTR3kHGGSlzFAZffOFGhpZTljKCOHydG7MMOA8ChL8aiQaADFgHKWSaR7nNspK9Ex1ywPB95V3IgoiI+IfMDFut/i5acP4c+T3hgN8IQXvQZz6s46MmItWhBMIKIpMzZzB3fO8V9PfbNWIcRcC440kBH7i9IExIYi44l8a1MP+wn96Bld0aODJ+vFAbYyJzy8oVd6+wp8QYIpfB3sWP68rvSg5JjhzyV1+pgFqZFWqbhJZ7LadYw5k+kanef6mDx1X9/yE+q/a6RTFxQGN5Wji8Nx1/cvk3vn6V99SX4e3oaToY37gOa6e3p5fLeHtgqm55/wetPUfq"
D0001_RAW_SHA256 = "820e7103fadef9348bd7dade5de72dd782c841570fac555086a1edbdf7461e0d"

sys.path.insert(0, str((SYSTEM / "pixel_importer").resolve()))
import import_pixel_sheet as pixel  # noqa: E402

sys.path.insert(0, str((SYSTEM / "renderer").resolve()))
import render as renderer  # noqa: E402


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configure_collection_mockup():
    if not MOCKUP.is_file():
        raise FileNotFoundError(f"Missing collection mockup: {MOCKUP}")

    collection = read_json(COLLECTION_PATH)
    spec = collection.get("mockup_spec") or {}
    frame = spec.get("frame") or {}
    area = frame.get("area_px") or {}
    required = ("x", "y", "width", "height")
    if not frame.get("enabled") or any(k not in area for k in required):
        raise RuntimeError("Iconic Destinations calibrated mockup frame is missing from collection.json")
    if float(frame.get("padding_ratio", 0)) != 0:
        raise RuntimeError("Iconic Destinations pixel mockup must keep padding_ratio=0")
    if str(frame.get("stitch_fit", "")).lower() != "cover":
        raise RuntimeError("Iconic Destinations pixel mockup must use stitch_fit=cover")
    return collection

def ensure_exact_d0001_source():
    indices = zlib.decompress(base64.b64decode(D0001_INDEX_ZLIB_B64))
    if len(indices) != 100 * 120:
        raise RuntimeError(f"Unexpected D0001 pixel-index length: {len(indices)}")
    pixels = [tuple(D0001_PALETTE[i]) for i in indices]
    raw = bytes(channel for px in pixels for channel in px)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != D0001_RAW_SHA256:
        raise RuntimeError(f"D0001 exact source checksum mismatch: {digest}")
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (100, 120))
    image.putdata(pixels)
    image.save(SOURCE, format="PNG", optimize=False)
    return image


def build_exact_d0001():
    ensure_exact_d0001_source()
    image = pixel.read_image(SOURCE)
    if image.size != (100, 120):
        raise RuntimeError(f"D0001 exact source must be 100x120, got {image.size}")

    pattern = pixel.build_exact_pattern(image, "D0001-CS", "Paris Eiffel Tower")
    pixel.validate_exact_roundtrip(image, pattern)
    pattern.update({
        "base_design_id": "D0001",
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "palette_mode": "per-design",
        "status": "ready",
        "source_mode": "pixel-exact",
        "source_asset": "collections/iconic-destinations/approved-pixel-designs/D0001-paris-eiffel-tower.png",
        "pixel_to_stitch": "1:1",
        "colour_mapping": "exact-rgb-no-quantization",
        "mosaic_source": {
            "sheet_size": [1000, 720],
            "rows": 6,
            "cols": 10,
            "tile_size": [100, 120],
            "tile_row": 0,
            "tile_col": 0,
            "extraction": "exact-crop-no-resize"
        },
    })
    write_json(PATTERN_PATH, pattern)

    product = read_json(PRODUCT_PATH)
    product.update({
        "code": "D0001-CS",
        "base_design_id": "D0001",
        "technique_code": "CS",
        "collection": COLLECTION_ID,
        "title": "Paris Eiffel Tower",
        "title_en": "Paris Eiffel Tower",
        "title_es": "París — Torre Eiffel",
        "design_slug": "paris-eiffel-tower",
        "technique": "cross-stitch",
        "pattern_file": "patterns/D0001-CS/pattern.json",
        "website": "www.drielo.com",
        "status": "ready",
        "render_ready": True,
        "renderer": "standard",
        "source_artwork": pattern["source_asset"],
        "palette_mode": "per-design",
        "source_mode": "pixel-exact",
    })
    write_json(PRODUCT_PATH, product)
    return pattern


def update_catalog(pattern):
    catalog = read_json(CATALOG_PATH)
    existing_iconic = [
        row for row in catalog.get("products", [])
        if row.get("collection") == COLLECTION_ID
    ]
    retired = set(catalog.get("retired_products", []))
    retired.update(
        row.get("sku") for row in existing_iconic
        if row.get("sku")
    )

    template = next(
        (row for row in existing_iconic if row.get("code") == "D0001-CS"),
        None,
    )
    if template is None:
        raise RuntimeError("D0001-CS catalog row not found")

    colours = len(pattern["threads"])
    row = dict(template)
    row.update({
        "code": "D0001-CS",
        "sku": "DRIELO-D0001-CS",
        "price": 2.99,
        "title": "Paris Eiffel Tower Cross Stitch Pattern PDF",
        "title_en": "Paris Eiffel Tower Cross Stitch Pattern PDF",
        "title_es": "Patrón PDF de punto de cruz: París — Torre Eiffel",
        "slug": "paris-eiffel-tower-cross-stitch-pattern",
        "collection": COLLECTION_ID,
        "stitches": 12000,
        "grid": "100 × 120 stitches",
        "colours": colours,
        "color_count": colours,
        "grid_width": 100,
        "grid_height": 120,
        "skill": "Intermediate",
        "skill_en": "Intermediate",
        "skill_es": "Intermedio",
        "stitch_type": "Full cross stitch",
        "stitch_type_en": "Full cross stitch",
        "stitch_type_es": "Punto de cruz completo",
        "short_description": (
            f"Downloadable Paris Eiffel Tower cross-stitch pattern. "
            f"Exact 100 × 120 pixel-to-stitch chart; {colours} exact source colours; "
            "one source pixel equals one full cross stitch. Code: D0001-CS."
        ),
        "short_description_en": (
            f"Downloadable Paris Eiffel Tower cross-stitch pattern. "
            f"Exact 100 × 120 pixel-to-stitch chart; {colours} exact source colours; "
            "one source pixel equals one full cross stitch. Code: D0001-CS."
        ),
        "short_description_es": (
            f"Patrón descargable de la Torre Eiffel de París. "
            f"Gráfico exacto 100 × 120; {colours} colores exactos de la imagen; "
            "cada píxel equivale a una puntada completa. Código: D0001-CS."
        ),
        "description": (
            "<p><strong>Paris Eiffel Tower Cross Stitch Pattern PDF</strong>.</p>"
            "<p>Pixel-by-pixel edition: every source pixel is one full cross stitch. "
            "The pattern is generated without resizing, colour reduction, smoothing or DMC remapping.</p>"
            f"<ul><li>Grid: 100 × 120 stitches</li><li>Total stitches: 12,000</li>"
            f"<li>Exact source colours: {colours}</li></ul>"
            "<p>The PDF includes the finished preview, exact colour key, colour charts and black-and-white symbol charts.</p>"
        ),
        "description_en": (
            "<p><strong>Paris Eiffel Tower Cross Stitch Pattern PDF</strong>.</p>"
            "<p>Pixel-by-pixel edition: every source pixel is one full cross stitch. "
            "The pattern is generated without resizing, colour reduction, smoothing or DMC remapping.</p>"
            f"<ul><li>Grid: 100 × 120 stitches</li><li>Total stitches: 12,000</li>"
            f"<li>Exact source colours: {colours}</li></ul>"
            "<p>The PDF includes the finished preview, exact colour key, colour charts and black-and-white symbol charts.</p>"
        ),
        "description_es": (
            "<p><strong>París — Torre Eiffel: patrón PDF de punto de cruz</strong>.</p>"
            "<p>Edición píxel a píxel: cada píxel de la imagen fuente corresponde exactamente a una puntada completa. "
            "No se redimensiona, reduce, suaviza ni remapea la paleta.</p>"
            f"<ul><li>Cuadrícula: 100 × 120</li><li>Puntadas: 12.000</li>"
            f"<li>Colores exactos: {colours}</li></ul>"
            "<p>El PDF incluye vista previa, clave de colores exactos, gráficos a color y gráficos en blanco y negro con símbolos.</p>"
        ),
        "download": "files/Drielo_D0001-CS.pdf",
        "featured_image": "assets/D0001-CS-product.webp",
        "gallery": [],
        "gallery_revision": 20260925,
        "design_id": "D0001-CS",
        "base_design_id": "D0001",
        "technique_code": "CS",
        "technique": "cross-stitch",
        "size_attribute_label": "Pattern size",
        "colour_attribute_label": "Exact colours",
        "type_attribute_label": "Technique",
        "count_attribute_label": "Total stitches",
    })

    catalog["products"] = [
        p for p in catalog.get("products", [])
        if p.get("collection") != COLLECTION_ID
    ]
    catalog["products"].append(row)
    catalog["retired_products"] = sorted(retired)

    coll = next(
        c for c in catalog.get("collections", [])
        if c.get("slug") == COLLECTION_ID
    )
    coll["cover_asset"] = "assets/D0001-CS-product.webp"
    coll["palette_mode"] = "per-design"
    coll["show_collection_palette"] = False
    coll["palette_hex"] = []
    coll["thread_codes"] = []
    coll["techniques"] = ["cross-stitch"]

    write_json(CATALOG_PATH, catalog)
    return [r.get("sku") for r in existing_iconic if r.get("sku")]


def render_and_stage():
    pdf = renderer.render("D0001-CS", fix=False)
    output = SYSTEM / "output" / "D0001-CS"
    image = output / "D0001-CS-product.webp"
    if not image.is_file():
        raise RuntimeError("Featured product image was not rendered")

    STORE_ASSETS.mkdir(parents=True, exist_ok=True)
    STORE_FILES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(image, STORE_ASSETS / image.name)
    shutil.copy2(pdf, STORE_FILES / pdf.name)

    if pdf.stat().st_size < 10000 or pdf.read_bytes()[:4] != b"%PDF":
        raise RuntimeError("Invalid D0001 PDF")
    if image.stat().st_size < 10000:
        raise RuntimeError("Invalid D0001 featured image")
    return pdf, image


def main():
    configure_collection_mockup()
    pattern = build_exact_d0001()
    retired = update_catalog(pattern)
    pdf, image = render_and_stage()

    source = pixel.read_image(SOURCE)
    saved = read_json(PATTERN_PATH)
    pixel.validate_exact_roundtrip(source, saved)

    print(json.dumps({
        "product": "D0001-CS",
        "grid": [100, 120],
        "stitches": 12000,
        "exact_colours": len(pattern["threads"]),
        "retire_from_live_collection": retired,
        "mockup": str(MOCKUP),
        "frame_test": {
            "area_px": [75, 27, 121, 149],
            "padding_ratio": 0.0,
            "stitch_offset_x_ratio": 0.0,
            "stitch_offset_y_ratio": 0.0,
            "stitch_fit": "cover",
            "intent": "fill the detected frame opening, no white padding, centered"
        },
        "pdf": str(pdf),
        "featured_image": str(image),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
