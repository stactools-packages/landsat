import os

from pystac import CatalogType

from stactools.landsat.stac import create_collection, create_stac_item


def test_data_href(path: str) -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests",
                        "data-files", path)


# MSS, Landsat 1-5 (Collection 2 Level-1)
mtl_xml_href = test_data_href(
    "mss/LM01_L1GS_001010_19720908_20200909_02_T2_MTL.xml")
item = create_stac_item(mtl_xml_href, use_usgs_geometry=True)
item.validate()
destination = "examples/item/mss"
item_path = os.path.join(destination, f"{item.id}.json")
item.set_self_href(item_path)
item.make_asset_hrefs_relative()
item.save_object(include_self_link=False)

# TM, Landsat 4-5 (Collection 2 Level-2)
mtl_xml_href = test_data_href(
    "tm/LT04_L2SP_002026_19830110_20200918_02_T1_MTL.xml")
item = create_stac_item(mtl_xml_href, use_usgs_geometry=True)
item.validate()
destination = "examples/item/tm"
item_path = os.path.join(destination, f"{item.id}.json")
item.set_self_href(item_path)
item.make_asset_hrefs_relative()
item.save_object(include_self_link=False)

# ETM, Landsat 7 (Collection 2 Level-2)
mtl_xml_href = test_data_href(
    "etm/LE07_L2SP_021030_20100109_20200911_02_T1_MTL.xml")
item = create_stac_item(mtl_xml_href, use_usgs_geometry=True)
item.validate()
destination = "examples/item/etm"
item_path = os.path.join(destination, f"{item.id}.json")
item.set_self_href(item_path)
item.make_asset_hrefs_relative()
item.save_object(include_self_link=False)

# OLI-TIRS, Landsat 8-9 (Collection 2 Level-2) - Legacy
mtl_xml_href = test_data_href(
    "assets/LC08_L2SP_005009_20150710_20200908_02_T2_MTL.xml")
item = create_stac_item(mtl_xml_href)
destination = "examples/item/oli-tirs"
item_path = os.path.join(destination, f"{item.id}-legacy.json")
item.set_self_href(item_path)
item.make_asset_hrefs_relative()
item.save_object(include_self_link=False)

# OLI-TIRS, Landsat 8-9 (Collection 2 Level-2) - New
mtl_xml_href = test_data_href(
    "assets/LC08_L2SP_005009_20150710_20200908_02_T2_MTL.xml")
item = create_stac_item(mtl_xml_href, legacy_l8=False, use_usgs_geometry=True)
destination = "examples/item/oli-tirs"
item_path = os.path.join(destination, f"{item.id}.json")
item.set_self_href(item_path)
item.make_asset_hrefs_relative()
item.save_object(include_self_link=False)

# STAC Collection: Collection 2 Level-1
collection = create_collection("landsat-c2-l1")
collection.catalog_type = CatalogType.SELF_CONTAINED
# NOTE: Will not validate until Item(s) are added to it
# collection.validate()
destination = "examples/collection/c2l2"
collection_path = os.path.join(destination, f"{collection.id}.json")
collection.set_self_href(collection_path)
collection.make_all_asset_hrefs_relative()
collection.save_object(include_self_link=False)
