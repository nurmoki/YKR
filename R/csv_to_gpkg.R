### Convert zipped YKR-data (csv) to geopackage tables ###

# Reads data from ykr-zipfiles, Creates geopackages to the spesified folder and uploads data to the created geopackages 

# Technical notes: 
  # common columns in every table are forced to certain types in read_scv --> col_types. 
  # Table specific columns are character by default but with guess_parser converted to correct type
  # For numeric values result is usually int
  # For non-coordinate tables geometries cannot be created (e.g tables with non-coordinate YKR-data and commuting data)
  # Using readr functions because of speed but cannot utilize csvt-files as in gdal

# Parameters:
  # geom: default FALSE, if TRUE creates point geometries
  # polygons: default FALSE, if TRUE creates polygon geometries, valid only when geom is TRUE
  # combine: default FALSE, if TRUE creates one layer with all the years instead of yearly layers. Non-coordinate data written separately always.


#Imports, install if needed
library('sf')
library('readr')
library('dplyr')

#Path to zip-file containing YKR-data as csv-files
file_path = "path/to/zipfile"

#Set output folder
out_path = "out/path/for/geopackages/"


#Define function to read csv-files from zip-files and to convert them to geopackage.
csv_to_geopackage <- function(zip_file, out_path, geom = FALSE, polygons = FALSE, combine = FALSE) {
  print(paste("zip-file = ", zip_file))
  
  csv_files <- unzip(zip_file, list = TRUE) %>% .[endsWith(.$Name, ".csv"),]
  
  col_types = cols(xyind = "character", axyind = "character", txyind = "character", kunta = "character", 
                   akunta = "character", tkunta = "character",
                   TK_id = "integer", aTK_id = "integer", tTK_id = "integer", id = "integer", vuosi = "integer", 
                   x = "integer", y = "integer", ax = "integer", ay = "integer",
                   .default = col_character())
  
  lapply(csv_files[,1], function(b, a) { 
    read_csv(unz(description = zip_file, filename = b), 
             progress = FALSE, guess_max = 10000, 
             col_types = col_types) %>%
      mutate(across(.cols = !any_of(names(col_types$cols)), ~parse_guess(., guess_integer = TRUE))) %>%
      
      glimpse(.) %>%
      
      {if (geom && select(., ends_with("xyind")) %>% anyNA() == FALSE) #Check if NA-coordinates from xyind column
        
        if (polygons) {
          xy <- select(., x, y)

          sfg.list <- unname(apply(xy, 1, function(i, j) { #Create rectangular polygons
            st_polygon(list(matrix(
              c(i[1] + j, i[1] - j, i[1] - j, i[1] + j, i[1] + j,
                i[2] + j, i[2] + j, i[2] - j, i[2] - j, i[2] + j),
              ncol = 2
            )))
          }, j = 125))
          
          st_sf(geometry = st_sfc(sfg.list), crs = 3067, .)
          
        } else {
          st_as_sf(., coords = c("x", "y"), crs = 3067) #Create points
        }
        else .
      } %>%
        st_write(.,
                 paste0(out_path, tools::file_path_sans_ext(basename(zip_file)),".gpkg"),
                 layer = tools::file_path_sans_ext(basename(if_else(combine, zip_file, b))), append = combine)
    
  }, zip_file)
}


#Run function for one zip-file.
csv_to_geopackage(file_path, out_path = out_path)

#Run for all zip-files in specified folder
ykr_zip_files <- list.files(path = ykr_path, pattern = ".zip$", full.names = TRUE) #List all zip-files in specified folder
lapply(ykr_zip_files, csv_to_geopackage, out_path = out_path)



