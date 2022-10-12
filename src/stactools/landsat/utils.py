import datetime
from typing import Any, Dict, Optional

import dateutil.parser
import rasterio
import shapely.affinity
import shapely.ops
from pystac import Item, Link, MediaType, STACError
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
from pystac_client import Client
from rasterio import RasterioIOError
from shapely.geometry import MultiPolygon, Polygon, box, mapping, shape
from stactools.core.io import ReadHrefModifier
from stactools.core.utils import antimeridian, href_exists
from stactools.core.utils.antimeridian import Strategy

from stactools.landsat.constants import (L8_EXTENSION_SCHEMA,
                                         OLD_L8_EXTENSION_SCHEMA, USGS_API,
                                         USGS_C2L1, USGS_C2L2_SR, Sensor)


def _parse_date(in_date: str) -> datetime.datetime:
    """
    Try to parse a date and return it as a datetime object with no timezone
    """
    parsed_date = dateutil.parser.parse(in_date)
    return parsed_date.replace(tzinfo=datetime.timezone.utc)


def transform_mtl_to_stac(metadata: dict) -> Item:
    """
    Handle USGS MTL as a dict and return a STAC item.

    NOT IMPLEMENTED

    Issues include:
        - There's no reference to UTM Zone or any other CRS info in the MTL
        - There's no absolute file path or reference to a URI to find data.
    """
    LANDSAT_METADATA = metadata["LANDSAT_METADATA_FILE"]
    product = LANDSAT_METADATA["PRODUCT_CONTENTS"]
    projection = LANDSAT_METADATA["PROJECTION_ATTRIBUTES"]
    image = LANDSAT_METADATA["IMAGE_ATTRIBUTES"]
    proessing_record = LANDSAT_METADATA["LEVEL2_PROCESSING_RECORD"]

    scene_id = product["LANDSAT_PRODUCT_ID"]

    xmin, xmax = float(projection["CORNER_LL_LON_PRODUCT"]), float(
        projection["CORNER_UR_LON_PRODUCT"])
    ymin, ymax = float(projection["CORNER_LL_LAT_PRODUCT"]), float(
        projection["CORNER_UR_LAT_PRODUCT"])
    geom = mapping(box(xmin, ymin, xmax, ymax))
    bounds = shape(geom).bounds

    # Like: "2020-01-01" for date and  "23:08:52.6773140Z" for time
    acquired_date = _parse_date(
        f"{image['DATE_ACQUIRED']}T{image['SCENE_CENTER_TIME']}")
    created = _parse_date(proessing_record["DATE_PRODUCT_GENERATED"])

    item = Item(id=scene_id,
                geometry=geom,
                bbox=bounds,
                datetime=acquired_date,
                properties={})

    # Common metadata
    item.common_metadata.created = created
    item.common_metadata.platform = image["SPACECRAFT_ID"]
    item.common_metadata.instruments = [
        i.lower() for i in image["SENSOR_ID"].split("_")
    ]

    # TODO: implement these three extensions
    EOExtension.add_to(item)
    ViewExtension.add_to(item)
    ProjectionExtension.add_to(item)

    return item


def transform_stac_to_stac(item: Item,
                           enable_proj: bool = True,
                           self_link: str = None,
                           source_link: str = None) -> Item:
    """
    Handle a 0.7.0 item and convert it to a 1.0.0.beta2 item.
    If `enable_proj` is true, the assets' geotiff files must be accessible.
    """
    # Clear hierarchical links
    item.set_parent(None)
    item.set_root(None)

    # Remove USGS extension and add back eo
    EOExtension.add_to(item)

    # Add and update links
    if self_link:
        item.links.append(Link(rel="self", target=self_link))
    if source_link:
        item.links.append(
            Link(rel="derived_from",
                 target=source_link,
                 media_type="application/json"))

    # Add some common fields
    item.common_metadata.constellation = "Landsat"

    # Handle view extension
    view = ViewExtension.ext(item, add_if_missing=True)
    if (item.properties.get("eo:off_nadir")
            or item.properties.get("eo:off_nadir") == 0):
        view.off_nadir = item.properties.pop("eo:off_nadir")
    elif (item.properties.get("view:off_nadir")
          or item.properties.get("view:off_nadir") == 0):
        view.off_nadir = item.properties.pop("view:off_nadir")
    else:
        STACError("eo:off_nadir or view:off_nadir is a required property")

    if enable_proj:
        # Enabled projection
        projection = ProjectionExtension.ext(item, add_if_missing=True)

        obtained_shape = None
        obtained_transform = None
        crs = None
        for asset in item.assets.values():
            if asset.media_type is not None and "geotiff" in asset.media_type:
                # retrieve shape, transform and crs from the first geotiff file among the assets
                if not obtained_shape:
                    try:
                        with rasterio.open(asset.href) as opened_asset:
                            obtained_shape = opened_asset.shape
                            obtained_transform = opened_asset.transform
                            crs = opened_asset.crs.to_epsg()
                            # Check to ensure that all information is present
                            if not obtained_shape or not obtained_transform or not crs:
                                raise STACError(
                                    f"Failed setting shape, transform and csr from {asset.href}"
                                )

                    except RasterioIOError as io_error:
                        raise STACError(
                            "Failed loading geotiff, so not handling proj fields"
                        ) from io_error

                asset_projection = ProjectionExtension.ext(asset)
                asset_projection.transform = obtained_transform
                asset_projection.shape = obtained_shape
                asset.media_type = MediaType.COG

        # Now we have the info, we can make the fields
        projection.epsg = crs

    # Remove .TIF from asset names
    item.assets = {
        name.replace(".TIF", ""): asset
        for name, asset in item.assets.items()
    }

    try:
        index = item.stac_extensions.index(OLD_L8_EXTENSION_SCHEMA)
        item.stac_extensions[index] = L8_EXTENSION_SCHEMA
    except ValueError:
        pass

    return item


def stac_api_to_stac(uri: str) -> Item:
    """
    Takes in a URI and uses that to feed the STAC transform
    """

    return transform_stac_to_stac(item=Item.from_file(uri),
                                  source_link=uri,
                                  enable_proj=False)


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
            item = next(search.items())
        else:
            item = None

    if item is not None:
        return item.geometry
    else:
        return None


def handle_antimeridian(item: Item, antimeridian_strategy: Strategy) -> None:
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

    antimeridian.fix_item(item, antimeridian_strategy)
