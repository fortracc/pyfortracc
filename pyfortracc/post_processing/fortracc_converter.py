import glob
import numpy as np
import pandas as pd
import geopandas as gpd
from datetime import datetime
import pathlib
from shapely import wkt
# from shapely.affinity import affine_transform
from pyfortracc.utilities.math_utils import uv2angle, uv2magn, calculate_vel_area
# from pyfortracc.utilities.utils import get_geotransform, get_pixarea, calculate_pixel_area


def convert_parquet_to_family(name_list,defaults_path = 'track', default_undef=-999.99, csv_out=True):
    
    input_columns = ['uid','threshold_level', 'cluster_id', 'timestamp', 'lifetime', 'size', 'expansion', 'u_', 'v_', 'status', 'geometry']

    #reading the tracking table:
    tracking_files = sorted(glob.glob(name_list['output_path'] + defaults_path + '/trackingtable/*.parquet'))
    tracking_table = pd.concat(pd.read_parquet(f,columns=input_columns) for f in tracking_files)
    tracking_table = tracking_table[input_columns]

    #find NaN, Inf, -Inf, empty strings, None, null, and replace for default_undef:
    tracking_table.replace([np.nan, np.inf, -np.inf, '', None, 'null'], default_undef, inplace=True)

    # Convert the 'geometry' column from WKT string to Shapely geometry and create the GeoDataFrame
    tracking_table['geometry'] = tracking_table['geometry'].apply(wkt.loads)
    geo_tracking_table = gpd.GeoDataFrame(tracking_table, geometry='geometry')
        
    # Group the data by 'uid' where 'threshold_level' == 0 and concatenate the groups into a single DataFrame:
    family_table = geo_tracking_table.loc[geo_tracking_table['threshold_level'] == 0].groupby('uid', as_index=False).apply(lambda x: x).reset_index(drop=True)
    family_table.drop('threshold_level', axis=1, inplace=True)

    #ALAN: ja converter no parquet
    family_table = family_table.rename(columns={'lifetime': 'time'})

    # Ensure 'timestamp' is in datetime format
    family_table['timestamp'] = pd.to_datetime(family_table['timestamp'], errors='coerce')
    # Group by 'uid' and calculate the first and last timestamps
    duration_df = family_table.groupby('uid')['timestamp'].agg(first_timestamp='min', last_timestamp='max').reset_index()
    # Calculate the total duration in hours for each 'uid'
    duration_df['duration'] = (duration_df['last_timestamp'] - duration_df['first_timestamp']).dt.total_seconds() / 3600
    # Merge the calculated 'duration_hours' back into the original DataFrame
    family_table = family_table.merge(duration_df[['uid', 'duration']], on='uid', how='left')    

    # Calculate centroids in a vectorized manner
    family_table['centroid'] = family_table['geometry'].centroid
    family_table['clat'] = family_table['centroid'].y
    family_table['clon'] = family_table['centroid'].x

    #Velocity and direction calculation
    # Get pixel size based on geotransform:
    # pixel_size = (geotransform[0] + geotransform[3]) / 2
    # Get delta_time in minutes:
    # delta_time = name_list['delta_time']
    # #get the area of the pixel and the xlat and xlon vectors:
    # pixel_area, xlat, xlon = calculate_pixel_area(name_list)

    # family_table['vel'] = family_table[['u_', 'v_', 'clon', 'clat']].apply(lambda x:
    #                                         calculate_vel_area(
    #                                         uv2magn(x['u_'], x['v_']),
    #                                         'km/h', 
    #                                         get_pixarea(x['clon'], x['clat'], xlon, xlat, pixel_area),
    #                                         delta_time)
    #                                         if not default_undef in x.values
    #                                         else default_undef, axis=1)

    family_table['dir'] = family_table[['u_', 'v_']].apply(lambda x:
                                                    uv2angle(x['u_'], x['v_'])
                                                    if not default_undef in x.values
                                                    else default_undef, axis=1)
        
    # Create the output directory if it does not exist
    pathlib.Path(name_list['output_path'] + defaults_path + '/family').mkdir(parents=True, exist_ok=True)
    
    # Prepare the data for saving
    output_columns = ['uid', 'cluster_id', 'timestamp', 'time', 'duration', 'clat', 'clon', 'size', 'expansion', 'dir','u_' ,'v_', 'status']
        
    #output file is based on the family_table first timestamp and last timestamp using family_YEAR1MONTH1DAY1HOUR1_YEAR2MONTH2DAY2HOUR2.txt:
    min_timestamp = family_table['timestamp'].min().strftime('%Y%m%d%H')
    max_timestamp = family_table['timestamp'].max().strftime('%Y%m%d%H')

    #saving a csv file
    if csv_out == True:
        #output file using family_YEAR1MONTH1DAY1HOUR1_YEAR2MONTH2DAY2HOUR2.csv:
        output_file = name_list['output_path']  + defaults_path +  '/family/family_' + min_timestamp + '_' + max_timestamp + '.csv'
        #convert to csv with ';' separator
        family_table[output_columns].to_csv(output_file, sep=';', index=False)

    output_file = name_list['output_path']  + defaults_path +  '/family/family_' + min_timestamp + '_' + max_timestamp + '.txt'

    with open(output_file, 'w') as f:
        for uid, group in family_table.groupby('uid'):
            min_timestamp = group['timestamp'].min()
            max_timestamp = group['timestamp'].max()
            duration = group['duration'].iloc[0]
            header = f"FAMILY= {uid} - YEAR={min_timestamp.year} MONTH={min_timestamp.month} DAY={min_timestamp.day} HOUR={min_timestamp.hour:.2f}\n"
            f.write(header)
            
            # Prepare columns for the ASCII file
            output_columns_2 = output_columns.copy()
            output_columns_2.remove('duration')
            output_columns_2.remove('timestamp')
            
            #ALAN: ja converter no parquet
            # Convert TIME to hours, the original time are in minutes
            group['TIME_H'] = group['time'] / 60
            group.drop('time', axis=1, inplace=True)
            group = group.rename(columns={'TIME_H': 'time'})
            group2 = group[output_columns_2]
            
            # Write header based on the output_columns with 12 characters for each column
            header2 = ' '.join([f'{col:>12s}' for col in output_columns_2]) + '\n'
            f.write(header2)
            
            # Write data rows
            for _, row in group2.iterrows():
                row_data = []
                for col in output_columns_2:
                    value = row[col]
                    if isinstance(value, datetime):
                        formatted_value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, (int, float)):
                        formatted_value = f'{value:12.2f}'
                    elif isinstance(value, str):
                        formatted_value = f'{value:>12s}'
                    else:
                        formatted_value = f'{str(value):>12s}'
                    row_data.append(formatted_value)
                row_str = ' '.join(row_data)
                f.write(row_str + '\n')
                
            # Write footer (optional)
            footer = f"TOTAL TIME= {duration:.2f}\n\n"
            f.write(footer)
