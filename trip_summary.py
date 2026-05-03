from functions import get_iso_emission_rate
import pandas as pd 
import numpy as np

trips = {
    "Rotenburg":  "germany_2024_06_14_Passat Variant TSI_10_14_10_28_abb4c15a-83dc-4376-9711-1b718843ee98.csv",
    "Frankfurt":  "germany_2025_10_30_Passat Variant TSI_19_33_19_46_2d2961c1-2e11-40b2-86f4-a55b1ca872bf.csv",
    "Stuttgart":  "germany_2022_07_12_rg.samsung_07_46_07_58_2eca8f6d-d6b6-45bc-aa4a-7cd5615d0b0b.csv",
    "Oranjestad": "aruba_2025_10_21_dt885_19_27_12_26_4812fcb0-c0eb-4c74-958d-9b12a177181b",
    "Bubali":     "aruba_2025_11_06_dt170_19_01_01_22_bb6f0a40-d888-4d53-b636-b5a8c044ba3b"
}

data = pd.read_csv('combined_trips.csv')

def baseline(trips_dict):
    """
    Purely observational — no calculations, just sums of recorded columns.
 
    Distance, CO2, and time are all pre-computed in the dataset by the recording device.
    """
    records = []
 
    for name, trip_id in trips_dict.items():
        print(f"Computing baseline for {name}...")
 
        trip_df = (
            data[data['trip'] == trip_id]
            .sort_values('Time[ms]')
            .reset_index(drop=True)
        )
 
        if trip_df.empty:
            print(f"  WARNING: trip '{trip_id}' not found, skipping.")
            continue
 
        total_dist_km = trip_df['Distance'].sum() / 1000.0
        total_time_s  = (trip_df['Time[ms]'].iloc[-1] - trip_df['Time[ms]'].iloc[0]) / 1000.0
        total_co2_g   = trip_df['CO2[kg]'].sum() * 1000.0  # kg → g
 
        records.append({
            'Trip':      name,
            'Dist (km)': round(total_dist_km, 3),
            'Time (s)':  round(total_time_s, 1),
            'CO2 (g)':   round(total_co2_g, 1),
            'g CO2/km':  round(total_co2_g / total_dist_km, 1) if total_dist_km > 0 else None,
        })
 
    return pd.DataFrame(records)

# Run it
df_baseline = baseline(trips)
print("\nBaseline results:")
print(df_baseline.to_string(index=False))
df_baseline.to_csv('baseline_results.csv', index=False)
print("Baseline saved to baseline_results.csv")