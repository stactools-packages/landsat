import pytest
from antimeridian import FixWindingWarning
from pystac.extensions.grid import GridExtension

from stactools.landsat.stac import create_item, create_item_from_mtl_text
from tests import test_data


def test_item() -> None:
    mtl_path = test_data.get_path(
        "data-files/assets4/LC08_L2SP_017036_20130419_20200913_02_T2_MTL.xml"
    )
    with pytest.warns(FixWindingWarning):
        item = create_item(mtl_path)

    # v1.1.1 landsat extension
    ext = "https://landsat.usgs.gov/stac/landsat-extension/v1.1.1/schema.json"
    assert ext in item.stac_extensions

    # grid extension

    grid = GridExtension.ext(item)
    assert grid.code == "WRS2-017036"
    assert (
        grid.code == f"WRS{item.properties['landsat:wrs_type']}-"
        f"{item.properties['landsat:wrs_path']}{item.properties['landsat:wrs_row']}"
    )

    # non-zero roll handled
    assert item.to_dict()["properties"]["view:off_nadir"] != 0

    # doi link
    assert len(item.get_links("cite-as")) == 1

    # via link(s) to usgs stac-server
    usgs_stac_links = item.get_links(rel="via")
    assert len(usgs_stac_links) > 0

    item.validate()


def test_read_href_modifier() -> None:
    mtl_path = test_data.get_path(
        "data-files/assets4/LC08_L2SP_017036_20130419_20200913_02_T2_MTL.xml"
    )

    did_it = False

    def read_href_modifier(href: str) -> str:
        nonlocal did_it
        did_it = True
        return href

    with pytest.warns(FixWindingWarning):
        _ = create_item(mtl_path, read_href_modifier=read_href_modifier)
    assert did_it


def test_southern_hemisphere_epsg() -> None:
    mtl_path = test_data.get_path(
        "data-files/tm/LT05_L2SP_010067_19860424_20200918_02_T2_MTL.xml"
    )
    item = create_item(mtl_path, use_usgs_geometry=True)
    item_dict = item.to_dict()

    # northern hemisphere UTM zone is used for southern hemisphere scene
    assert item_dict["properties"]["proj:epsg"] == 32617


def test_mss_scale_offset() -> None:
    mtl_path = test_data.get_path(
        "data-files/mss/LM01_L1GS_001010_19720908_20200909_02_T2_MTL.xml"
    )
    item = create_item(mtl_path, use_usgs_geometry=True)
    item_dict = item.to_dict()

    # MSS should grab scale and offset values (to convert DN to TOA radiance)
    # for the optical data bands from the MTL metadata
    asset_keys = ["green", "red", "nir08", "nir09"]
    for key in asset_keys:
        raster_bands = item_dict["assets"][key]["raster:bands"][0]
        assert "scale" in raster_bands
        assert "offset" in raster_bands


def test_mss_null_scale_offset() -> None:
    mtl_path = test_data.get_path(
        "data-files/mss/LM01_L1GS_007019_19771009_20200907_02_T2_MTL.xml"
    )
    item = create_item(mtl_path, use_usgs_geometry=True)
    item.validate()

    item_dict = item.to_dict()
    # Check that unit, scale, and offset do not exist in the band with null
    # values for scale and/or offset
    raster_bands = item_dict["assets"]["green"]["raster:bands"][0]
    assert "unit" not in raster_bands
    assert "scale" not in raster_bands
    assert "offset" not in raster_bands

    # Check that unit, scale, and offset do exist in other bands
    asset_keys = ["red", "nir08", "nir09"]
    for key in asset_keys:
        raster_bands = item_dict["assets"][key]["raster:bands"][0]
        assert "unit" in raster_bands
        assert "scale" in raster_bands
        assert "offset" in raster_bands


def test_l1_bitfields_exist() -> None:
    mtl_path = test_data.get_path(
        "data-files/mss/LM01_L1GS_001010_19720908_20200909_02_T2_MTL.xml"
    )
    item = create_item(mtl_path, use_usgs_geometry=True)
    item_dict = item.to_dict()

    qa_pixel = item_dict["assets"]["qa_pixel"]
    assert "classification:bitfields" in qa_pixel


def test_l2_bitfields_exist() -> None:
    mtl_path = test_data.get_path(
        "data-files/oli-tirs/LC08_L2SP_047027_20201204_20210313_02_T1_MTL.xml"
    )
    with pytest.warns(FixWindingWarning):
        item = create_item(mtl_path, use_usgs_geometry=True)
    item_dict = item.to_dict()

    asset_keys = ["qa_pixel", "qa_radsat", "qa_aerosol"]
    for key in asset_keys:
        bitfield_band = item_dict["assets"][key]
        assert "classification:bitfields" in bitfield_band


def test_no_cloud_cover() -> None:
    mtl_path = test_data.get_path(
        "data-files/mss/LM01_L1GS_005037_19720823_20200909_02_T2_MTL.xml"
    )
    item = create_item(mtl_path, use_usgs_geometry=True)
    item.validate()

    # When cloud cover percentage is not computed (assigned a value of -1), the
    # eo:cloud_cover property should not exist
    eo_cloud_cover = item.properties.pop("eo:cloud_cover", None)
    assert eo_cloud_cover is None


def test_no_emis_coefficient() -> None:
    mtl_path = test_data.get_path(
        "data-files/oli-tirs/LC08_L2SP_047027_20201204_20210313_02_T1_MTL.xml"
    )
    with pytest.warns(FixWindingWarning):
        item = create_item(mtl_path, use_usgs_geometry=True)
    item_dict = item.to_dict()
    assert "emissivity" in item_dict["assets"]["emis"]["roles"]
    assert "emissivity" in item_dict["assets"]["emsd"]["roles"]
    assert item_dict["assets"]["emis"]["raster:bands"][0].pop("unit", None) is None
    assert item_dict["assets"]["emsd"]["raster:bands"][0].pop("unit", None) is None


def test_mtl_text() -> None:
    mtl_path = test_data.get_path(
        "data-files/oli-tirs/LC08_L2SP_047027_20201204_20210313_02_T1_MTL.txt"
    )
    with pytest.warns(FixWindingWarning):
        item = create_item_from_mtl_text(mtl_path, use_usgs_geometry=True)
    item_dict = item.to_dict()

    asset_keys = ["qa_pixel", "qa_radsat", "qa_aerosol"]
    for key in asset_keys:
        bitfield_band = item_dict["assets"][key]
        assert "classification:bitfields" in bitfield_band
