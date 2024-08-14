import yaml
from utils import validate_yaml_syntax, validate_kubernetes_semantics, validate_critical_key_values, validate_kubectl_dry_run
import json
from datetime import datetime

def load_yaml_from_file(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def validate_configurations(original_file, zero_shot_file, few_shot_file, critical_fields):
    original_yaml = load_yaml_from_file(original_file)
    zero_shot_yaml = load_yaml_from_file(zero_shot_file)
    few_shot_yaml = load_yaml_from_file(few_shot_file)
    
    # Validate Zero-Shot Configuration
    zero_shot_results = validate_single_configuration(original_yaml, zero_shot_yaml, critical_fields, "Zero-Shot")
    
    # Validate Few-Shot Configuration
    few_shot_results = validate_single_configuration(original_yaml, few_shot_yaml, critical_fields, "Few-Shot")

    return zero_shot_results, few_shot_results

def validate_single_configuration(original_yaml, generated_yaml, critical_fields, method):
    generated_yaml_str = yaml.dump(generated_yaml)
    
    # Step 1: Syntax Validation
    syntax_result = validate_yaml_syntax(generated_yaml_str)

    # Step 2: Semantic Validation
    semantic_result = validate_kubernetes_semantics(generated_yaml_str)

    # Step 3: Critical Key-Value Pair Validation
    key_value_matches, key_value_mismatches = validate_critical_key_values(original_yaml, generated_yaml, critical_fields)

    # Step 4: Kubectl Dry Run Validation
    kubectl_result = validate_kubectl_dry_run(generated_yaml_str)

    # Collect results
    results = {
        "method": method,
        "syntax_result": syntax_result,               # 1 for valid, 0 for invalid
        "semantic_result": semantic_result,           # 1 for valid, 0 for invalid
        "key_value_matches": key_value_matches,       # Number of matches
        "key_value_mismatches": key_value_mismatches, # Number of mismatches
        "kubectl_result": kubectl_result              # 1 for success, 0 for failure
    }

    # Log the results
    log_results("validation/logs/validation_log.json", results)

    return results

def log_results(log_file, results):
    with open(log_file, "a") as log:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        log.write(json.dumps(log_entry) + "\n")

def save_results_to_csv(results, csv_file):
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        if not file_exists:
            writer.writeheader()
        for result in results:
            writer.writerow(result)
