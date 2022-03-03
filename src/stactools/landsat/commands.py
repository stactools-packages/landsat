import os

import click
from click import Command, Group
from pystac import Item

from stactools.landsat.stac import create_stac_item
from stactools.landsat.utils import transform_stac_to_stac


def create_landsat_command(cli: Group) -> Command:
    """Creates a command group for commands working with the USGS' Landsat
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
        short_help="Create a STAC item from Collection 2 scene metadata.")
    @click.option("--mtl",
                  required=True,
                  help="HREF to the source MTL metadata xml file")
    @click.option("--output",
                  required=True,
                  help="HREF of directory in which to write the item.")
    @click.option("--usgs_geometry",
                  default=False,
                  show_default=True,
                  help="Use USGS STAC Item geometry")
    def create_item_cmd(mtl: str, output: str, usgs_geometry: bool) -> None:
        """\b
        Creates a STAC Item for a Landsat Collection 2 scene based on metadata
        from a Landsat MTL xml file. The following Landsat processing Levels and
        sensors are supported:
            Level-1
                - Landsat 1-5 Multi Spectral Scanner (MSS)
            Level-2
                - Landat 4-5 Thematic Mapper (TM)
                - Landsat 7 Enhanced Thematic Mapper (ETM)
                - Landsat 8-9 Operational Land Imager - Thermal Infrared Sensor
                  (OLI-TIRS)

        All assets (COGs, metadata files) must reside in the same directory /
        blob prefix / etc. as the MTL xml metadata file.

        \b
        Args:
            mtl (str): HREF to the source MTL metadata xml file
            output (str): Directory that will contain the STAC Item
            usgs_geometry (bool, optional): Use the geometry from a USGS STAC
                Item that resides in the same directory as the MTL xml file or
                can be queried from the USGS STAC API.
        """
        item = create_stac_item(mtl_xml_href=mtl,
                                use_usgs_geometry=usgs_geometry)
        item.set_self_href(os.path.join(output, f'{item.id}.json'))
        item.save_object()

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
            enable_proj (flag): Include the proj extension in the created STAC
                Item
        """
        in_item = Item.from_file(stac)
        item = transform_stac_to_stac(in_item, enable_proj=enable_proj)

        item_path = os.path.join(dst, '{}.json'.format(item.id))
        item.set_self_href(item_path)
        item.save_object()

    return landsat
