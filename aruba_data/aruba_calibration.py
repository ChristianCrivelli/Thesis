import pandas as pd
import numpy as np
import glob
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def get_full_aruba_model(folder_path):
    trip_results = []
    # Adjust path to match your actual folder
    files = glob.glob(os.path.join(folder_path, "*.csv"))

    # STEP 1: Extract signatures from every file
    for f in files:
        if not os.path.isfile(f): continue
        try:
            df = pd.read_csv(f).dropna(subset=['Distance', 'Fuel[l]'])
            dist = df['Distance'].sum()
            if dist < 500: continue # Skip very short logs
            
            # Calculate RPA for clustering
            df['accel_pos'] = df['Speed[m/s]'].diff().clip(lower=0)
            rpa = (df['Speed[m/s]'] * df['accel_pos']).sum() / dist
            fuel_intensity = (df['Fuel[l]'].sum() / dist) * 1000
            
            trip_results.append({
                'RPA': rpa,
                'fuel_intensity': fuel_intensity,
                'df': df
            })
        except Exception as e:
            print(f"Error reading {f}: {e}")

    if not trip_results:
        print("No files processed. Check folder path.")
        return None

    # STEP 2: Cluster trips into High and Low
    summary_df = pd.DataFrame(trip_results)
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(summary_df[['RPA', 'fuel_intensity']])
    
    kmeans = KMeans(n_clusters=2, random_state=42, n_init=10).fit(scaled_data)
    summary_df['cluster'] = kmeans.labels_
    
    high_cluster = summary_df.groupby('cluster')['fuel_intensity'].mean().idxmax()
    summary_df['group'] = summary_df['cluster'].apply(lambda x: 'high' if x == high_cluster else 'low')

    # STEP 3: Create detailed calibrations
    def classify_wltp(s):
        if s <= 8.33: return 'Low'
        elif s <= 13.89: return 'Medium'
        elif s <= 19.44: return 'High'
        else: return 'Extra-High'

    final_calib = []
    for group in ['high', 'low']:
        group_data = summary_df[summary_df['group'] == group]
        if group_data.empty: continue
        
        combined_df = pd.concat(list(group_data['df']))
        combined_df['wltp_class'] = combined_df['Speed[m/s]'].apply(classify_wltp)
        
        # New aggregation including all your requested columns
        stats = combined_df.groupby('wltp_class').agg(
            total_fuel_l=('Fuel[l]', 'sum'),
            total_dist_m=('Distance', 'sum'),
            avg_speed_ms=('Speed[m/s]', 'mean'),
            sample_count=('Time[ms]', 'count')
        ).reset_index()
        
        # Calculate derived metrics
        stats['fuel_per_km'] = (stats['total_fuel_l'] / stats['total_dist_m']) * 1000
        stats['co2_per_km'] = stats['fuel_per_km'] * 2.4
        stats['emission_group'] = group
        
        final_calib.append(stats)

    return pd.concat(final_calib)

# --- EXECUTION ---
# Change './aruba_data' to your actual folder name
calibration_results = get_full_aruba_model('./aruba_data')

if calibration_results is not None:
    # Save to CSV with all columns
    calibration_results.to_csv('aruba_emission_calibration.csv', index=False)
    print("Detailed Aruba calibration saved to 'aruba_emission_calibration.csv'")
    print(calibration_results)