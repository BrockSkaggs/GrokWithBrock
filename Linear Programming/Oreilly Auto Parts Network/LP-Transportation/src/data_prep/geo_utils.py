import numpy as np

def haversine_vectorized(df, start_lat:str, start_lon:str, end_lat:float, end_lon:float):
    # 1. Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [df[start_lat], df[start_lon], end_lat, end_lon])

    # 2. Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))

    # 3. Radius of Earth in kilometers is 6371, for miles it is 3956
    r = 3956
    return c * r

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 3956  # Radius of earth in miles. Use 6371 for kilometers
    return c * r