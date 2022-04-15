import json
from typing import Any, Dict, Optional

import pkg_resources
from pystac import Asset, Extent, Link, MediaType, Provider, Summaries
from pystac.extensions.item_assets import AssetDefinition
from pystac.utils import make_absolute_href

from stactools.landsat.constants import Sensor


class CollectionFragments:
    """Class for accessing collection data."""

    def __init__(self, collection_id: str):
        """Initialize a new group of fragments for the provided Sensor."""
        self._id = collection_id

    def collection(self) -> Dict[str, Any]:
        """Loads the collection.json for the given collection id.

        Converts some elements to pystac object.

        Returns:
            Dict[str, Any]: Dict from parsed JSON with some converted fields.
        """
        data = self._load()
        data["extent"] = Extent.from_dict(data["extent"])
        data["providers"] = [
            Provider.from_dict(provider) for provider in data["providers"]
        ]
        data["links"] = [Link.from_dict(link) for link in data["links"]]
        data["summaries"] = Summaries(data["summaries"])

        item_assets = {}
        for key, asset_dict in data["item_assets"].items():
            media_type = asset_dict.get("type")
            asset_dict["type"] = MediaType[media_type]
            item_assets[key] = AssetDefinition(asset_dict)
        data["item_assets"] = item_assets

        return data

    def _load(self) -> Any:
        try:
            with pkg_resources.resource_stream(
                    "stactools.landsat.fragments",
                    f"collections/{self._id}.json") as stream:
                return json.load(stream)
        except FileNotFoundError as e:
            raise e


class Fragments:
    """Class for accessing asset and extension data."""

    def __init__(self, sensor: Sensor, satellite: int, base_href: str,
                 level1_radiance: Dict[str, Dict[str, Optional[float]]]):
        """Initialize a new group of fragments for the provided Sensor."""
        self._sensor = sensor
        self._satellite = satellite
        self.base_href = base_href
        self.level1_radiance = level1_radiance

    def common_assets(self) -> Dict[str, Any]:
        """Loads common-assets.json.

        Converts the loaded dicts to STAC Assets.

        Returns:
            Dict[str, Asset]: Dict of Assets keys and Assets.
        """
        asset_dicts = self._load("common-assets.json", "common")
        assets = self._convert_assets(asset_dicts)
        return assets

    def sr_assets(self) -> Dict[str, Any]:
        """Loads the sr-assets.json for the given sensor.

        If MSS, updates the band numbers depending on the given satellite number
        (satellites 1-3 use bands 4-7, satellites 4-5 use bands 1-4). Converts
        the loaded dicts to STAC Assets.

        Returns:
            Dict[str, Asset]: Dict of Assets keys and Assets.
        """
        asset_dicts = self._load("sr-assets.json")
        if self._satellite < 4:
            asset_dicts = self._update_mss_num(asset_dicts)
        assets = self._convert_assets(asset_dicts)
        return assets

    def sr_eo_bands(self) -> Dict[str, Any]:
        """Loads the sr-eo-bands.json for the given sensor.

        If MSS, updates the band numbers depending on the given satellite number
        (satellites 1-3 use bands 4-7, satellites 4-5 use bands 1-4).

        Returns:
            Dict[str, Dict]: Dict of Assets keys and EO Extension dicts.
        """
        eo = self._load("sr-eo-bands.json")
        if self._satellite < 4:
            eo = self._update_mss_num(eo)
        return eo

    def sr_raster_bands(self) -> Dict[str, Any]:
        """Loads the sr-raster-bands.json for the given sensor.

        If MSS, updates the band numbers depending on the given satellite number
        (satellites 1-3 use bands 4-7, satellites 4-5 use bands 1-4). If MSS,
        adds scale and offset informationt.

        Returns:
            Dict[str, Dict]: Dict of Assets keys and Raster Extension dicts.
        """
        raster = self._load("sr-raster-bands.json")
        if self._satellite < 4:
            raster = self._update_mss_num(raster)
        if self._sensor is Sensor.MSS:
            raster = self._update_mss_raster(raster)
        return raster

    def st_assets(self) -> Dict[str, Any]:
        """Loads the st-assets.json for the given sensor.

        Converts the loaded dicts to STAC Assets.

        Returns:
            Dict[str, Asset]: Dict of Assets keys and Assets.
        """
        asset_dicts = self._load("st-assets.json")
        assets = self._convert_assets(asset_dicts)
        return assets

    def st_eo_bands(self) -> Dict[str, Any]:
        """Loads the st-eo-bands.json for the given sensor.

        Returns:
            Dict[str, Dict]: Dict of Assets keys and EO Extension dicts.
        """
        eo = self._load("st-eo-bands.json")
        return eo

    def st_raster_bands(self) -> Dict[str, Any]:
        """Loads the st-raster-bands.json for the given sensor.

        Returns:
            Dict[str, Dict]: Dict of Assets keys and Raster Extension dicts.
        """
        raster = self._load("st-raster-bands.json")
        return raster

    def _update_mss_num(self, mss_dict: Dict[str, Any]) -> Dict[str, Any]:
        mss_str = json.dumps(mss_dict)
        mss_str = mss_str.replace("B4", "B7")
        mss_str = mss_str.replace("B3", "B6")
        mss_str = mss_str.replace("B2", "B5")
        mss_str = mss_str.replace("B1", "B4")
        mss_str = mss_str.replace("4-5", "1-3")
        return json.loads(mss_str)

    def _update_mss_raster(self, mss_raster_dict: Dict[str,
                                                       Any]) -> Dict[str, Any]:
        for key, value in mss_raster_dict.items():
            rad_key = value.pop("temp_name", None)
            if rad_key:
                if not self.level1_radiance[rad_key][
                        "mult"] or not self.level1_radiance[rad_key]["add"]:
                    mss_raster_dict[key].pop("unit")
                else:
                    mss_raster_dict[key]["scale"] = self.level1_radiance[
                        rad_key]["mult"]
                    mss_raster_dict[key]["offset"] = self.level1_radiance[
                        rad_key]["add"]

        return mss_raster_dict

    def _convert_assets(self, asset_dicts: Dict[str, Any]) -> Dict[str, Asset]:
        assets = {}
        for key, asset_dict in asset_dicts.items():
            media_type = asset_dict.pop("type", None)
            if media_type is not None:
                asset_dict["type"] = MediaType[media_type]
            else:
                asset_dict["type"] = MediaType.COG

            href_suffix = asset_dict.pop('href_suffix', None)
            if href_suffix is not None:
                href = f"{self.base_href}_{href_suffix}"
            else:
                href = f"{self.base_href}_{key.upper()}.TIF"
            asset_dict["href"] = make_absolute_href(href)
            assets[key] = Asset.from_dict(asset_dict)

        return assets

    def _load(self, file_name: str, dir_name: Optional[str] = None) -> Any:
        if dir_name is None:
            dir_name = self._sensor.name.lower()
        try:
            with pkg_resources.resource_stream(
                    "stactools.landsat.fragments",
                    f"{dir_name}/{file_name}") as stream:
                return json.load(stream)
        except FileNotFoundError as e:
            raise e
