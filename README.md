# stactools-landsat

[![PyPI](https://img.shields.io/pypi/v/stactools-landsat)](https://pypi.org/project/stactools-landsat/)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/stactools-packages/landsat/main?filepath=docs/installation_and_basic_usage.ipynb)

- Name: landsat
- Package: `stactools.landsat`
- PyPI: https://pypi.org/project/stactools-landsat/
- Owners:
  - @lossyrob
  - @pjhartzell
  - @gadomski
- Dataset homepages:
  - https://www.usgs.gov/landsat-missions
  - https://landsat.gsfc.nasa.gov/
- STAC extensions used:
  - [classification](https://github.com/stac-extensions/classification)
  - [eo](https://github.com/stac-extensions/eo)
  - [landsat](https://landsat.usgs.gov/stac/landsat-extension/v1.1.1/schema.json)
  - [proj](https://github.com/stac-extensions/projection/)
  - [raster](https://github.com/stac-extensions/raster)
  - [scientific](https://github.com/stac-extensions/scientific)
  - [view](https://github.com/stac-extensions/view)

This repository will assist you in the generation of STAC files for Landsat datasets. The table below provides an overview on Landsat Mission's sensors and band wavelengths.

<img width="1147" alt="Landsat Missions - Sensors and Band Wavelengths" src="https://user-images.githubusercontent.com/1312546/190440352-0b6e2c81-f1b4-48ff-bcf1-5b5addba1bd9.png">

Source: https://pubs.usgs.gov/fs/2015/3081/fs20153081.pdf


## Examples

### STAC Collections and Items

- [Collection](examples/landsat-c2-l2/collection.json)
- [Item](examples/landsat-c2-l1/LM01_L1GS_001010_19720908_02_T2/LM01_L1GS_001010_19720908_02_T2.json)

### Command-line usage

To create a STAC `Item`:

```bash
$ stac landsat create-item --mtl tests/data-files/oli-tirs/LC08_L2SP_047027_20201204_20210313_02_T1_MTL.xml --output examples --usgs_geometry
```

To create a STAC `Collection` from a text file containing a list of Landsat scene XML metadata files:

```bash
$ stac landsat create-collection --file_list examples/c2-l2-file-list.txt --output examples/landsat-c2-l2 --id landsat-c2-l2 --usgs_geometry
```

The above `create-collection` command is exactly how the contents of the `examples/landsat-c2-l2` directory are generated.
