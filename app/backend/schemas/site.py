from pydantic import BaseModel, Field


class Site(BaseModel):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    description: str
    science_value: str
    image_path: str | None = None
    terrain_available: bool = False


class SiteRequest(BaseModel):
    site_id: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

