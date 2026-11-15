from fastapi import APIRouter

from app.backend.schemas.site import Site

router = APIRouter(tags=["sites"])

PRESETS = [
    Site(
        id="shackleton-rim",
        name="Shackleton rim",
        lat=-89.9,
        lon=0.0,
        description="South-pole rim with near-continuous illumination potential.",
        science_value="Water-ice and permanently shadowed region access",
        terrain_available=False,
    ),
    Site(
        id="malapert-massif",
        name="Malapert Massif",
        lat=-85.99,
        lon=0.0,
        description="High-relief south-pole massif; coordinates are approximate.",
        science_value="Highland geology and communications relay studies",
        terrain_available=False,
    ),
    Site(
        id="nobile-region",
        name="Nobile region",
        lat=-85.0,
        lon=30.0,
        description="Candidate south-pole landing region; coordinates are approximate.",
        science_value="Volatiles and permanently shadowed terrain",
        terrain_available=False,
    ),
    Site(
        id="apollo-11",
        name="Apollo 11",
        lat=0.674,
        lon=23.473,
        description="Historic non-polar reference site.",
        science_value="Reference mission comparison",
        terrain_available=False,
    ),
    Site(
        id="apollo-17",
        name="Apollo 17",
        lat=20.19,
        lon=30.77,
        description="Historic non-polar reference site.",
        science_value="Reference mission comparison",
        terrain_available=False,
    ),
]


@router.get("/presets", response_model=list[Site])
def list_presets() -> list[Site]:
    return PRESETS
