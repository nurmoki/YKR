# -*- coding: utf-8 -*-
"""
Reads data from ykr-zipfile and creates a geopackage

Technical notes: 
  Common columns in every table are forced to correct types. Table specific columns are guessed by parser
  For non-coordinate tables geometries are not created (e.g tables with non-coordinate YKR-data and commuting data (9-tables, ykr_tmatka))
  These will result as non-spatial geopackage tables. Using pyogrio because at least 10x faster than fiona but cannot use schema so will result 
  a bit inconsistent data types in output layers. Pyogrio do not allow append, this complicates script a bit.

Params:
    file_path: path to zipfile
    out_path: output folder
    geom: default False, if True creates geometries, defaults to points. Not valid for data that contains null-coordinates.
    polygon: default False, if True creates 250m-polygon geometries, valid only when geom is True
    combine: default False, if True creates one layer with all the years instead of yearly layers. Non-coordinate ykr-tables written separately always.
    
"""

#Import packages
import pandas as pd
import zipfile as zf
import geopandas as gp
from pathlib import Path
from shapely import geometry

#Path to zip-file containing YKR-data as csv-files
file_path = "path/to/zipfile"

#Set output folder
out_path = "out/path/for/geopackages/"

#Define function to convert csv-files in zip to geopackages
def csv_to_geopackage(file_path, out_path, geom=False, combine=False, polygon=False):
    csv_zip = zf.ZipFile(file_path)
    csv_in_zip = csv_zip.namelist()
    csv_in_zip = [string for string in csv_in_zip if string.endswith('.csv')]
    
    def csv_reader(csv_in_zip, out_path):
        """
        A generator function to be run for each csv-file

        """
        
        for file in csv_in_zip:
            df_gen = pd.read_csv(csv_zip.open(file),
                              dtype = {'xyind': str,
                                       'axyind' : str,
                                       'txyind' : str,
                                       'kunta' : str,
                                       'akunta' : str,
                                       'tkunta' : str
                                       })
            print(file)
                
            df_gen = df_gen.astype({col: 'int32' for col in df_gen.select_dtypes('int64').columns})
            
            if geom and df_gen.filter(regex = "^xyind").notna().any(axis=None): #Write geoms use geopandas if table with valid geometries

                if polygon: #create 250m polygons
                    df_gen['geometry'] = df_gen.apply(lambda a: geometry.box(a['x'] - 125, a['y'] - 125, a['x'] + 125, a['y'] + 125), axis=1)
                    gdf = gp.GeoDataFrame(df_gen, geometry='geometry', crs="EPSG:3067")
                else:
                    gdf = gp.GeoDataFrame(df_gen, geometry=gp.points_from_xy(df_gen.x, df_gen.y), crs="EPSG:3067")

            else: #geom=False, työmatkat, 9-tables, use geopandas but with None geometries
                df_gen = df_gen.assign(geometry = None)
                gdf = gp.GeoDataFrame(df_gen, geometry='geometry', crs="EPSG:3067")
              
            if combine and not file.endswith("_9.csv"):
                yield gdf
            else:
                yield gdf.to_file(f"{out_path}{Path(csv_zip.filename).stem}.gpkg", layer=f"{Path(file).stem}",
                                  driver="GPKG", mode='w', engine="pyogrio")

    #Consume generator function
    if combine:
        gdf_all = pd.concat(csv_reader(csv_in_zip, out_path))
        gdf_all.to_file(f"{out_path}{Path(csv_zip.filename).stem}.gpkg", layer=f"{Path(csv_zip.filename).stem}", 
                          driver="GPKG", mode='w', engine="pyogrio")
    else:
        list(csv_reader(csv_in_zip, out_path))

#Execute function for one zip-file
csv_to_geopackage(file_path, out_path)

#Optionally execute function for all YKR-zip files in a directory
import glob
zip_list = glob.glob("path/folder/zipfiles/*.zip") #List zip-files in folder
[csv_to_geopackage(s, out_path=out_path, geom=True) for s in zip_list]


