from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from pyproj import Geod
from pystac.utils import map_opt, str_to_datetime
from stactools.core.io import ReadHrefModifier
from stactools.core.io.xml import XmlElement
from stactools.core.projection import transform_from_bbox


class MTLError(Exception):
    pass


class MtlMetadata:
    """Parses a Collection 2 MTL XML file.

    References https://github.com/sat-utils/sat-stac-landsat/blob/f2263485043a827b4153aecc12f45a3d1363e9e2/satstac/landsat/main.py#L157
    """  # noqa

    def __init__(self,
                 root: XmlElement,
                 href: Optional[str] = None,
                 legacy_l8: bool = True):
        self._root = root
        self.href = href
        self.legacy_l8 = legacy_l8

    def _xml_error(self, item: str) -> MTLError:
        return MTLError(f"Cannot find {item} in MTL metadata" +
                        ("" if self.href is None else f" at {self.href}"))

    def _get_text(self, xpath: str) -> str:
        return self._root.find_text_or_throw(xpath, self._xml_error)

    def _get_float(self, xpath: str) -> float:
        return float(self._get_text(xpath))

    def _get_int(self, xpath: str) -> int:
        return int(self._get_text(xpath))

    def _float_or_none(self, value: str) -> Optional[float]:
        if value == "NULL":
            return None
        return float(value)

    @property
    def satellite_num(self) -> int:
        """Return the Landsat satellite number."""
        return int(self.product_id[2:4])

    @property
    def product_id(self) -> str:
        """Return the Landsat product ID."""
        return self._get_text("PRODUCT_CONTENTS/LANDSAT_PRODUCT_ID")

    @property
    def item_id(self) -> str:
        # Remove the processing date, as products IDs
        # that only vary by processing date represent the
        # same scene
        # See "Section 5 - Product Packaging" at
        # https://prd-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/atoms/files/LSDS-1619_Landsat8-C2-L2-ScienceProductGuide-v2.pdf  # noqa

        # ID format: LXSS_LLLL_PPPRRR_YYYYMMDD_yyyymmdd_CX_TX
        # remove yyyymmdd
        id_parts = self.product_id.split('_')
        id = '_'.join(id_parts[:4] + id_parts[-2:])

        return id

    @property
    def scene_id(self) -> str:
        """"Return the Landsat scene ID."""
        return self._get_text("LEVEL1_PROCESSING_RECORD/LANDSAT_SCENE_ID")

    @property
    def processing_level(self) -> str:
        """Processing level. Determines product contents.

        Returns either 'L2SP' or 'L2SR', standing for
        'Level 2 Science Product' and 'Level 2 Surface Reflectance',
        respectively. L2SP has thermal + surface reflectance assets;
        L2SR only has surface reflectance.
        """
        return self._get_text("PRODUCT_CONTENTS/PROCESSING_LEVEL")

    @property
    def epsg(self) -> int:
        utm_zone = self._root.find_text('PROJECTION_ATTRIBUTES/UTM_ZONE')
        if utm_zone:
            if self.satellite_num == 8 and self.legacy_l8:
                # Keep current STAC Item content consistent for Landsat 8
                bbox = self.bbox
                utm_zone_integer = int(
                    self._get_text('PROJECTION_ATTRIBUTES/UTM_ZONE'))
                center_lat = (bbox[1] + bbox[3]) / 2.0
                return int(
                    f"{326 if center_lat > 0 else 327}{utm_zone_integer:02d}")
            else:
                # The projection transforms in the COGs provided by the USGS are
                # always for UTM North zones. The EPSG codes should therefore
                # be UTM north zones (326XX, where XX is the UTM zone number).
                # See: https://www.usgs.gov/faqs/why-do-landsat-scenes-southern-hemisphere-display-negative-utm-values  # noqa
                utm_zone_integer = int(
                    self._get_text('PROJECTION_ATTRIBUTES/UTM_ZONE'))
                return int(f"326{utm_zone_integer:02d}")
        else:
            # Polar Stereographic
            # Based on Landsat 8-9 OLI/TIRS Collection 2 Level 1 Data Format Control Book,
            # should only ever be 71 or -71
            lat_ts = self._get_text('PROJECTION_ATTRIBUTES/TRUE_SCALE_LAT')
            if lat_ts == "-71.00000":
                # Antarctic
                return 3031
            elif lat_ts == "71.00000":
                # Arctic
                return 3995
            else:
                raise MTLError(
                    f'Unexpeced value for PROJECTION_ATTRIBUTES/TRUE_SCALE_LAT: {lat_ts} '
                )

    @property
    def bbox(self) -> List[float]:
        # Might be cleaner to just transform the proj bbox to WGS84.
        lons = [
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_UL_LON_PRODUCT"),
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_UR_LON_PRODUCT"),
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_LL_LON_PRODUCT"),
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_LR_LON_PRODUCT")
        ]

        lats = [
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_UL_LAT_PRODUCT"),
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_UR_LAT_PRODUCT"),
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_LL_LAT_PRODUCT"),
            self._get_float("PROJECTION_ATTRIBUTES/CORNER_LR_LAT_PRODUCT")
        ]
        geod = Geod(ellps="WGS84")
        offset = self.sr_gsd / 2
        _, _, bottom_distance = geod.inv(lons[2], lats[2], lons[3], lats[3])
        bottom_offset = offset * (lons[3] - lons[2]) / bottom_distance
        _, _, top_distance = geod.inv(lons[0], lats[0], lons[1], lats[1])
        top_offset = offset * (lons[1] - lons[0]) / top_distance
        _, _, lat_distance = geod.inv(lons[0], lats[0], lons[2], lats[2])
        lat_offset = offset * (lats[0] - lats[2]) / lat_distance
        return [
            min(lons) - bottom_offset,
            min(lats) - lat_offset,
            max(lons) + top_offset,
            max(lats) + lat_offset
        ]

    @property
    def proj_bbox(self) -> List[float]:
        # USGS metadata provide bounds at the center of the pixel, but
        # GDAL/rasterio transforms are to edge of pixel.
        # https://github.com/stac-utils/stactools/issues/117
        offset = self.sr_gsd / 2
        xs = [
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_UL_PROJECTION_X_PRODUCT") -
            offset,
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_UR_PROJECTION_X_PRODUCT") +
            offset,
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_LL_PROJECTION_X_PRODUCT") -
            offset,
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_LR_PROJECTION_X_PRODUCT") +
            offset
        ]

        ys = [
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_UL_PROJECTION_Y_PRODUCT") +
            offset,
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_UR_PROJECTION_Y_PRODUCT") +
            offset,
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_LL_PROJECTION_Y_PRODUCT") -
            offset,
            self._get_float(
                "PROJECTION_ATTRIBUTES/CORNER_LR_PROJECTION_Y_PRODUCT") -
            offset
        ]

        return [min(xs), min(ys), max(xs), max(ys)]

    @property
    def sr_shape(self) -> List[int]:
        """Shape for surface reflectance assets.

        Used for proj:shape. In [row, col] order"""
        return [
            self._get_int("PROJECTION_ATTRIBUTES/REFLECTIVE_LINES"),
            self._get_int("PROJECTION_ATTRIBUTES/REFLECTIVE_SAMPLES")
        ]

    @property
    def thermal_shape(self) -> Optional[List[int]]:
        """Shape for thermal bands.

        None if thermal bands not present.
        Used for proj:shape. In [row, col] order"""
        rows = map_opt(
            int, self._root.find_text("PROJECTION_ATTRIBUTES/THERMAL_LINES"))
        cols = map_opt(
            int, self._root.find_text("PROJECTION_ATTRIBUTES/THERMAL_SAMPLES"))

        if rows is not None and cols is not None:
            return [rows, cols]
        else:
            return None

    @property
    def sr_transform(self) -> List[float]:
        return transform_from_bbox(self.proj_bbox, self.sr_shape)

    @property
    def thermal_transform(self) -> Optional[List[float]]:
        return map_opt(
            lambda shape: transform_from_bbox(self.proj_bbox, shape),
            self.thermal_shape)

    @property
    def sr_gsd(self) -> float:
        return self._get_float(
            "LEVEL1_PROJECTION_PARAMETERS/GRID_CELL_SIZE_REFLECTIVE")

    @property
    def thermal_gsd(self) -> Optional[float]:
        return map_opt(
            float,
            self._root.find_text(
                'LEVEL1_PROJECTION_PARAMETERS/GRID_CELL_SIZE_THERMAL'))

    @property
    def scene_datetime(self) -> datetime:
        date = self._get_text("IMAGE_ATTRIBUTES/DATE_ACQUIRED")
        time = self._get_text("IMAGE_ATTRIBUTES/SCENE_CENTER_TIME")

        return str_to_datetime(f"{date} {time}")

    @property
    def cloud_cover(self) -> float:
        return self._get_float("IMAGE_ATTRIBUTES/CLOUD_COVER")

    @property
    def sun_azimuth(self) -> float:
        """Returns the sun azimuth in STAC form.

        Converts from Landsat metadata form (-180 to 180 from north, west being
        negative) to STAC form (0 to 360 clockwise from north).

        Returns:
            float: Sun azimuth, 0 to 360 clockwise from north.
        """
        azimuth = self._get_float("IMAGE_ATTRIBUTES/SUN_AZIMUTH")
        if azimuth < 0.0:
            azimuth += 360
        return azimuth

    @property
    def sun_elevation(self) -> float:
        return self._get_float("IMAGE_ATTRIBUTES/SUN_ELEVATION")

    @property
    def off_nadir(self) -> Optional[float]:
        if self.satellite_num == 8 and self.legacy_l8:
            # Keep current STAC Item content consistent for Landsat 8
            if self._get_text("IMAGE_ATTRIBUTES/NADIR_OFFNADIR") == "NADIR":
                return 0
            else:
                return None
        else:
            # NADIR_OFFNADIR and ROLL_ANGLE xml entries do not exist prior to
            # landsat 8. Therefore, we perform a soft check for NADIR_OFFNADIR.
            # If exists and is equal to "OFFNADIR", then a non-zero ROLL_ANGLE
            # exists. We force this ROLL_ANGLE to be positive to conform with
            # the stac View Geometry extension. We return 0 otherwise since
            # off-nadir views are only an option on Landsat 8-9.
            if self._root.find_text(
                    "IMAGE_ATTRIBUTES/NADIR_OFFNADIR") == "OFFNADIR":
                return abs(self._get_float("IMAGE_ATTRIBUTES/ROLL_ANGLE"))
            else:
                return 0

    @property
    def wrs_path(self) -> str:
        return self._get_text("IMAGE_ATTRIBUTES/WRS_PATH").zfill(3)

    @property
    def wrs_row(self) -> str:
        return self._get_text("IMAGE_ATTRIBUTES/WRS_ROW").zfill(3)

    @property
    def landsat_metadata(self) -> Dict[str, Any]:
        landsat_meta = {
            "landsat:cloud_cover_land":
            self._get_float("IMAGE_ATTRIBUTES/CLOUD_COVER_LAND"),
            "landsat:wrs_type":
            self._get_text("IMAGE_ATTRIBUTES/WRS_TYPE"),
            "landsat:wrs_path":
            self.wrs_path,
            "landsat:wrs_row":
            self.wrs_row,
            "landsat:collection_category":
            self._get_text("PRODUCT_CONTENTS/COLLECTION_CATEGORY"),
            "landsat:collection_number":
            self._get_text("PRODUCT_CONTENTS/COLLECTION_NUMBER"),
            "landsat:correction":
            self.processing_level,
            "landsat:scene_id":
            self.scene_id
        }
        if self.satellite_num == 8 and self.legacy_l8:
            landsat_meta["landsat:processing_level"] = landsat_meta.pop(
                "landsat:correction")
        return landsat_meta

    @property
    def level1_radiance(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Gets the scale (mult) and offset (add) values for generating TOA
        radiance from Level-1 DNs.

        This is relevant to MSS data, which is only processed to Level-1. Sets
        the scale and offset values to None if a NULL text string is
        encountered.

        Returns:
            Dict[str, Any]: Dict of scale and offset dicts, keyed by band
                number.
        """
        node = self._root.find_or_throw("LEVEL1_RADIOMETRIC_RESCALING",
                                        self._xml_error)
        mult_add: Dict[str, Any] = defaultdict(dict)
        for item in node.element:
            value = str(item.text)
            if item.tag.startswith("RADIANCE_MULT_BAND"):
                band = f'B{item.tag.split("_")[-1]}'
                mult_add[band]["mult"] = self._float_or_none(value)
            elif item.tag.startswith("RADIANCE_ADD_BAND"):
                band = f'B{item.tag.split("_")[-1]}'
                mult_add[band]["add"] = self._float_or_none(value)
        return mult_add

    @classmethod
    def from_file(cls,
                  href: str,
                  read_href_modifier: Optional[ReadHrefModifier] = None,
                  legacy_l8: bool = True) -> "MtlMetadata":
        return cls(XmlElement.from_file(href, read_href_modifier),
                   href=href,
                   legacy_l8=legacy_l8)
