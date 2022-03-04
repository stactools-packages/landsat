import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pystac import Item, Link
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from pystac.extensions.scientific import ScientificExtension
from pystac.extensions.view import ViewExtension
from pystac_client import Client
from shapely.geometry import box, mapping
from stactools.core.io import ReadHrefModifier
from stactools.core.utils import href_exists

from stactools.landsat.ang_metadata import AngMetadata
from stactools.landsat.assets import (ANG_ASSET_DEF, COMMON_ASSET_DEFS,
                                      SR_ASSET_DEFS, THERMAL_ASSET_DEFS)
from stactools.landsat.constants import (L8_EXTENSION_SCHEMA, L8_INSTRUMENTS,
                                         L8_ITEM_DESCRIPTION, L8_PLATFORM,
                                         LANDSAT_EXTENSION_SCHEMA, SENSORS,
                                         USGS_API, USGS_BROWSER_C2, USGS_C2L1,
                                         USGS_C2L2_SR, Sensor)
from stactools.landsat.fragments import Fragments
from stactools.landsat.mtl_metadata import MtlMetadata

logger = logging.getLogger(__name__)


def create_stac_item(
        mtl_xml_href: str,
        use_usgs_geometry: bool = False,
        read_href_modifier: Optional[ReadHrefModifier] = None) -> Item:
    """Creates a STAC Item for Landsat 1-5 Collection 2 Level-1 or Landsat
    4-5, 7-9 Collection 2 Level-2 scene data.

    Args:
        mtl_xml_href (str): An href to an MTL XML metadata file.
        use_usgs_geometry (bool): Option to use the geometry from a USGS STAC
            file that is stored alongside the XML metadata file or pulled from
            the USGS STAC API.
        read_href_modifier (Callable[[str], str]): An optional function to
            modify the MTL and USGS STAC hrefs (e.g. to add a token to a url).
    Returns:
        pystac.Item: A STAC Item representing the Landsat scene.
    """
    base_href = '_'.join(mtl_xml_href.split('_')[:-1])  # Remove the _MTL.txt

    mtl_metadata = MtlMetadata.from_file(mtl_xml_href, read_href_modifier)

    sensor = Sensor(mtl_metadata.item_id[1])

    if use_usgs_geometry:
        geometry = get_usgs_geometry(base_href, sensor,
                                     mtl_metadata.product_id,
                                     read_href_modifier)
    else:
        geometry = None

    if geometry is None:
        if sensor is Sensor.OLI_TIRS:
            ang_href = ANG_ASSET_DEF.get_href(base_href)
            ang_metadata = AngMetadata.from_file(ang_href, read_href_modifier)
            geometry = ang_metadata.get_scene_geometry(mtl_metadata.bbox)
        else:
            geometry = mapping(box(*mtl_metadata.bbox))
            logger.warning(
                f"Using bbox for geometry for {mtl_metadata.product_id}.")

    item = Item(id=mtl_metadata.item_id,
                bbox=mtl_metadata.bbox,
                geometry=geometry,
                datetime=mtl_metadata.scene_datetime,
                properties={})

    if sensor is Sensor.OLI_TIRS:
        item.common_metadata.platform = L8_PLATFORM
        item.common_metadata.instruments = L8_INSTRUMENTS
        item.common_metadata.description = L8_ITEM_DESCRIPTION

        # eo
        eo_item = EOExtension.ext(item, add_if_missing=True)
        eo_item.cloud_cover = mtl_metadata.cloud_cover

        # view
        view = ViewExtension.ext(item, add_if_missing=True)
        view.off_nadir = mtl_metadata.off_nadir
        view.sun_elevation = mtl_metadata.sun_elevation
        view.sun_azimuth = mtl_metadata.sun_azimuth

        # projection
        projection = ProjectionExtension.ext(item, add_if_missing=True)
        projection.epsg = mtl_metadata.epsg
        projection.bbox = mtl_metadata.proj_bbox

        # landsat8
        item.stac_extensions.append(L8_EXTENSION_SCHEMA)
        item.properties.update(**mtl_metadata.landsat_metadata)

        # -- Add assets

        # Add common assets
        for asset_definition in COMMON_ASSET_DEFS:
            asset_definition.add_asset(item, mtl_metadata, base_href)

        # Add SR assets
        for asset_definition in SR_ASSET_DEFS:
            asset_definition.add_asset(item, mtl_metadata, base_href)

        # Add thermal assets, if this is a L2SP product
        if mtl_metadata.processing_level == 'L2SP':
            for asset_definition in THERMAL_ASSET_DEFS:
                asset_definition.add_asset(item, mtl_metadata, base_href)

        # -- Add links
        # NOTE: This link is incorrect. Leads to a dead "page". The last
        # component needs to have the processing time in it (replace item_id
        # with product_id to fix). May warrant a GitHub issue.
        usgs_item_page = (f"{USGS_BROWSER_C2}/level-2/standard/oli-tirs"
                          f"/{mtl_metadata.scene_datetime.year}"
                          f"/{mtl_metadata.wrs_path}/{mtl_metadata.wrs_row}"
                          f"/{mtl_metadata.item_id}")

        item.add_link(
            Link(rel="alternate",
                 target=usgs_item_page,
                 title="USGS stac-browser page",
                 media_type="text/html"))

    else:
        satellite = int(mtl_metadata.item_id[2:4])
        level = int(mtl_metadata.item_id[6])

        item.common_metadata.platform = f"landsat-{satellite}"
        item.common_metadata.instruments = SENSORS[sensor.name]["instruments"]
        item.common_metadata.created = datetime.now(tz=timezone.utc)
        item.common_metadata.gsd = SENSORS[sensor.name]["reflective_gsd"]
        if level == 1:
            item.common_metadata.description = "Landsat Collection 2 Level-1 Data Product"
        elif level == 2:
            item.common_metadata.description = "Landsat Collection 2 Level-2 Science Product"

        fragments = Fragments(sensor, satellite, base_href,
                                mtl_metadata.level1_radiance)

        # Common assets
        assets = fragments.common_assets()
        for key, asset in assets.items():
            # MSS data does not have an angle file
            if sensor is Sensor.MSS and key.startswith("ANG"):
                continue
            # MTL files are specific to the processing level
            if key.startswith("MTL"):
                asset.description = asset.description.replace(
                    "Level-X", f"Level-{level}")
            item.add_asset(key, asset)

        # Optical assets
        assets = fragments.sr_assets()
        eo_bands = fragments.sr_eo_bands()
        raster_bands = fragments.sr_raster_bands()
        for key, asset in assets.items():
            item.add_asset(key, asset)
            eo_band = eo_bands.get(key, None)
            if eo_band is not None:
                optical_eo = EOExtension.ext(asset, add_if_missing=True)
                optical_eo.bands = [Band.create(**eo_band)]
            raster_band = raster_bands.get(key, None)
            if raster_band is not None:
                optical_raster = RasterExtension.ext(asset,
                                                        add_if_missing=True)
                optical_raster.bands = [RasterBand.create(**raster_band)]

        # Thermal assets (only exist if optical exist)
        if mtl_metadata.processing_level == 'L2SP':
            assets = fragments.st_assets()
            eo_bands = fragments.st_eo_bands()
            raster_bands = fragments.st_raster_bands()
            for key, asset in assets.items():
                item.add_asset(key, asset)
                eo_band = eo_bands.get(key, None)
                if eo_band is not None:
                    thermal_eo = EOExtension.ext(asset, add_if_missing=True)
                    thermal_eo.bands = [Band.create(**eo_band)]
                raster_band = raster_bands.get(key, None)
                if raster_band is not None:
                    thermal_raster = RasterExtension.ext(asset,
                                                            add_if_missing=True)
                    thermal_raster.bands = [RasterBand.create(**raster_band)]
                if key.startswith("ST_B"):
                    asset.common_metadata.gsd = SENSORS[
                        sensor.name]["thermal_gsd"]

        eo_item = EOExtension.ext(item, add_if_missing=True)
        eo_item.cloud_cover = mtl_metadata.cloud_cover

        view = ViewExtension.ext(item, add_if_missing=True)
        view.off_nadir = mtl_metadata.off_nadir
        view.sun_elevation = mtl_metadata.sun_elevation
        view.sun_azimuth = mtl_metadata.sun_azimuth

        projection = ProjectionExtension.ext(item, add_if_missing=True)
        projection.epsg = mtl_metadata.epsg
        projection.shape = mtl_metadata.sr_shape
        projection.transform = mtl_metadata.sr_transform

        scientific = ScientificExtension.ext(item, add_if_missing=True)
        scientific.doi = SENSORS[sensor.name]["doi"]

        item.stac_extensions.append(LANDSAT_EXTENSION_SCHEMA)
        item.properties.update(**mtl_metadata.landsat_metadata)
        item.properties["landsat:correction"] = item.properties.pop(
            "landsat:processing_level")

        # Link to USGS STAC browser for this item
        instrument = "-".join(i for i in SENSORS[sensor.name]["instruments"])
        usgs_item_page = (
            f"{USGS_BROWSER_C2}/level-{level}/standard/{instrument}"
            f"/{mtl_metadata.scene_datetime.year}"
            f"/{mtl_metadata.wrs_path}/{mtl_metadata.wrs_row}"
            f"/{mtl_metadata.product_id}")
        item.add_link(
            Link(rel="alternate",
                    target=usgs_item_page,
                    title="USGS stac-browser page",
                    media_type="text/html"))

    return item


def get_usgs_geometry(
    base_href: str,
    sensor: Sensor,
    product_id: str,
    read_href_modifier: Optional[ReadHrefModifier] = None
) -> Optional[Dict[str, Any]]:
    """Attempts to get scene geometry from a USGS STAC Item.

    Args:
        base_href (str): Base href to a STAC storage location
        sensor (Sensor): Enum of MSS, TM, ETM, or OLI-TIRS
        product_id (str): Scene product id from mtl metadata
        read_href_modifier (Callable[[str], str]): An optional function to
            modify the storage href (e.g. to add a token to a url)
    Returns:
        Optional[Dict[str, Any]]: Either a GeoJSON geometry or None
    """
    # Check data storage first
    if sensor is Sensor.MSS:
        stac_href = f"{base_href}_stac.json"
    else:
        stac_href = f"{base_href}_SR_stac.json"

    if read_href_modifier is not None:
        stac_href = read_href_modifier(stac_href)

    if href_exists(stac_href):
        item = Item.from_file(stac_href)
    else:
        item = None

    # If not found, check the USGS STAC API
    if item is None:
        if sensor is Sensor.MSS:
            collection = USGS_C2L1
        else:
            collection = USGS_C2L2_SR
            product_id = f"{product_id}_SR"

        catalog = Client.open(USGS_API)
        search = catalog.search(collections=[collection], ids=[product_id])
        if search.matched() == 1:
            item = next(search.get_items())
        else:
            item = None

    if item is not None:
        return item.geometry
    else:
        return None
