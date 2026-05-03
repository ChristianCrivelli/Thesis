import pandas as pd
import networkx as nx
import numpy as np
import requests

# load csv
data = pd.read_csv('combined_trips.csv')
calib = pd.read_csv('custom_calibration_lookup.csv')

# build graph
def build_graph(trip_id, imposed_speed_limit=None):
    trip_df = data[data['trip'] == trip_id].sort_values('Time[ms]')
    G = nx.DiGraph()
    
    nodes_list = []
    for i, row in trip_df.iterrows():
        node_id = (row['Latitude'], row['Longitude'])
        G.add_node(node_id, pos=(row['Longitude'], row['Latitude']))
        nodes_list.append((node_id, row['Speed[m/s]'], row.get('emission_group', 'low')))

    for j in range(len(nodes_list) - 1):
        u_data, v_data = nodes_list[j], nodes_list[j+1]
        u, recorded_speed, group = u_data[0], u_data[1], u_data[2]
        v = v_data[0]
        
        # Calculate Distance (using Euclidean as proxy for small segments)
        dist = np.sqrt((u[0]-v[0])**2 + (u[1]-v[1])**2) * 111320 # approx meters
        
        # Determine Speed to use for Weights
        speed = recorded_speed if recorded_speed > 0 else 1.0 # Avoid div by zero
        if imposed_speed_limit:
            speed = min(speed, imposed_speed_limit)
        
        # Calculate Weights
        time_weight = dist / speed
        co2_rate = get_iso_emission_rate(speed, group)
        emission_weight = (dist / 1000.0) * co2_rate # distance in km * co2/km
        
        G.add_edge(u, v, 
                   distance=dist, 
                   time=time_weight, 
                   emissions=emission_weight,
                   speed=speed)
                   
    return G

# get wltp class
def get_wltp_class(speed_ms):
    if speed_ms <= 8.33: return 'Low'
    elif speed_ms <= 13.89: return 'Medium'
    elif speed_ms <= 19.44: return 'High'
    else: return 'Extra-High'

# get emission rate
def get_iso_emission_rate(speed_ms, group='low'):
    wltp = get_wltp_class(speed_ms)
    match = calib[(calib['wltp_class'] == wltp) & (calib['emission_group'] == group)]
    if not match.empty:
        return match.iloc[0]['co2_per_km']
    return calib['co2_per_km'].mean()

def get_path_metrics(G, path):
    totals = {'distance': 0.0, 'time': 0.0, 'emissions': 0.0}
    for i in range(len(path) - 1):
        u, v = path[i], path[i+1]
        edge_data = G[u][v]
        totals['distance'] += edge_data['distance']
        totals['time'] += edge_data['time']
        totals['emissions'] += edge_data['emissions']
    return totals