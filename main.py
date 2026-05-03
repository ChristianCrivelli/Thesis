from simulations import simulate

trips = {
    "Rotenburg":  "germany_2024_06_14_Passat Variant TSI_10_14_10_28_abb4c15a-83dc-4376-9711-1b718843ee98.csv",
    "Frankfurt":  "germany_2025_10_30_Passat Variant TSI_19_33_19_46_2d2961c1-2e11-40b2-86f4-a55b1ca872bf.csv",
    "Stuttgart":  "germany_2022_07_12_rg.samsung_07_46_07_58_2eca8f6d-d6b6-45bc-aa4a-7cd5615d0b0b.csv",
    "Oranjestad": "aruba_2025_10_21_dt885_19_27_12_26_4812fcb0-c0eb-4c74-958d-9b12a177181b",
    "Bubali":     "aruba_2025_11_06_dt170_19_01_01_22_bb6f0a40-d888-4d53-b636-b5a8c044ba3b"
}

# Manual Run
trip_name = "Rotenburg"
TRIP_ID = trips[trip_name]
df_results = simulate(TRIP_ID, n_profiles=100)
print(df_results.to_string(index=False))
df_results.to_csv(f'simulation_{trip_name.lower()}.csv', index=False)
print("Results saved to simulation_results.csv")