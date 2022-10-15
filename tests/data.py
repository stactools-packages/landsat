from tests import test_data

TEST_GEOMETRY_PATHS = {
    "stac_in_storage": test_data.get_path(
        "data-files/assets2/LC08_L2SR_099120_20191129_20201016_02_T2_MTL.xml"
    ),
    "stac_not_in_storage": test_data.get_path(
        "data-files/assets5/LC08_L2SP_047027_20201204_20210313_02_T1_MTL.xml"
    ),
    "vcr_cassette": test_data.get_path("fixtures/usgs_stac_api.yml"),
    "antimeridian": test_data.get_path(
        "data-files/oli-tirs/LC08_L2SR_084024_20160111_20201016_02_T1_MTL.xml"
    ),
    "presplit_antimeridian": test_data.get_path(
        "data-files/tm/LT05_L2SR_087017_20090621_20200827_02_T2_MTL.xml"
    ),
}
