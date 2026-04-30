import pandas as pd
import folium

# 1. Load the Germany dataset
df_germany = pd.read_csv('germany_data/combined_vehicle_data.csv')

# 2. Clean the data (Drop rows missing GPS coordinates)
df_germany = df_germany.dropna(subset=['Latitude', 'Longitude'])

# 3. Sort by 'trip' and 'Time' so lines connect sequentially!
df_germany = df_germany.sort_values(by=['trip', 'Time[ms]'])

# 4. Find the center coordinates for the map
center_lat = df_germany['Latitude'].mean()
center_lon = df_germany['Longitude'].mean()

# 5. Initialize the Folium map with the 'CartoDB positron' style
germany_map = folium.Map(
    location=[center_lat, center_lon], 
    zoom_start=11, 
    tiles='CartoDB positron'  # This provides the bright/clean look
)

# 6. A distinct list of colors to iterate through
colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FF33A1', 
          '#33FFF5', '#FFA500', '#800080', '#008080', '#E31A1C']

# 7. Loop through each unique trip and plot the sequential line
unique_trips = df_germany['trip'].unique()
for i, trip in enumerate(unique_trips):
    # Filter dataset for the current trip
    trip_df = df_germany[df_germany['trip'] == trip]
    
    # Create a list of [Latitude, Longitude] pairs
    path_coords = trip_df[['Latitude', 'Longitude']].values.tolist()
    
    # Shorten the name so the tooltip hover isn't overwhelmingly long
    trip_name = str(trip)[:20] + "..."
    
    # Add the continuous line to the map
    folium.PolyLine(
        locations=path_coords,
        color=colors[i % len(colors)],
        weight=4,            # Thickness of the line
        opacity=0.8,         # Slight transparency so roads underneath are visible
        tooltip=trip_name    # Text that pops up when you hover over the line
    ).add_to(germany_map)

# 8. Save the resulting Folium map as an interactive HTML file
germany_map.save('germany_folium_map.html')
print("Successfully generated germany_folium_map.html!")