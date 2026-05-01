import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import osmnx as ox

#loading gdf
df = pd.read_csv("combined_trips.csv")

gdf = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.Longitude, df.Latitude),
    crs="EPSG:4326"
)

# country divison
germany = gdf[gdf["country"] == "germany"]
aruba = gdf[gdf["country"] == "aruba"]

# 
germany.plot(markersize=1)
aruba.plot(markersize=1)

# bounding box from your data
north, south = germany.geometry.y.max(), germany.geometry.y.min()
east, west = germany.geometry.x.max(), germany.geometry.x.min()

G = ox.graph_from_bbox(north, south, east, west, network_type="drive")

fig, ax = ox.plot_graph(G, show=False, close=False)

germany.plot(ax=ax, markersize=1, color="red")