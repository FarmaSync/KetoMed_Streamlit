
import pandas as pd

# === CONFIGURATION ===
input_file = "labeling\hulpstof_beoordelingsbestand_KetoMed_v20241230.csv"     # Path to your dataset
output_file = "sample.csv"  # File to save the random sample
sample_size = 25            # Number of rows to extract
random_seed = 42            # Set for reproducibility (optional)

# === READ DATASET ===
df = pd.read_csv(input_file, sep=';', encoding='latin1')

# === EXTRACT RANDOM SAMPLE ===
sample_df = df.sample(n=sample_size, random_state=random_seed)

# === SAVE TO NEW FILE ===
sample_df.to_csv(output_file, index=False)

#Sample df to clipboard for excel
sample_df.to_clipboard(index=False)

print(f"✅ Extracted {sample_size} random rows and saved to '{output_file}'")
