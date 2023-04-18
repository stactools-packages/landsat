# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.

## [Unreleased]

### Added

- Added support for the Grid Extension `grid:code` field ([#56](https://github.com/stactools-packages/landsat/pull/56))
- Added support for the Projection Extension `proj:centroid` field ([#56](https://github.com/stactools-packages/landsat/pull/56))

### Removed

Nothing.

### Changed

Nothing.

### Fixed

Nothing.

### Deprecated

Nothing.

## [0.3.0] - 2022-10-21

### Added

- "emissivity" to `roles` list on the `emis` and `emsd` assets ([#47](https://github.com/stactools-packages/landsat/pull/47))

### Removed

- `unit` from the `emis` and `emsd` assets (emissivity coefficient is unitless) ([#47](https://github.com/stactools-packages/landsat/pull/47))
- `legacy_l8` option from Item creation ([#40](https://github.com/stactools-packages/landsat/pull/40))
- Outdated `convert` command ([#40](https://github.com/stactools-packages/landsat/pull/40))
- Unused utility functions: `_parse_date`, `transform_mtl_to_stac`, `transform_stac_to_stac`, `stac_api_to_stac` ([#40](https://github.com/stactools-packages/landsat/pull/40))
- Unused test data files ([#40](https://github.com/stactools-packages/landsat/pull/40))
- Unused docs directory ([#40](https://github.com/stactools-packages/landsat/pull/40))

### Changed

- Item geometry and bbox coordinates rounded to six decimal places ([#45](https://github.com/stactools-packages/landsat/pull/45))
- Renamed `create_stac_item` function to `create_item` ([#40](https://github.com/stactools-packages/landsat/pull/40))

### Fixed

- Nothing.

### Deprecated

- Nothing.

## [0.2.4] - 2022-10-12

### Fixed

- Change function/method calls to remove warnings ([#42](https://github.com/stactools-packages/landsat/pull/42))
- Fixed issue where EPSG codes were missing the second to last digit when the digit is `0` ([#39](https://github.com/stactools-packages/landsat/pull/39))
- Remove the `unit`, `scale`, and `offset` properties from `raster:bands` when "NULL" values for `mult` and `add` are encountered in the metadata. This applies to Collection 2 Level-1 data only ([#33](https://github.com/stactools-packages/landsat/pull/33))
- Handle MultiPolygon geometries before applying the stactools antimeridian `fix_item` utility function ([#30](https://github.com/stactools-packages/landsat/pull/30))
- `eo:cloud_cover` is not added to Item properties when it was not computed (indicated by a value of -1) during scene processing ([#28](https://github.com/stactools-packages/landsat/pull/28))

## [0.2.3] - 2022-04-01

### Fixed

- Corrected  `setup.cfg` urls

## [0.2.2] - 2022-04-01

### Added

- Classification extension (`classification:bitfields`) added to Item QA Bands ([#23](https://github.com/stactools-packages/landsat/pull/23))

## [0.2.1] - 2022-03-29

NOTE: For backwards compatibility, all items under the Added, Changed, and Fixed headings below are ignored for Landsat 8 scenes unless `legacy_l8=False` is passed to the `create_stac_item` function.

### Added

- Collection 2 Level-1 and Level-2 Items from additional instruments and platforms:
  - Landsat 1-5 Multispectral Scanner System (MSS, Level-1)
  - Landsat 4-5 Thematic Mapper (TM, Level-2)
  - Landsat 7 Enhanced Thematic Mapper Plus (ETM+, Level-2)
  - Landsat 8*-9 Operational Land Imager and Thermal Infrared Sensor (OLI-TIRS, Level-2)
- Collection 2 Level-1 and Level-2 STAC Collections
- Item links to corresponding USGS STAC Items
- Item and Collection DOI links (`scientific` extension) specific to the instrument
- Option to split or normalize Item geometries that cross the antimeridian
- Option to use Item geometry from the corresponding USGS STAC Item in lieu of computation from the ANG.txt metadata file
- `raster extension`

### Changed

- Decrease Asset verbosity by moving redundant `projection` extension and `gsd` information from the Assets to Item properties.
  - Assets having a different `gsd` than specified in the Item properties now override the Item properties `gsd` with their own `gsd` value (i.e., the thermal bands).
- Update the `landsat` extension from `v1.1.0` to `v1.1.1`
- Include non-zero `off_nadir` angles for Landsat 8-9
- Switch to [common EO band names](https://github.com/stac-extensions/eo#common-band-names) for Asset keys to address existence of different band numbers for the same EO band between instruments or platforms
- Update repository to the stactools-packages [template contents](https://github.com/stac-extensions/template/commit/7dfc84fd70c4cf15d6035968323c0baf8da06dd8).

### Fixed

- Correct EPSG code for southern hemisphere scenes to [always use northern hemisphere codes](https://www.usgs.gov/faqs/why-do-landsat-scenes-southern-hemisphere-display-negative-utm-values)
- Remove incorrect link to USGS STAC browser page

## [0.2.0] - 2021-07-20

### Changed

- Upgrade to stactools 0.2.1.a2 (supporting PySTAC 1.0.0)

[Unreleased]: <https://github.com/stactools-packages/landsat/compare/v0.3.0..main>
[0.3.0]: <https://github.com/stactools-packages/landsat/compare/v0.2.4..v0.3.0>
[0.2.4]: <https://github.com/stactools-packages/landsat/compare/v0.2.3..v0.2.4>
[0.2.3]: <https://github.com/stactools-packages/landsat/compare/v0.2.2..v0.2.3>
[0.2.2]: <https://github.com/stactools-packages/landsat/compare/v0.2.1..v0.2.2>
[0.2.1]: <https://github.com/stactools-packages/landsat/compare/v0.2.0..v0.2.1>
[0.2.0]: <https://github.com/stactools-packages/landsat/releases/tag/v0.2.0>

<!-- markdownlint-disable-file MD024 -->
