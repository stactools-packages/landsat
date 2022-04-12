import logging
from datetime import datetime, timezone
from typing import Optional

from pystac import Collection, Item, Link, MediaType
from pystac.extensions.eo import Band, EOExtension
from pystac.extensions.item_assets import ItemAssetsExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension
from pystac.extensions.scientific import ScientificExtension
from pystac.extensions.view import ViewExtension
from shapely.geometry import box, mapping
from stactools.core.io import ReadHrefModifier
from stactools.core.utils.antimeridian import Strategy

from stactools.landsat.ang_metadata import AngMetadata
from stactools.landsat.assets import (ANG_ASSET_DEF, COMMON_ASSET_DEFS,
                                      SR_ASSET_DEFS, THERMAL_ASSET_DEFS)
from stactools.landsat.constants import Sensor  # yapf: disable
from stactools.landsat.constants import (CLASSIFICATION_EXTENSION_SCHEMA,
                                         COLLECTION_IDS, L8_EXTENSION_SCHEMA,
                                         L8_INSTRUMENTS, L8_ITEM_DESCRIPTION,
                                         L8_PLATFORM, LANDSAT_EXTENSION_SCHEMA,
                                         SENSORS, USGS_API, USGS_BROWSER_C2,
                                         USGS_C2L1, USGS_C2L2_SR, USGS_C2L2_ST)
from stactools.landsat.fragments import CollectionFragments, Fragments
from stactools.landsat.mtl_metadata import MtlMetadata
from stactools.landsat.utils import get_usgs_geometry, handle_antimeridian

logger = logging.getLogger(__name__)


def create_stac_item(
        mtl_xml_href: str,
        legacy_l8: bool = True,
        use_usgs_geometry: bool = False,
        antimeridian_strategy: Strategy = Strategy.SPLIT,
        read_href_modifier: Optional[ReadHrefModifier] = None) -> Item:
    """Creates a STAC Item for Landsat 1-5 Collection 2 Level-1 or Landsat
    4-5, 7-9 Collection 2 Level-2 scene data.

    Args:
        mtl_xml_href (str): An href to an MTL XML metadata file.
        legacy_l8 (bool): Use the legacy (old) method for a Landsat 8 STAC Item.
        use_usgs_geometry (bool): Use the geometry from a USGS STAC file that is
            stored alongside the XML metadata file or pulled from the USGS STAC
            API.
        antimeridian_strategy (Antimeridian): Either split on -180 or
            normalize geometries so all longitudes are either positive or
            negative. Has no effect if legacy_l8=True.
        read_href_modifier (Callable[[str], str]): An optional function to
            modify the MTL and USGS STAC hrefs (e.g. to add a token to a url).
    Returns:
        pystac.Item: A STAC Item representing the Landsat scene.
    """
    base_href = '_'.join(mtl_xml_href.split('_')[:-1])

    mtl_metadata = MtlMetadata.from_file(mtl_xml_href,
                                         read_href_modifier,
                                         legacy_l8=legacy_l8)

    sensor = Sensor(mtl_metadata.item_id[1])
    satellite = int(mtl_metadata.item_id[2:4])
    level = int(mtl_metadata.item_id[6])
    correction = mtl_metadata.item_id[7:9]

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

    if satellite == 8 and legacy_l8:
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
        # with product_id to fix).
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
        handle_antimeridian(item, antimeridian_strategy)

        item.common_metadata.platform = f"landsat-{satellite}"
        item.common_metadata.instruments = SENSORS[sensor.name]["instruments"]
        item.common_metadata.created = datetime.now(tz=timezone.utc)
        item.common_metadata.gsd = SENSORS[sensor.name]["reflective_gsd"]
        item.common_metadata.description = f"Landsat Collection 2 Level-{level}"

        fragments = Fragments(sensor, satellite, base_href,
                              mtl_metadata.level1_radiance)

        # Common assets
        assets = fragments.common_assets()
        for key, asset in assets.items():
            # MSS data does not have an angle file
            if sensor is Sensor.MSS and key.startswith("ang"):
                continue
            # MTL files are specific to the processing level
            if key.startswith("mtl"):
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
                if key.startswith("lwir"):
                    asset.common_metadata.gsd = SENSORS[
                        sensor.name]["thermal_gsd"]

        if mtl_metadata.cloud_cover >= 0:
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

        item.stac_extensions.append(LANDSAT_EXTENSION_SCHEMA)
        item.properties.update(**mtl_metadata.landsat_metadata)

        item.stac_extensions.append(CLASSIFICATION_EXTENSION_SCHEMA)

        scientific = ScientificExtension.ext(item, add_if_missing=True)
        scientific.doi = SENSORS[sensor.name]["doi"]
        doi_link = item.get_single_link("cite-as")
        doi_link.title = SENSORS[sensor.name]["doi_title"]  # type: ignore

        via_links = []
        if level == 1:
            via_links.append(
                f"{USGS_API}/collections/{USGS_C2L1}/items/{mtl_metadata.product_id}"
            )
        elif level == 2 and correction == "SP":
            via_links.append(
                f"{USGS_API}/collections/{USGS_C2L2_SR}/items/{mtl_metadata.product_id}_SR"
            )
            via_links.append(
                f"{USGS_API}/collections/{USGS_C2L2_ST}/items/{mtl_metadata.product_id}_ST"
            )
        elif level == 2 and correction == "SR":
            via_links.append(
                f"{USGS_API}/collections/{USGS_C2L2_SR}/items/{mtl_metadata.product_id}_SR"
            )
        for via_link in via_links:
            item.add_link(
                Link(rel="via",
                     target=via_link,
                     title="USGS STAC Item",
                     media_type=MediaType.JSON))

    return item


def create_collection(collection_id: str) -> Collection:
    """Creates a STAC Collection for Landsat Collection 2 Level-1 or Level-2
    data.

    Args:
        collection_id (str): ID of the STAC Collection. Must be one of
            "landsat-c2-l1" or "landsat-c2-l2".
    Returns:
        Collection: The created STAC Collection.
    """
    if collection_id not in COLLECTION_IDS:
        raise ValueError(f"Invalid collection id: {collection_id}")

    fragment = CollectionFragments(collection_id).collection()

    collection = Collection(id=collection_id,
                            title=fragment["title"],
                            description=fragment["description"],
                            license=fragment["license"],
                            keywords=fragment["keywords"],
                            providers=fragment["providers"],
                            extent=fragment["extent"],
                            summaries=fragment["summaries"])
    collection.add_links(fragment["links"])

    item_assets = ItemAssetsExtension(collection)
    item_assets.item_assets = fragment["item_assets"]

    ItemAssetsExtension.add_to(collection)
    ViewExtension.add_to(collection)
    ScientificExtension.add_to(collection)
    RasterExtension.add_to(collection)
    EOExtension.add_to(collection)

    return collection
