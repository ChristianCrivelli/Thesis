import pandas as pd

def perform_emission_calibration(file_path):
    # 1. Load your dataset
    df = pd.read_csv(file_path)

    # 2. Define WLTP Speed Classes (converted from km/h to m/s)
    # Low: 0-30 km/h | Medium: 30-50 km/h | High: 50-70 km/h | Extra-High: >70 km/h
    def classify_wltp(speed_ms):
        if speed_ms <= 8.33:
            return 'Low'
        elif speed_ms <= 13.89:
            return 'Medium'
        elif speed_ms <= 19.44:
            return 'High'
        else:
            return 'Extra-High'

    # 3. Apply classification to every row
    df['wltp_class'] = df['Speed[m/s]'].apply(classify_wltp)

    # 4. Data Cleaning
    # Remove rows where fuel or distance is missing or zero to avoid division errors
    df_clean = df.dropna(subset=['Fuel[l]', 'Distance'])
    df_clean = df_clean[df_clean['Distance'] > 0]

    # 5. Group by Driving Style (emission_group) and Road Type (wltp_class)
    # We aggregate the totals to get a statistically significant average per class
    calibration = df_clean.groupby(['emission_group', 'wltp_class']).agg(
        total_fuel_l=('Fuel[l]', 'sum'),
        total_dist_m=('Distance', 'sum'),
        avg_speed_ms=('Speed[m/s]', 'mean'),
        sample_count=('Time[ms]', 'count')
    ).reset_index()

    # 6. Calculate the Final Emission Rates (Liters per Kilometer)
    # Formula: (Total Fuel / Total Distance in meters) * 1000
    calibration['fuel_per_km'] = (calibration['total_fuel_l'] / calibration['total_dist_m']) * 1000
    
    # Calculate CO2 per km (Standard factor: 2.4 kg per Liter of fuel)
    calibration['co2_per_km'] = calibration['fuel_per_km'] * 2.4

    return calibration

# Execution
calibration_table = perform_emission_calibration('combined_vehicle_data.csv')

# Display the results
print("--- EMPIRICAL EMISSION CALIBRATION TABLE ---")
print(calibration_table[['emission_group', 'wltp_class', 'fuel_per_km', 'avg_speed_ms']])

# Optional: Save for your routing model
calibration_table.to_csv('emission_calibration_lookup.csv', index=False)