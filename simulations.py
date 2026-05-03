import pandas as pd
import numpy as np
from functions import get_iso_emission_rate

# --- Config ---
DATA_FILE = 'combined_trips.csv'
data = pd.read_csv(DATA_FILE)

# PoD tuning constants (ISO 23795-3 / Newtonian)
ACCEL_THRESHOLD  = 0.5   # m/s² — above this, apply inertia penalty
ACCEL_PENALTY_K  = 0.8   # penalty scale per m/s² above threshold
GRADE_WEIGHT     = 5.0   # hill penalty scale (tunable)
GRADE_MIN_FACTOR = 0.5   # minimum fuel factor downhill (not zero — engine still runs)


def simulate(trip_id, n_profiles=10):
    """
    Simulate n driving profiles ranging from eco (alpha=0) to aggressive (alpha=1).

    Each profile blends:
      - eco speed  : recorded speed clipped to 12 m/s (~43 km/h)
      - fast speed : recorded speed * 1.2, clipped to 30 m/s (~108 km/h)

    CO2 is calculated per segment using:
      1. Baseline rate from WLTP class lookup (kg CO2/km)
      2. PoD acceleration penalty (inertia force)
      3. PoD grade penalty (slope resistance)

    Units throughout:
      distance  → metres  (converted to km for CO2 calc)
      time      → seconds
      CO2       → grams   (calibration is kg/km → converted here)
    """
    print(f"\nSimulating: {trip_id[:50]}...")

    trip_df = (
        data[data['trip'] == trip_id]
        .sort_values('Time[ms]')
        .copy()
        .reset_index(drop=True)
    )

    if trip_df.empty:
        raise ValueError(f"Trip '{trip_id}' not found in dataset.")

    # --- 1. Segment distances (Euclidean, degrees → metres) ---
    trip_df['next_lat'] = trip_df['Latitude'].shift(-1)
    trip_df['next_lon'] = trip_df['Longitude'].shift(-1)
    trip_df['dist_m'] = (
        np.sqrt(
            (trip_df['Latitude']  - trip_df['next_lat'])**2 +
            (trip_df['Longitude'] - trip_df['next_lon'])**2
        ) * 111_320
    )

    # --- 2. Road grade via elevation API (vectorised — one call for whole trip) ---
    trip_df['elevation'] = trip_df['Altitude']
    trip_df['next_elevation'] = trip_df['elevation'].shift(-1)
    trip_df['delta_elev']     = trip_df['next_elevation'] - trip_df['elevation']

    # grade = rise/run, capped at ±10 % to avoid GPS noise blowup
    trip_df['grade'] = (trip_df['delta_elev'] / trip_df['dist_m']).clip(-0.10, 0.10)

    # Drop the last row (no next point → NaN distances/grades)
    trip_df = trip_df.dropna(subset=['dist_m', 'grade']).copy()

    emission_group = (
        trip_df['emission_group'].iloc[0]
        if 'emission_group' in trip_df.columns
        else 'low'
    )

    # Pre-compute grade penalty — same for all profiles (road doesn't change)
    grade_penalty = (1.0 + trip_df['grade'].values * GRADE_WEIGHT).clip(min=GRADE_MIN_FACTOR)

    results = []

    for i, alpha in enumerate(np.linspace(0, 1, n_profiles)):

        # --- 3. Simulated speed profile ---
        v_eco  = trip_df['Speed[m/s]'].clip(upper=12.0)
        v_fast = (trip_df['Speed[m/s]'] * 1.2).clip(upper=30.0)
        sim_speed = ((alpha * v_fast) + ((1 - alpha) * v_eco)).clip(lower=0.1)

        # --- 4. Segment travel time ---
        sim_dt = trip_df['dist_m'].values / sim_speed.values   # seconds

        # --- 5. Acceleration (PoD: inertia force proxy) ---
        next_speed   = np.roll(sim_speed.values, -1)
        next_speed[-1] = sim_speed.values[-1]                  # last point: no change
        sim_accel    = (next_speed - sim_speed.values) / np.where(sim_dt > 0, sim_dt, 1e-6)

        accel_penalty = np.where(
            sim_accel > ACCEL_THRESHOLD,
            1.0 + (sim_accel - ACCEL_THRESHOLD) * ACCEL_PENALTY_K,
            1.0
        )

        # --- 6. Baseline CO2 rates from WLTP lookup (kg/km) ---
        base_co2_kg_per_km = np.array([
            get_iso_emission_rate(s, group=emission_group)
            for s in sim_speed.values
        ])

        # --- 7. Final CO2 per segment (grams) ---
        # dist in km × base_rate (kg/km) × penalties × 1000 → grams
        dist_km        = trip_df['dist_m'].values / 1000.0
        final_co2_g    = dist_km * base_co2_kg_per_km * accel_penalty * grade_penalty * 1000.0

        results.append({
            'Profile':   f"Profile {i+1:02d}",
            'Alpha':     round(float(alpha), 2),
            'Time (s)':  round(float(sim_dt.sum()), 1),
            'Dist (km)': round(float(dist_km.sum()), 3),
            'CO2 (g)':   round(float(final_co2_g.sum()), 1),
        })

    df = pd.DataFrame(results)
    df['g CO2/km'] = (df['CO2 (g)'] / df['Dist (km)']).round(1)

    return df
