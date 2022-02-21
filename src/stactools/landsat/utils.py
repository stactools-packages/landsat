from pystac import Item, Link, MediaType, STACError
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.view import ViewExtension
import rasterio
from rasterio import RasterioIOError

from stactools.landsat.constants import OLD_L8_EXTENSION_SCHEMA, L8_EXTENSION_SCHEMA


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
            if "geotiff" in asset.media_type:
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
