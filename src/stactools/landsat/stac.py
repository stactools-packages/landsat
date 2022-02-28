from typing import Any, Dict, Optional

import pystac
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
from pystac_client import Client
from stactools.core.io import ReadHrefModifier
from stactools.core.utils import href_exists

from stactools.landsat.ang_metadata import AngMetadata
from stactools.landsat.assets import (ANG_ASSET_DEF, COMMON_ASSET_DEFS,
                                      SR_ASSET_DEFS, THERMAL_ASSET_DEFS)
from stactools.landsat.constants import (L8_EXTENSION_SCHEMA, L8_INSTRUMENTS,
                                         L8_ITEM_DESCRIPTION, L8_PLATFORM,
                                         USGS_C2L2_SR, USGS_STAC_API)
from stactools.landsat.mtl_metadata import MtlMetadata


def create_stac_item(
        mtl_xml_href: str,
        use_usgs_stac: bool = False,
        read_href_modifier: Optional[ReadHrefModifier] = None) -> pystac.Item:
    """Creates a Landsat 8 C2 L2 STAC Item.

    Reads data from a single scene of
    Landsat Collection 2 Level-2 Surface Reflectance Product data.

    Uses the MTL XML HREF as the bases for other files; assumes that all
    files are co-located in a directory or blob prefix.
    """
    base_href = '_'.join(mtl_xml_href.split('_')[:-1])  # Remove the _MTL.txt

    mtl_metadata = MtlMetadata.from_file(mtl_xml_href, read_href_modifier)

    ang_href = ANG_ASSET_DEF.get_href(base_href)
    ang_metadata = AngMetadata.from_file(ang_href, read_href_modifier)

    scene_datetime = mtl_metadata.scene_datetime

    if use_usgs_stac:
        geometry = get_usgs_geometry(base_href, mtl_metadata.product_id,
                                     read_href_modifier)
    else:
        geometry = None

    if geometry is None:
        geometry = ang_metadata.get_scene_geometry(mtl_metadata.bbox)

    item = pystac.Item(id=mtl_metadata.scene_id,
                       bbox=mtl_metadata.bbox,
                       geometry=geometry,
                       datetime=scene_datetime,
                       properties={})

    item.common_metadata.platform = L8_PLATFORM
    item.common_metadata.instruments = L8_INSTRUMENTS
    item.common_metadata.description = L8_ITEM_DESCRIPTION

    # eo
    eo = EOExtension.ext(item, add_if_missing=True)
    eo.cloud_cover = mtl_metadata.cloud_cover

    # view
    view = ViewExtension.ext(item, add_if_missing=True)
    view.off_nadir = mtl_metadata.off_nadir
    view.sun_elevation = mtl_metadata.sun_elevation
    # Sun Azimuth in landsat metadata is -180 to 180 from north, west being negative.
    # In STAC, it's 0 to 360 clockwise from north.
    sun_azimuth = mtl_metadata.sun_azimuth
    if sun_azimuth < 0.0:
        sun_azimuth = 360 + sun_azimuth
    view.sun_azimuth = sun_azimuth

    # projection
    projection = ProjectionExtension.ext(item, add_if_missing=True)
    projection.epsg = mtl_metadata.epsg
    projection.bbox = mtl_metadata.proj_bbox

    # landsat8
    item.stac_extensions.append(L8_EXTENSION_SCHEMA)
    item.properties.update(**mtl_metadata.additional_metadata)
    item.properties['landsat:scene_id'] = ang_metadata.scene_id

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

    usgs_item_page = (
        f"https://landsatlook.usgs.gov/stac-browser/collection02/level-2/standard/oli-tirs"
        f"/{scene_datetime.year}"
        f"/{mtl_metadata.wrs_path}/{mtl_metadata.wrs_row}"
        f"/{mtl_metadata.scene_id}")

    item.add_link(
        pystac.Link(rel="alternate",
                    target=usgs_item_page,
                    title="USGS stac-browser page",
                    media_type="text/html"))

    return item


def get_usgs_geometry(
    base_href: str,
    product_id: str,
    read_href_modifier: Optional[ReadHrefModifier] = None
) -> Optional[Dict[str, Any]]:
    """Attempts to get scene geometry from a USGS STAC Item.

    Args:
        base_href (str): Base href to a STAC storage location
        product_id (str): Scene product id from mtl metadata
        read_href_modifier (Callable[[str], str]): An optional function to
            modify the storage href (e.g. to add a token to a url)
    Returns:
        Optional[Dict[str, Any]]: Either a GeoJSON geometry or None
    """
    # Check data storage first
    stac_href = f"{base_href}_SR_stac.json"
    if read_href_modifier is not None:
        stac_href = read_href_modifier(stac_href)

    if href_exists(stac_href):
        item = pystac.Item.from_file(stac_href)
    else:
        item = None

    # If not found, check the USGS STAC API
    if item is None:
        collection = USGS_C2L2_SR
        product_id = f"{product_id}_SR"

        catalog = Client.open(USGS_STAC_API)
        search = catalog.search(collections=[collection], ids=[product_id])
        if search.matched() == 1:
            item = next(search.get_items())
        else:
            item = None

    if item is not None:
        return item.geometry
    else:
        return None
