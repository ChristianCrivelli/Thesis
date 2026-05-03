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

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in metres
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

# === For the Stopping FUnctions ===
# Stop detection
STOP_SPEED_THRESHOLD = 0.5    # m/s — below this = stopped
MIN_STOP_DURATION_S  = 2.0    # ignore GPS glitches shorter than this
IDLE_CO2_RATE_G_S    = 0.5    # grams CO2 per second while idling

# Braking kinematics
BRAKE_DECEL = 0.8    # m/s² — gentle, anticipatory
BRAKE_ACCEL = 0.6    # m/s² — smooth pull-away


def detect_stops(trip_df):
    """
    Identify stop events from the recorded trip by finding contiguous
    segments where speed drops below STOP_SPEED_THRESHOLD for at least
    MIN_STOP_DURATION_S seconds. These represent real-world stopping events
    (traffic lights, stop signs, congestion) that all simulated profiles
    must respect, since they are a property of the road environment,
    not the driver.

    Returns a list of dicts:
        index      — row index in trip_df where the stop begins
        duration_s — how long the stop lasts (from recorded data)
    """
    stops = []
    in_stop = False
    start_i = None
    start_time_ms = None

    speeds = trip_df['Speed[m/s]'].values
    times  = trip_df['Time[ms]'].values

    for i in range(len(trip_df)):
        is_stopped = speeds[i] < STOP_SPEED_THRESHOLD

        if is_stopped and not in_stop:
            in_stop = True
            start_i = i
            start_time_ms = times[i]

        elif not is_stopped and in_stop:
            duration_s = (times[i - 1] - start_time_ms) / 1000.0
            if duration_s >= MIN_STOP_DURATION_S:
                stops.append({
                    'index':      start_i,
                    'duration_s': duration_s,
                })
            in_stop = False

    # Handle trip ending while still stopped
    if in_stop:
        duration_s = (times[-1] - start_time_ms) / 1000.0
        if duration_s >= MIN_STOP_DURATION_S:
            stops.append({'index': start_i, 'duration_s': duration_s})

    return stops


def apply_braking_profile(sim_speed, stop_idx, seg_len_m=10.0):
    # No alpha parameter anymore
    decel = BRAKE_DECEL
    accel = BRAKE_ACCEL

    look_back = max(0, stop_idx - 5)
    approach_speed = float(np.mean(sim_speed[look_back:stop_idx])) if stop_idx > 0 else 1.0
    approach_speed = max(approach_speed, 0.5)

    n_brake = max(1, int(approach_speed**2 / (2 * decel * seg_len_m)))
    n_accel = max(1, int(approach_speed**2 / (2 * accel * seg_len_m)))

    for j in range(n_brake):
        idx = stop_idx - n_brake + j
        if 0 <= idx < len(sim_speed):
            sim_speed[idx] = max(0.1, approach_speed * (j + 1) / n_brake)

    if 0 <= stop_idx < len(sim_speed):
        sim_speed[stop_idx] = 0.1

    for j in range(n_accel):
        idx = stop_idx + 1 + j
        if 0 <= idx < len(sim_speed):
            sim_speed[idx] = max(0.1, approach_speed * (j + 1) / n_accel)

    return sim_speed
