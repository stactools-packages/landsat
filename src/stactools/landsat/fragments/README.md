# Fragments

Fragments are JSON files that contain constant values that are included in generated STAC items. The following fragment types/files exist:

- `common-assets.json`: Asset data that is common to all Landsat data products.
- `sr-` or `st-assets.json`: Surface reflectance or surface temperature asset data.
- `sr-` or `st-eo-bands.json`: STAC EO extension data for surface reflectance or temperature assets.
- `sr-` or `st-raster-bands.json`: STAC raster-band extension data for surface reflectance or temperature assets.

Note that MSS fragments use the `sr-` file pattern even though MSS data is TOA (not surface) radiance (not reflectance).
