import os

import click
from click import Command, Group
from pystac import CatalogType
from stactools.core.utils.antimeridian import Strategy

from stactools.landsat.stac import create_collection, create_item
from stactools.landsat.constants import GeometrySource


def create_landsat_command(cli: Group) -> Command:
    """Creates a command group for commands working with the USGS's Landsat
    Collection 2 metadata.
    """

    @cli.group(
        "landsat",
        short_help=("Commands for working with Landsat Collection 2 metadata."),
    )
    def landsat() -> None:
        pass

    @landsat.command(
        "create-item",
        short_help=("Creates a STAC Item from Landsat Collection 2 scene metadata."),
    )
    @click.argument("infile")
    @click.argument("destination")
    @click.argument(
        "geometry",
        type=click.Choice(
            [source.name for source in GeometrySource], case_sensitive=False
        ),
    )
    @click.option(
        "-n",
        "--asset-name",
        type=str,
        help="Asset name in created Item to use for data footprint geometry computation",
    )
    @click.option(
        "-a",
        "--antimeridian-strategy",
        type=click.Choice(["normalize", "split"], case_sensitive=False),
        default="split",
        show_default=True,
        help="geometry strategy for antimeridian scenes",
    )
    def create_item_cmd(
        infile: str,
        destination: str,
        geometry: str,
        asset_name: str,
        antimeridian_strategy: str,
    ) -> None:
        """\b
        Creates a STAC Item for a Landsat Collection 2 scene based on metadata
        from a Landsat MTL XML metadata file.

        \b
        The following Landsat Collection 2 processing Levels and sensors are
        supported:
            Level-1
                - Landsat 1-5 Multi Spectral Scanner (MSS)
            Level-2
                - Landat 4-5 Thematic Mapper (TM)
                - Landsat 7 Enhanced Thematic Mapper Plus (ETM+)
                - Landsat 8-9 Operational Land Imager - Thermal Infrared Sensor
                  (OLI-TIRS)

        \b
        Args:
            infile (str): HREF to the source MTL metadata xml file.
            destination (str): Directory that will contain the STAC Item.
            geometry (str): Method to use for Item geometry creation. One of
                'usgs', 'footprint', 'ang', or 'bbox'.
            asset_name (str): Name of asset in created Item that should be used
                for generating geometry from a raster data footprint. This option
                only has effect when 'footprint' is specified for the geometry
                argument.
            antimeridian_strategy (str): Choice of 'normalize' or 'split' to
                either split the Item geometry on -180 longitude or normalize
                the Item geometry so all longitudes are either positive or
                negative.
        """
        strategy = Strategy[antimeridian_strategy.upper()]
        geometry_source = GeometrySource[geometry.upper()]
        item = create_item(
            mtl_xml_href=infile,
            geometry_source=geometry_source,
            footprint_asset_name=asset_name,
            antimeridian_strategy=strategy,
        )
        item.set_self_href(os.path.join(destination, f"{item.id}.json"))
        item.save_object()

    @landsat.command(
        "create-collection",
        short_help="Creates a STAC Collection with contents defined by a list "
        " of metadata file hrefs in a text file.",
    )
    @click.argument("infile")
    @click.argument("destination")
    @click.argument(
        "collection",
        type=click.Choice(["landsat-c2-l1", "landsat-c2-l2"], case_sensitive=False),
    )
    @click.argument(
        "geometry",
        type=click.Choice(
            [source.name for source in GeometrySource], case_sensitive=False
        ),
    )
    @click.option(
        "-n",
        "--asset-name",
        type=str,
        help="Asset name in created Item to use for data footprint geometry computation",
    )
    @click.option(
        "-a",
        "--antimeridian-strategy",
        type=click.Choice(["normalize", "split"], case_sensitive=False),
        default="split",
        show_default=True,
        help="geometry strategy for antimeridian scenes",
    )
    def create_collection_cmd(
        infile: str,
        destination: str,
        collection: str,
        geometry: bool,
        asset_name: str,
        antimeridian_strategy: str,
    ) -> None:
        """\b
        Creates a STAC Collection for Items defined by the hrefs in file_list.

        \b
        Args:
            file_list (str): Text file containing one href per line. The hrefs
                should point to XML MTL metadata files.
            output (str): Directory that will contain the collection.
            id (str): Choice of 'landsat-c2-l1' or 'landsat-c2-l2'.
            usgs_geometry (bool): Flag to use the geometry from a USGS STAC Item
                that resides in the same directory as the MTL xml file or can be
                queried from the USGS STAC API.
            antimeridian_strategy (str): Choice of 'normalize' or 'split' to
                either split the Item geometry on -180 longitude or normalize
                the Item geometry so all longitudes are either positive or
                negative.
        """
        strategy = Strategy[antimeridian_strategy.upper()]
        collection_id = collection.lower()
        with open(infile) as file:
            hrefs = [line.strip() for line in file.readlines()]

        collection = create_collection(collection_id)
        collection.set_self_href(os.path.join(destination, "collection.json"))
        collection.catalog_type = CatalogType.SELF_CONTAINED
        for href in hrefs:
            item = create_item(
                mtl_xml_href=href,
                geometry_source=geometry,
                footprint_asset_name=asset_name,
                antimeridian_strategy=strategy,
            )
            collection.add_item(item)
        collection.make_all_asset_hrefs_relative()
        collection.validate_all()
        collection.save()

    return landsat
