import pandas as pd

# Load the combined trips data
df = pd.read_csv('combined_trips.csv')

# Get the unique trip identifiers
unique_trips = df['trip'].unique()

# Count data points per trip for a quick summary
trip_summary = df['trip'].value_counts()

print(f"Total unique trips: {len(unique_trips)}")
print(trip_summary)