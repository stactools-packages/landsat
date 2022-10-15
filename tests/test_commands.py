import os.path
from tempfile import TemporaryDirectory
from typing import Callable, List

import pystac
from click import Command, Group
from stactools.testing.cli_test import CliTestCase

from stactools.landsat.commands import create_landsat_command
from tests import test_data


class LandsatTest(CliTestCase):
    def create_subcommand_functions(self) -> List[Callable[[Group], Command]]:
        return [create_landsat_command]

    def test_create_item(self) -> None:
        infile = test_data.get_path(
            "data-files/assets4/LC08_L2SP_017036_20130419_20200913_02_T2_MTL.xml"
        )

        with TemporaryDirectory() as temp_dir:
            cmd = (
                f"landsat create-item --mtl {infile} --output {temp_dir} "
                f"--usgs_geometry"
            )
            self.run_command(cmd)
            item_path = os.path.join(temp_dir, "LC08_L2SP_017036_20130419_02_T2.json")
            item = pystac.read_file(item_path)
        item.validate()
