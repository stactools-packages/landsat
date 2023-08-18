from pathlib import Path

import pystac
import pytest
from antimeridian import FixWindingWarning
from click import Group
from click.testing import CliRunner

from stactools.landsat.commands import create_landsat_command
from tests import test_data


def test_create_item(tmp_path: Path) -> None:
    infile = test_data.get_path(
        "data-files/assets4/LC08_L2SP_017036_20130419_20200913_02_T2_MTL.xml"
    )
    runner = CliRunner()
    with pytest.warns(FixWindingWarning):
        runner.invoke(
            create_landsat_command(Group()),
            [
                "create-item",
                "--mtl",
                infile,
                "--output",
                str(tmp_path),
                "--usgs_geometry",
            ],
        )
    item = pystac.read_file(str(tmp_path / "LC08_L2SP_017036_20130419_02_T2.json"))
    item.validate()
