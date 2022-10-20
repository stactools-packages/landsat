from typing import Any, Dict, List, Optional

import shapely.affinity
import shapely.ops
from pystac import Item
from pystac_client import Client
from shapely.geometry import MultiPolygon, Polygon, shape
from stactools.core.io import ReadHrefModifier
from stactools.core.utils import antimeridian, href_exists
from stactools.core.utils.antimeridian import Strategy
from stactools.core.utils.raster_footprint import update_geometry_from_asset_footprint

from stactools.landsat.ang_metadata import AngMetadata
from stactools.landsat.constants import (
    DENSIFICATION_FACTOR,
    SIMPLIFY_TOLERANCE,
    USGS_API,
    USGS_C2L1,
    USGS_C2L2_SR,
    GeometrySource,
    Sensor,
)
from stactools.landsat.mtl_metadata import MtlMetadata


class GeometryError(Exception):
    pass


def get_usgs_geometry(
    base_href: str,
    sensor: Sensor,
    product_id: str,
    read_href_modifier: Optional[ReadHrefModifier] = None,
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
            item = next(search.items())
        else:
            item = None

    if item is not None:
        return item.geometry
    else:
        return None


def handle_antimeridian(item: Item, antimeridian_strategy: Strategy) -> Item:
    """Handles some quirks of the antimeridian.

    Applies the requested SPLIT or NORMALIZE strategy via the stactools
    antimeridian utility. If the geometry is already SPLIT (a MultiPolygon,
    which can occur when using USGS geometry), a merged polygon with different
    longitude signs is created to match the expected input of the fix_item
    function.

    Args:
        item (Item): STAC Item
        antimeridian_strategy (Antimeridian): Either split on +/-180 or
            normalize geometries so all longitudes are either positive or
            negative.

    Returns:
        Item: The original PySTAC Item, with updated antimeridian geometry.
    """
    geometry = shape(item.geometry)
    if isinstance(geometry, MultiPolygon):
        # force all positive lons so we can merge on an antimeridian split
        polys = list(geometry.geoms)
        for index, poly in enumerate(polys):
            coords = list(poly.exterior.coords)
            lons = [coord[0] for coord in coords]
            if min(lons) < 0:
                polys[index] = shapely.affinity.translate(poly, xoff=+360)
        merged_geometry = shapely.ops.unary_union(polys)

        # revert back to + and - lon signs for fix_item's expected input
        merged_coords = list(merged_geometry.exterior.coords)
        for index, coord in enumerate(merged_coords):
            if coord[0] > 180:
                merged_coords[index] = (coord[0] - 360, coord[1])
        item.geometry = Polygon(merged_coords)

    return antimeridian.fix_item(item, antimeridian_strategy)


def round_coordinates(item: Item, precision: int) -> Item:
    """Rounds an Item's geometry and bbox geographic coordinates.

    Any tuples encountered will be converted to lists.

    Args:
        item (Item): A pystac Item.
        precision (int): Number of decimal places for rounding.

    Returns:
        Item: The original PySTAC Item, with rounded coordinates.
    """

    def recursive_round(coordinates: List[Any], precision: int) -> List[Any]:
        for idx, value in enumerate(coordinates):
            if isinstance(value, (int, float)):
                coordinates[idx] = round(value, precision)
            else:
                coordinates[idx] = list(value)  # handle any tuples
                coordinates[idx] = recursive_round(coordinates[idx], precision)
        return coordinates

    if item.geometry is not None:
        item.geometry["coordinates"] = recursive_round(
            list(item.geometry["coordinates"]), precision
        )

    if item.bbox is not None:
        item.bbox = recursive_round(list(item.bbox), precision)

    return item


def _update_geometry(
    item: Item,
    geometry_source: GeometrySource,
    base_href: str,
    sensor: Sensor,
    mtl_metadata: MtlMetadata,
    footprint_asset_name: Optional[str] = None,
    read_href_modifier: Optional[ReadHrefModifier] = None,
) -> Item:
    """Updates the Item geometry using the specified geometry source.
    Args:
        item (Item): PySTAC Item to be updated.
        geometry_source (GeometrySource): Source for Item geometry. Choices:
            USGS: Use USGS STAC Item geometry. The USGS STAC Item must exist in
                same directory as the MTL XML file.
            FOOTPRINT: Use the data footprint derived from one of the Item
                assets, which can be specified in `footprint_asset_name` option.
                The asset file must exist in the same directory as the MTL XML
                file. If the `footprint_asset_name` option is not specified,
                the first asset from which a footprint can be successfully
                created will be used.
            ANG: Use the ANG metadata file. Only valid for Landsat 8 and 9. The
                ANG text file must exist in the same directory as the MTL XML file.
            BBOX: Use the bounding box derived from the MTL XML metadata.
        base_href (str): Base HREF from which HREFs to other files can be generated.
        sensor (Sensor): Enum of MSS, TM, ETM, or OLI-TIRS sensors.
        mtl_metadata (MtlMetadata): MTL MetaData class.
        footprint_asset_name (Optional[str]): Name of asset to use if the
            'footprint' option is selected for the `geometry_source` argument.
        read_href_modifier (Callable[[str], str]): An optional function to
            modify an HREF (e.g., to add a token to the HREF).
    Returns:
        Item: The original PySTAC Item, with updated geometry.
    """
    if geometry_source is GeometrySource.USGS:
        item.geometry = get_usgs_geometry(
            base_href, sensor, mtl_metadata.product_id, read_href_modifier
        )
        if item.geometry is None:
            raise GeometryError("Unable to use USGS STAC Item geometry.")

    elif geometry_source is GeometrySource.FOOTPRINT:
        asset_name = [footprint_asset_name] if footprint_asset_name else []
        result = update_geometry_from_asset_footprint(
            item,
            asset_names=asset_name,
            densification_factor=DENSIFICATION_FACTOR,
            simplify_tolerance=SIMPLIFY_TOLERANCE,
        )
        if not result:
            raise GeometryError("Unable to generate geometry from the raster data.")

    elif geometry_source is GeometrySource.ANG:
        if geometry_source is GeometrySource.ANG and sensor is not Sensor.OLI_TIRS:
            raise GeometryError(
                "The 'ANG' metadata file can only be used as the geometry source "
                "for scenes collected by the OLI-TIRS sensor on Landsat 8 and 9."
            )
        ang_href = f"{base_href}_ANG.txt"
        ang_metadata = AngMetadata.from_file(ang_href, read_href_modifier)
        item.geometry = ang_metadata.get_scene_geometry(mtl_metadata.bbox)

    return item
