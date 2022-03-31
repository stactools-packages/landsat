import os
from tempfile import TemporaryDirectory

import pystac
import rasterio
from pystac.extensions.eo import EOExtension
from pystac.extensions.projection import ProjectionExtension
from pystac.utils import is_absolute_href
from shapely.geometry import box, mapping, shape
from stactools.core.projection import reproject_geom
from stactools.testing import CliTestCase

from stactools.landsat.assets import (SR_ASSET_DEFS, ST_B10_ASSET_DEF,
                                      THERMAL_ASSET_DEFS)
from stactools.landsat.commands import create_landsat_command
from stactools.landsat.constants import L8_SP_BANDS, L8_SR_BANDS
from stactools.landsat.stac import create_stac_item
from tests import test_data
from tests.data import TEST_MTL_PATHS


class CreateItemTest(CliTestCase):

    def create_subcommand_functions(self):
        return [create_landsat_command]

    def test_create_item(self):

        def check_proj_bbox(item, tif_bounds):
            bbox = item.bbox
            bbox_shp = box(*bbox)
            projection = ProjectionExtension.ext(item)
            proj_bbox = projection.bbox
            assert proj_bbox is not None
            self.assertEqual(proj_bbox, list(tif_bounds))
            proj_bbox_shp = box(*proj_bbox)
            reproj_bbox_shp = shape(
                reproject_geom(f"epsg:{projection.epsg}", "epsg:4326",
                               mapping(proj_bbox_shp)))

            self.assertLess((reproj_bbox_shp - bbox_shp).area,
                            0.0001 * reproj_bbox_shp.area)

        for item_id, mtl_path in TEST_MTL_PATHS.items():
            with self.subTest(mtl_path):
                base_path = "_".join(mtl_path.split("_")[:-1])
                tif_path = f"{base_path}_SR_B3.TIF"
                with rasterio.open(tif_path) as dataset:
                    tif_bounds = dataset.bounds
                with TemporaryDirectory() as tmp_dir:
                    cmd = [
                        'landsat', 'create-item', '--mtl', mtl_path,
                        '--output', tmp_dir, '--legacy_l8'
                    ]
                    self.run_command(cmd)

                    jsons = [
                        p for p in os.listdir(tmp_dir) if p.endswith('.json')
                    ]
                    self.assertEqual(len(jsons), 1)
                    fname = jsons[0]

                    item = pystac.Item.from_file(os.path.join(tmp_dir, fname))
                    # This is a hack to get validation working, since v1.1.0 of
                    # the landsat schema lists "collection" as a required
                    # property.
                    item.collection_id = "landsat-8-c2-l2"
                    item.links.append(
                        pystac.Link(rel="collection",
                                    target="http://example.com"))
                    item.validate()
                    self.assertEqual(item.id, item_id)

                    # Ensure gsd is not set on the Item,
                    # as it's set on the asset level

                    # Ensure gsd is correctly set for band 10
                    if ST_B10_ASSET_DEF.key in item.assets:
                        self.assertIn(
                            'gsd',
                            item.assets[ST_B10_ASSET_DEF.key].extra_fields)
                        self.assertEqual(
                            item.assets[
                                ST_B10_ASSET_DEF.key].extra_fields['gsd'],
                            100.0)

                    bands_seen = set()

                    for asset in item.assets.values():
                        self.assertTrue(is_absolute_href(asset.href))
                        eo = EOExtension.ext(asset)

                        if eo.bands is not None:
                            bands_seen |= set(b.name for b in eo.bands)

                            # Ensure gsd is set
                            self.assertIn('gsd', asset.extra_fields)

                    if item.properties['landsat:processing_level'] == 'L2SP':
                        self.assertEqual(
                            bands_seen,
                            set(L8_SR_BANDS.keys()) | set(L8_SP_BANDS.keys()))
                    else:
                        self.assertEqual(bands_seen, set(L8_SR_BANDS.keys()))

                    check_proj_bbox(item, tif_bounds)

    def test_convert_and_create_agree(self):

        def get_item(output_dir: str) -> pystac.Item:
            jsons = [p for p in os.listdir(output_dir) if p.endswith('.json')]
            self.assertEqual(len(jsons), 1)

            fname = jsons[0]
            item = pystac.Item.from_file(os.path.join(output_dir, fname))
            # This is a hack to get validation working, since v1.1.0 of the
            # landsat schema lists "collection" as a required property.
            item.collection_id = "landsat-8-c2-l2"
            item.links.append(
                pystac.Link(rel="collection", target="http://example.com"))
            item.validate()

            return item

        for mtl_path in TEST_MTL_PATHS.values():
            with self.subTest(mtl_path):
                with TemporaryDirectory() as tmp_dir:
                    create_dir = os.path.join(tmp_dir, 'create')
                    convert_dir = os.path.join(tmp_dir, 'convert')
                    original_dir = os.path.join(tmp_dir, 'original')
                    os.makedirs(create_dir, exist_ok=True)
                    os.makedirs(convert_dir, exist_ok=True)
                    os.makedirs(original_dir, exist_ok=True)

                    create_cmd = [
                        'landsat', 'create-item', '--mtl', mtl_path,
                        '--output', create_dir, '--legacy_l8'
                    ]
                    self.run_command(create_cmd)

                    stac_path = mtl_path.replace('_MTL.xml', '_SR_stac.json')
                    import shutil
                    shutil.copy(
                        stac_path,
                        os.path.join(original_dir,
                                     os.path.basename(stac_path)))
                    convert_cmd = [
                        'landsat', 'convert', '--stac', stac_path, '--dst',
                        convert_dir
                    ]
                    self.run_command(convert_cmd)

                    created_item = get_item(create_dir)

                    # Ensure media_type is set
                    for asset in created_item.assets.values():
                        self.assertTrue(asset.media_type is not None)

                    for asset_def in SR_ASSET_DEFS:
                        self.assertIn(asset_def.key, created_item.assets)
                    if created_item.properties[
                            'landsat:processing_level'] == 'L2SP':
                        for asset_def in THERMAL_ASSET_DEFS:
                            self.assertIn(asset_def.key, created_item.assets)

                    # TODO: Resolve disagreements between convert and create.
                    # This might best be informed by USGS's own STAC 1.0.* items
                    # when they are made available.

                    # created_item = get_item(create_dir)
                    # converted_item = get_item(convert_dir)

                    # self.assertTrue(
                    #     set(converted_item.assets.keys()).issubset(
                    #         set(created_item.assets.keys())),
                    #     msg=
                    #     f"{set(converted_item.assets.keys()) - set(created_item.assets.keys())}"
                    # )


def test_nonlegacyl8_item() -> None:
    mtl_path = test_data.get_path(
        "data-files/assets4/LC08_L2SP_017036_20130419_20200913_02_T2_MTL.xml")
    item = create_stac_item(mtl_path, legacy_l8=False)
    item_dict = item.to_dict()

    # nonlegacy uses v1.1.1 landsat extension
    ext = "https://landsat.usgs.gov/stac/landsat-extension/v1.1.1/schema.json"
    assert ext in item.stac_extensions

    # nonlegacy handles non-zero roll
    assert item_dict["properties"]["view:off_nadir"] != 0

    # nonlegacy has doi link
    assert len(item.get_links("cite-as")) == 1

    # nonlegacy has via link(s) to usgs stac-server
    usgs_stac_links = item.get_links(rel="via")
    assert len(usgs_stac_links) > 0


def test_read_href_modifier() -> None:
    mtl_path = test_data.get_path(
        "data-files/assets4/LC08_L2SP_017036_20130419_20200913_02_T2_MTL.xml")

    did_it = False

    def read_href_modifier(href: str) -> str:
        nonlocal did_it
        did_it = True
        return href

    _ = create_stac_item(mtl_path,
                         legacy_l8=False,
                         read_href_modifier=read_href_modifier)
    assert did_it


def test_southern_hemisphere_epsg() -> None:
    mtl_path = test_data.get_path(
        "data-files/tm/LT05_L2SP_010067_19860424_20200918_02_T2_MTL.xml")
    item = create_stac_item(mtl_path, legacy_l8=False, use_usgs_geometry=True)
    item_dict = item.to_dict()

    # northern hemisphere UTM zone is used for southern hemisphere scene
    assert item_dict["properties"]["proj:epsg"] == 32617


def test_mss_scale_offset() -> None:
    mtl_path = test_data.get_path(
        "data-files/mss/LM01_L1GS_001010_19720908_20200909_02_T2_MTL.xml")
    item = create_stac_item(mtl_path, legacy_l8=False, use_usgs_geometry=True)
    item_dict = item.to_dict()

    # MSS should grab scale and offset values (to convert DN to TOA radiance)
    # for the optical data bands from the MTL metadata
    asset_keys = ["green", "red", "nir08", "nir09"]
    for key in asset_keys:
        raster_bands = item_dict["assets"][key]["raster:bands"][0]
        assert "scale" in raster_bands
        assert "offset" in raster_bands


def test_l1_bitfields_exist() -> None:
    mtl_path = test_data.get_path(
        "data-files/mss/LM01_L1GS_001010_19720908_20200909_02_T2_MTL.xml")
    item = create_stac_item(mtl_path, legacy_l8=False, use_usgs_geometry=True)
    item_dict = item.to_dict()

    qa_pixel = item_dict["assets"]["qa_pixel"]
    assert "classification:bitfields" in qa_pixel


def test_l2_bitfields_exist() -> None:
    mtl_path = test_data.get_path(
        "data-files/oli-tirs/LC08_L2SP_047027_20201204_20210313_02_T1_MTL.xml")
    item = create_stac_item(mtl_path, legacy_l8=False, use_usgs_geometry=True)
    item_dict = item.to_dict()

    asset_keys = ["qa_pixel", "qa_radsat", "qa_aerosol"]
    for key in asset_keys:
        bitfield_band = item_dict["assets"][key]
        assert "classification:bitfields" in bitfield_band
