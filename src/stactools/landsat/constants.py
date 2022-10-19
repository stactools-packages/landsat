from enum import Enum
from typing import Any, Dict


class Sensor(Enum):
    MSS = "M"
    TM = "T"
    ETM = "E"
    OLI_TIRS = "C"


LANDSAT_EXTENSION_SCHEMA = (
    "https://landsat.usgs.gov/stac/landsat-extension/v1.1.1/schema.json"
)
CLASSIFICATION_EXTENSION_SCHEMA = (
    "https://stac-extensions.github.io/classification/v1.0.0/schema.json"  # noqa
)
USGS_API = "https://landsatlook.usgs.gov/stac-server"
USGS_BROWSER_C2 = "https://landsatlook.usgs.gov/stac-browser/collection02"
USGS_C2L1 = "landsat-c2l1"
USGS_C2L2_SR = "landsat-c2l2-sr"
USGS_C2L2_ST = "landsat-c2l2-st"
COLLECTION_IDS = ["landsat-c2-l1", "landsat-c2-l2"]

SENSORS: Dict[str, Any] = {
    "MSS": {
        "instruments": ["mss"],
        "doi": "10.5066/P9AF14YV",
        "doi_title": "Landsat 1-5 MSS Collection 2 Level-1",
        "reflective_gsd": 79,
    },
    "TM": {
        "instruments": ["tm"],
        "doi": "10.5066/P9IAXOVV",
        "doi_title": "Landsat 4-5 TM Collection 2 Level-2",
        "reflective_gsd": 30,
        "thermal_gsd": 120,
    },
    "ETM": {
        "instruments": ["etm+"],
        "doi": "10.5066/P9C7I13B",
        "doi_title": "Landsat 7 ETM+ Collection 2 Level-2",
        "reflective_gsd": 30,
        "thermal_gsd": 60,
    },
    "OLI_TIRS": {
        "instruments": ["oli", "tirs"],
        "doi": "10.5066/P9OGBGM6",
        "doi_title": "Landsat 8-9 OLI/TIRS Collection 2 Level-2",
        "reflective_gsd": 30,
        "thermal_gsd": 100,
    },
}

COORDINATE_PRECISION = 6
