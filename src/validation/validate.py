import os
from validation.validate import validate_configurations, save_results_to_csv

# Paths to configuration files
original_file = "path/to/original.yaml"
zero_shot_file = "path/to/zero_shot.yaml"
few_shot_file = "path/to/few_shot.yaml"

# Critical fields to validate
critical_fields = ["replicas", "image", "ports"]

# Run validation
zero_shot_results, few_shot_results = validate_configurations(original_file, zero_shot_file, few_shot_file, critical_fields)

# Save the results to a CSV file
results_file = "results/validation_results.csv"
save_results_to_csv([zero_shot_results, few_shot_results], results_file)

print(f"Validation completed. Results saved to {results_file}.")


