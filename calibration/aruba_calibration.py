import pandas as pd
import glob
import os

#germany
germany = pd.read_csv("combined_vehicle_data.csv")
germany["source"] = "germany"


#aruba
aruba_path = "path/to/arruba_data"

files = glob.glob(os.path.join(aruba_path, "*.csv"))

aruba_dfs = []

for file in files:
    df = pd.read_csv(file)
    df["source"] = "aruba"
    df["source_file"] = os.path.basename(file)
    aruba_dfs.append(df)

aruba = pd.concat(aruba_dfs, ignore_index=True)

#Combine Datasets
