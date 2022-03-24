import os

import click
from click import Command, Group
from pystac import CatalogType, Item
from stactools.core.utils.antimeridian import Strategy

from stactools.landsat.stac import create_collection, create_stac_item
from stactools.landsat.utils import transform_stac_to_stac


def create_landsat_command(cli: Group) -> Command:
    """Creates a command group for commands working with the USGS's Landsat
    Collection 2 metadata.
    """

    @cli.group(
        'landsat',
        short_help=("Commands for working with Landsat Collection 2 metadata.")
    )
    def landsat() -> None:
        pass

    @landsat.command(
        "create-item",
        short_help=(
            "Creates a STAC Item from Landsat Collection 2 scene metadata."))
    @click.option("-m",
                  "--mtl",
                  required=True,
                  help="HREF to the source MTL metadata xml file.")
    @click.option("-o",
                  "--output",
                  required=True,
                  help="HREF of directory in which to write the item.")
    @click.option("-u",
                  "--usgs_geometry",
                  is_flag=True,
                  help="Use USGS STAC Item geometry")
    @click.option("-l",
                  "--legacy_l8",
                  is_flag=True,
                  help="Create legacy Landsat 8 STAC Item")
    @click.option("-a",
                  "--antimeridian_strategy",
                  type=click.Choice(["normalize", "split"],
                                    case_sensitive=False),
                  default="split",
                  show_default=True,
                  help="geometry strategy for antimeridian scenes")
    @click.option("--level",
                  type=click.Choice(['level-1', 'level-2'],
                                    case_sensitive=False),
                  default="level-2",
                  show_default=True,
                  help="Product level to process. Unused.")
    def create_item_cmd(level: str, mtl: str, output: str, usgs_geometry: bool,
                        legacy_l8: bool, antimeridian_strategy: str) -> None:
        """\b
        Creates a STAC Item for a Landsat Collection 2 scene based on metadata
        from a Landsat MTL xml file.

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

        All assets (COGs, metadata files) must reside in the same
        directory/blob prefix/etc. as the MTL xml metadata file.

        \b
        Args:
            mtl (str): HREF to the source MTL metadata xml file
            output (str): Directory that will contain the STAC Item
            usgs_geometry (bool): Flag to use the geometry from a USGS STAC Item
                that resides in the same directory as the MTL xml file or can be
                queried from the USGS STAC API.
            legacy_l8 (bool): Flag to use the legacy method for creating a
                Landsat 8 STAC Item.
            antimeridian_strategy (str): Choice of 'normalize' or 'split' to
                either split the Item geometry on -180 longitude or normalize
                the Item geometry so all longitudes are either positive or
                negative. Has no effect if legacy_l8=True.
            level (str): Choice of 'level-1' or 'level-2'. This is not used
                and has no effect.
        """
        strategy = Strategy[antimeridian_strategy.upper()]
        item = create_stac_item(mtl_xml_href=mtl,
                                use_usgs_geometry=usgs_geometry,
                                legacy_l8=legacy_l8,
                                antimeridian_strategy=strategy)
        item.set_self_href(os.path.join(output, f'{item.id}.json'))
        item.save_object()

    @landsat.command(
        "create-collection",
        short_help="Creates a STAC Collection with contents defined by a list "
        " of metadata file hrefs in a text file.")
    @click.option("-f",
                  "--file_list",
                  required=True,
                  help="Text file of HREFs to Landsat scene XML MTL metadata "
                  "files.")
    @click.option("-o",
                  "--output",
                  required=True,
                  help="HREF of directory in which to write the collection.")
    @click.option("-i",
                  "--id",
                  type=click.Choice(['landsat-c2-l1', 'landsat-c2-l2'],
                                    case_sensitive=True),
                  required=True,
                  help="Landsat collection type. Choice of 'landsat-c2-l1' "
                  "'landsat-c2-l2'")
    @click.option("-u",
                  "--usgs_geometry",
                  is_flag=True,
                  help="Use USGS STAC Item geometry")
    @click.option("-a",
                  "--antimeridian_strategy",
                  type=click.Choice(["normalize", "split"],
                                    case_sensitive=False),
                  default="split",
                  show_default=True,
                  help="geometry strategy for antimeridian scenes")
    def create_collection_cmd(file_list: str, output: str, id: str,
                              usgs_geometry: bool,
                              antimeridian_strategy: str) -> None:
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
        with open(file_list) as file:
            hrefs = [line.strip() for line in file.readlines()]

        collection = create_collection(id)
        collection.set_self_href(os.path.join(output, "collection.json"))
        collection.catalog_type = CatalogType.SELF_CONTAINED
        for href in hrefs:
            item = create_stac_item(href,
                                    use_usgs_geometry=usgs_geometry,
                                    legacy_l8=False,
                                    antimeridian_strategy=strategy)
            collection.add_item(item)
        collection.make_all_asset_hrefs_relative()
        collection.validate_all()
        collection.save()

    @landsat.command(
        "convert",
        short_help="Convert a USGS STAC 0.7.0 Item to an updated STAC Item")
    @click.option("-s",
                  "--stac",
                  required=True,
                  help="HREF to the source STAC file.")
    @click.option(
        "-p",
        "--enable-proj",
        is_flag=True,
        help="Enable the proj extension. Requires access to blue band.")
    @click.option("-d", "--dst", help="Output directory")
    def convert_cmd(stac: str, enable_proj: bool, dst: str) -> None:
        """Converts a USGS STAC 0.7.0 Item to an updated STAC Item.

        \b
        Args:
            stac (str): href to the source STAC file
            dst (str): Directory that will contain the STAC Item
            enable_proj: Flag to include the proj extension in the created STAC
                Item
        """
        in_item = Item.from_file(stac)
        item = transform_stac_to_stac(in_item, enable_proj=enable_proj)

        item_path = os.path.join(dst, '{}.json'.format(item.id))
        item.set_self_href(item_path)
        item.save_object()

    return landsat
