import pandas as pd
import folium
import glob
import os

# 1. Gather all Aruba CSV files
aruba_files = glob.glob('aruba_data/2025_*.csv')

# 2. Initialize the map centered around Aruba's approximate coordinates
aruba_map = folium.Map(location=[12.51, -69.96], zoom_start=12, tiles='CartoDB positron')

# A list of colors to differentiate the trips
colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FF33A1', '#33FFF5', "#483A76", "#83DE9C", "#5C131B", "#B8538E"]

# 3. Loop through each file and add its trajectory to the map
for i, file in enumerate(aruba_files):
    df = pd.read_csv(file)
    df = df.dropna(subset=['Latitude', 'Longitude'])
    
    if not df.empty:
        # Sort by time
        df = df.sort_values(by='Time[ms]')
        
        # Create a list of (Latitude, Longitude) tuples
        path_coords = list(zip(df['Latitude'], df['Longitude']))
        
        # Extract a clean name for the tooltip
        trip_name = os.path.basename(file).split('_dt')[0]
        
        # Add the line to the map
        folium.PolyLine(
            locations=path_coords,
            color=colors[i % len(colors)],
            weight=4,           # Line thickness
            opacity=0.8,        # Line transparency
            tooltip=trip_name   # Text shown when hovering over the line
        ).add_to(aruba_map)

# 4. Save to HTML
aruba_map.save('my_aruba_folium_map.html')
print("Map successfully saved! Open 'my_aruba_folium_map.html' in your browser.")