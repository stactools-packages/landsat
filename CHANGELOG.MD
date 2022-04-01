# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.


## [Unreleased]

Nothing.

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

[Unreleased]: <https://github.com/stactools-packages/landsat/compare/v0.2.2..main>
[0.2.2]: <https://github.com/stactools-packages/landsat/compare/v0.2.1..v0.2.2>
[0.2.1]: <https://github.com/stactools-packages/landsat/compare/v0.2.0..v0.2.1>
[0.2.0]: <https://github.com/stactools-packages/landsat/releases/tag/v0.2.0>
