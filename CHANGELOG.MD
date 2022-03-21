# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). This project attempts to match the major and minor versions of [stactools](https://github.com/stac-utils/stactools) and increments the patch number as needed.

## [Unreleased]

NOTE: For backwards compatibility, all new features and fixes are ignored for Landsat 8 scenes unless `legacy_l8=False` is passed to the `create_stac_item` function.

### New Features

- Create Collection 2 Level-2 and Level-2 Items from additional instruments and platforms:
    - Landsat 1-5 Multispectral Scanner System (MSS, Level-1)
    - Landsat 4-5 Thematic Mapper (TM, Level-2)
    - Landsat 7 Enhanced Thematic Mapper Plus (ETM+, Level-2)
    - Landsat 8*-9 Operational Land Imager and Thermal Infrared Sensor (OLI-TIRS, Level-2)
- Decrease Asset verbosity by moving redundant `projection` extension and `gsd` information from the Assets to Item properties.
    - Assets having a different `gsd` than specified in the Item properties now override the Item properties `gsd` with their own `gsd` value (i.e., the thermal bands).
- Add links to USGS STAC Items
- Add ability to create STAC Collections
- Add ability to split or normalize Item geometries that cross the antimeridian
- Add instrument-specific DOI links to Items and Collections via the `scientific extension`
- Add `raster extension`
- Update `landsat extension` from `v1.1.0` to `v1.1.1`
- Include non-zero `off_nadir` angles for Landsat 8-9
- Switch to [common EO band names](https://github.com/stac-extensions/eo#common-band-names) for Asset keys to address existence of different band numbers for the same EO band between instruments or platforms
- Add option to use Item geometry from the corresponding USGS STAC Item in lieu of computation from the ANG.txt metadata file


### Fix

- Correct EPSG code for southern hemisphere scenes to [always use northern hemisphere codes](https://www.usgs.gov/faqs/why-do-landsat-scenes-southern-hemisphere-display-negative-utm-values)
- Remove incorrect link to USGS STAC browser page

### Chore

- Repo brought up to date with the current stactools-packages template contents as of 2022-02-18.

## [0.2.0] - 2021-07-20

### Changed

- Upgrade to stactools 0.2.1.a2 (supporting PySTAC 1.0.0)

[Unreleased]: <https://github.com/stactools-packages/landsat/compare/v0.2.0..main>
[0.2.0]: <https://github.com/stactools-packages/landsat/releases/tag/v0.2.0>
