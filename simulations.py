import pandas as pd
import numpy as np
from functions import get_iso_emission_rate, haversine, apply_braking_profile, detect_stops

# --- Config ---
DATA_FILE = 'combined_trips.csv'
data = pd.read_csv(DATA_FILE)

# PoD tuning constants (ISO 23795-3 / Newtonian)
ACCEL_THRESHOLD  = 0.5   # m/s² — above this, apply inertia penalty
ACCEL_PENALTY_K  = 0.8   # penalty scale per m/s² above threshold
GRADE_WEIGHT     = 5.0   # hill penalty scale (tunable)
GRADE_MIN_FACTOR = 0.5   # minimum fuel factor downhill

# === For the Stopping ===
# Stop detection
STOP_SPEED_THRESHOLD = 0.5    # m/s — below this = stopped
MIN_STOP_DURATION_S  = 2.0    # ignore GPS glitches shorter than this
IDLE_CO2_RATE_G_S    = 0.5    # grams CO2 per second while idling

# Braking kinematics
BRAKE_DECEL = 0.8    # m/s² — gentle, anticipatory
BRAKE_ACCEL = 0.6    # m/s² — smooth pull-away

def simulate(trip_id, n_profiles=10):
    """
    Simulate n driving profiles ranging from eco (alpha=0) to aggressive (alpha=1).

    Speed profiles are shaped as: recorded speed scaled by a per-profile factor,
    with stop events detected from the original trip injected into every profile.
    Eco profiles use anticipatory braking; aggressive profiles brake late and hard.

    CO2 is calculated per segment using:
      1. Baseline rate from WLTP class lookup (kg CO2/km)
      2. PoD acceleration penalty — bidirectional (penalises both hard
         acceleration and hard braking as wasted kinetic energy)
      3. PoD grade penalty (slope resistance)
      4. Idle CO2 added per stop event, scaled by recorded stop duration
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

    # --- 1. Segment distances (Haversine) ---
    trip_df['next_lat'] = trip_df['Latitude'].shift(-1)
    trip_df['next_lon'] = trip_df['Longitude'].shift(-1)
    trip_df['dist_m'] = haversine(
        trip_df['Latitude'].values,
        trip_df['Longitude'].values,
        trip_df['next_lat'].values,
        trip_df['next_lon'].values,
    )

    # --- 2. Road grade (smoothed elevation to suppress GPS noise) ---
    trip_df['elevation']      = trip_df['Altitude[m]'].rolling(window=5, center=True, min_periods=1).mean()
    trip_df['next_elevation'] = trip_df['elevation'].shift(-1)
    trip_df['delta_elev']     = trip_df['next_elevation'] - trip_df['elevation']
    trip_df['grade']          = (trip_df['delta_elev'] / trip_df['dist_m']).clip(-0.10, 0.10)

    trip_df = trip_df.dropna(subset=['dist_m', 'grade']).copy().reset_index(drop=True)

    emission_group = (
        trip_df['emission_group'].iloc[0]
        if 'emission_group' in trip_df.columns
        else 'low'
    )

    # --- 3. Detect stops from recorded trip (road-environment property) ---
    stops = detect_stops(trip_df)
    total_idle_co2_base = sum(s['duration_s'] * IDLE_CO2_RATE_G_S for s in stops)

    # Pre-compute grade penalty (same for all profiles — road doesn't change)
    grade_penalty = (1.0 + trip_df['grade'].values * GRADE_WEIGHT).clip(min=GRADE_MIN_FACTOR)

    results = []

    for i, alpha in enumerate(np.linspace(0, 1, n_profiles)):

        # --- 4. Base speed profile (eco drivers go slower, aggressive faster) ---
        sim_speed = (trip_df['Speed[m/s]'] * (0.85 + alpha * 0.35)).clip(lower=0.1).values.copy()

        # --- 5. Inject stop events with alpha-blended braking style ---
        for stop in stops:
            sim_speed = apply_braking_profile(sim_speed, stop['index']) 

        # --- 6. Segment travel time ---
        sim_dt = trip_df['dist_m'].values / np.where(sim_speed > 0, sim_speed, 0.1)

        # --- 7. Bidirectional acceleration penalty ---
        next_speed     = np.roll(sim_speed, -1)
        next_speed[-1] = sim_speed[-1]
        sim_accel      = (next_speed - sim_speed) / np.where(sim_dt > 0, sim_dt, 1e-6)

        accel_penalty = np.where(
            np.abs(sim_accel) > ACCEL_THRESHOLD,
            1.0 + (np.abs(sim_accel) - ACCEL_THRESHOLD) * ACCEL_PENALTY_K,
            1.0
        )

        # --- 8. Baseline CO2 from WLTP lookup ---
        base_co2_kg_per_km = np.array([
            get_iso_emission_rate(s, group=emission_group)
            for s in sim_speed
        ])

        # --- 9. Segment CO2 + idle penalty ---
        dist_km     = trip_df['dist_m'].values / 1000.0
        driving_co2 = dist_km * base_co2_kg_per_km * accel_penalty * grade_penalty * 1000.0

        # Idle CO2: eco drivers idle for the full recorded duration;
        # aggressive drivers idle less (they arrived later, stop is shorter for them)
        idle_co2 = total_idle_co2_base

        results.append({
            'Profile':    f"Profile {i+1:02d}",
            'Alpha':      round(float(alpha), 2),
            'Time (s)':   round(float(sim_dt.sum()), 1),
            'Dist (km)':  round(float(dist_km.sum()), 3),
            'CO2 (g)':    round(float(driving_co2.sum() + idle_co2), 1),
            'Idle CO2 (g)': round(idle_co2, 1),
            'Stops':      len(stops),
        })

    df = pd.DataFrame(results)
    df['g CO2/km'] = (df['CO2 (g)'] / df['Dist (km)']).round(1)
    return df