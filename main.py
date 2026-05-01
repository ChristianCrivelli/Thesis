import pandas as pd
import networkx as nx
import folium
from functions import build_graph, get_path_metrics
from dijkstra import dijkstra as run_custom_dijkstra

# 1. Define the trips to analyze
trips = {
    "Rotenburg": "germany_2024_06_14_Passat Variant TSI_10_14_10_28_abb4c15a-83dc-4376-9711-1b718843ee98.csv",
    "Frankfurt": "germany_2025_10_30_Passat Variant TSI_19_33_19_46_2d2961c1-2e11-40b2-86f4-a55b1ca872bf.csv",
    "Stuttgart": "germany_2022_07_12_rg.samsung_07_46_07_58_2eca8f6d-d6b6-45bc-aa4a-7cd5615d0b0b.csv",
    "Oranjestad": "aruba_2025_10_21_dt885_19_27_12_26_4812fcb0-c0eb-4c74-958d-9b12a177181b",
    "Bubali": "aruba_2025_11_06_dt170_19_01_01_22_bb6f0a40-d888-4d53-b636-b5a8c044ba3b"
}

# Store all results for the CSV
