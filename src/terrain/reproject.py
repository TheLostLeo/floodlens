import os
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling


def reproject_dem_to_utm(source_path, output_path):
    """
    Reproject a DEM GeoTIFF from EPSG:4326 to EPSG:32644 (WGS 84 / UTM zone 44N).
    
    Parameters:
    -----------
    source_path : str
        Path to the source DEM GeoTIFF file.
    output_path : str
        Path where the reprojected DEM will be saved.
    
    Returns:
    --------
    str
        The output path after successfully creating the file.
    
    Raises:
    -------
    FileNotFoundError
        If the source file does not exist.
    ValueError
        If the DEM has no CRS or does not have exactly one band.
    """
    
    # Check that source file exists
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file not found: {source_path}")
    
    # Create output folder if it does not exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Open source DEM
    with rasterio.open(source_path) as src:
        # Check that CRS exists
        if src.crs is None:
            raise ValueError("Source DEM has no CRS (coordinate reference system).")
        
        # Check that DEM has exactly one band
        if src.count != 1:
            raise ValueError(f"Source DEM must have exactly one band, but has {src.count} bands.")
        
        # Get source data
        src_crs = src.crs
        src_nodata = src.nodata
        
        # Calculate transform for target CRS and resolution (30m x 30m)
        dst_crs = "EPSG:32644"

        transform, width, height = calculate_default_transform(
            src.crs,
            dst_crs,
            src.width,
            src.height,
            *src.bounds,
            resolution=30,
        )
        
        
        # Create output raster
        output_kwargs = src.profile.copy()
        output_kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height,
            'nodata': -32768,
        })
        
        # Reproject with bilinear resampling
        with rasterio.open(output_path, 'w', **output_kwargs) as dst:
            reproject(
                src.read(1),
                rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.bilinear,
                src_nodata=src_nodata,
                dst_nodata=-32768,
            )
    
    return output_path
