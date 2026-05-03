import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from functions import get_iso_emission_rate, get_elevation

#import data
data = pd.read_csv('combined_trips.csv')
trips = {
    "Rotenburg": "germany_2024_06_14_Passat Variant TSI_10_14_10_28_abb4c15a-83dc-4376-9711-1b718843ee98.csv",
    "Frankfurt": "germany_2025_10_30_Passat Variant TSI_19_33_19_46_2d2961c1-2e11-40b2-86f4-a55b1ca872bf.csv",
    "Stuttgart": "germany_2022_07_12_rg.samsung_07_46_07_58_2eca8f6d-d6b6-45bc-aa4a-7cd5615d0b0b.csv",
    "Oranjestad": "aruba_2025_10_21_dt885_19_27_12_26_4812fcb0-c0eb-4c74-958d-9b12a177181b",
    "Bubali": "aruba_2025_11_06_dt170_19_01_01_22_bb6f0a40-d888-4d53-b636-b5a8c044ba3b"
}

# simulation function
def simulate(trip_id, n_profiles=5):
    print(f"Running High-Fidelity Simulation for {trip_id[:20]}...")
    
    trip_df = data[data['trip'] == trip_id].sort_values('Time[ms]').copy()
    
    # Calculate Distance
    trip_df['next_lat'] = trip_df['Latitude'].shift(-1)
    trip_df['next_lon'] = trip_df['Longitude'].shift(-1)
    trip_df['dist_meters'] = np.sqrt(
        (trip_df['Latitude'] - trip_df['next_lat'])**2 + 
        (trip_df['Longitude'] - trip_df['next_lon'])**2
    ) * 111320
    
    # --- NEW: CALCULATE ROAD GRADE ---
    trip_df['elevation'] = trip_df.apply(lambda row: get_elevation(row['Latitude'], row['Longitude']), axis=1)
    trip_df['next_elevation'] = trip_df['elevation'].shift(-1)
    trip_df['delta_elevation'] = trip_df['next_elevation'] - trip_df['elevation']
    
    # Grade = rise / run (capped between -10% and +10% to prevent extreme outliers)
    trip_df['grade'] = (trip_df['delta_elevation'] / trip_df['dist_meters']).clip(-0.10, 0.10)
    
    trip_df = trip_df.dropna(subset=['dist_meters'])
    emission_group = trip_df['emission_group'].iloc[0] if 'emission_group' in trip_df.columns else 'low'

    results = []
    alphas = np.linspace(0, 1, n_profiles)
    
    for i, alpha in enumerate(alphas):
        # 1. Simulate Speeds
        v_eco = trip_df['Speed[m/s]'].clip(upper=12.0)
        v_fast = (trip_df['Speed[m/s]'] * 1.2).clip(upper=30.0) 
        sim_speed = (alpha * v_fast + (1 - alpha) * v_eco).clip(lower=0.1) # Avoid true zero for time division
        
        # --- NEW: CALCULATE ACCELERATION ---
        # dt = time to cover the distance at the simulated speed
        sim_dt = trip_df['dist_meters'] / sim_speed 
        
        # dv = difference in speed to the next point
        next_speed = sim_speed.shift(-1).fillna(sim_speed)
        sim_acceleration = (next_speed - sim_speed) / sim_dt
        
        # 2. Get Baseline CO2
        base_co2_rates = [get_iso_emission_rate(s, group=emission_group) for s in sim_speed]
        
        # --- NEW: APPLY PoD PENALTIES (Inertia + Gravity) ---
        # If accelerating rapidly (e.g., > 0.5 m/s^2), increase CO2 rate
        accel_penalty = np.where(sim_acceleration > 0.5, 1 + (sim_acceleration * 0.8), 1.0)
        
        # If going uphill (grade > 0), increase CO2. Downhill allows coasting.
        grade_penalty = 1 + (trip_df['grade'] * 5) # 5 is a tuning weight for how much hills hurt
        grade_penalty = grade_penalty.clip(lower=0.5) # You never use 0 fuel downhill unless it's an EV
        
        # Combine the penalties
        final_co2_rates = base_co2_rates * accel_penalty * grade_penalty
        
        # Calculate totals
        sim_emissions = (trip_df['dist_meters'] / 1000.0) * final_co2_rates
        
        results.append({
            'Profile_Name': f"Profile {i+1}",
            'Alpha': round(alpha, 2),
            'Time (s)': round(sim_dt.sum(), 2),
            'CO2 (g)': round(sum(sim_emissions), 2)
        })
        
    return pd.DataFrame(results)

# Run the test
df_hf_results = simulate("germany_2024_06_14_Passat Variant TSI_10_14_10_28_abb4c15a-83dc-4376-9711-1b718843ee98.csv", n_profiles=10)
print(df_hf_results.to_string(index=False))