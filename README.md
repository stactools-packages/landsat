# stactools-landsat

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
  - [proj](https://github.com/stac-extensions/projection/)
  - [eo](https://github.com/stac-extensions/eo)
  - [view](https://github.com/stac-extensions/view)
  - [landsat](https://landsat.usgs.gov/stac/landsat-extension/v1.1.0/schema.json)

This repository will assist you in the generation of STAC files for Landsat datasets. The table below provides an overview on Landsat Mission's sensors and band wavelengths.

<img width="1147" alt="Landsat Missions - Sensors and Band Wavelengths" src="https://user-images.githubusercontent.com/91917800/155609794-4cdb98aa-36f3-4452-93cd-c6193416e3a4.png">

Source: https://pubs.usgs.gov/fs/2015/3081/fs20153081_ver1.2.pdf


## Examples

### STAC objects

- [Item](examples/item/LC08_L2SP_005009_20150710_02_T2.json)

### Command-line usage

To create the example STAC `Item`:

```bash
$ stac landsat create-item "tests/data-files/assets/LC08_L2SP_005009_20150710_20200908_02_T2_MTL.xml" "examples/item/LC08_L2SP_005009_20150710_02_T2.json"
```

Use `stac landsat --help` to see all subcommands and options.
