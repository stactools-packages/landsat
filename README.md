[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/stactools-packages/landsat/main?filepath=docs/installation_and_basic_usage.ipynb)

# stactools-landsat

- Name: landsat
- Package: `stactools.landsat`
- Dataset homepage: https://landsat.gsfc.nasa.gov/
- STAC extensions used:
  - [proj](https://github.com/stac-extensions/projection/)
  - [eo](https://github.com/stac-extensions/eo)
  - [view](https://github.com/stac-extensions/view)
  - [landsat](https://landsat.usgs.gov/stac/landsat-extension/v1.1.0/schema.json)

Create STAC Items for Landsat 8 Collection 2 Level 2 data.

## Examples

### STAC objects

- [Item](examples/item/LC08_L2SP_005009_20150710_02_T2.json)

### Command-line usage

To create the example STAC `Item`:

```bash
$ stac landsat create-item "/tests/data-files/assets/LC08_L2SP_005009_20150710_20200908_02_T2_MTL.xml" "examples/item/LC08_L2SP_005009_20150710_02_T2.json"
```

Use `stac landsat --help` to see all subcommands and options.
