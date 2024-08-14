import yaml
import json
from datetime import datetime
import subprocess
import os

def validate_yaml_syntax(yaml_content):
    try:
        yaml.safe_load(yaml_content)
        return 1  # Valid syntax
    except yaml.YAMLError as e:
        print(f"YAML syntax error: {e}")
        return 0  # Invalid syntax

def validate_kubernetes_semantics(yaml_content, kubeval_path="kubeval"):
    try:
        with open("temp.yaml", "w") as temp_file:
            temp_file.write(yaml_content)
        
        result = subprocess.run([kubeval_path, "temp.yaml"], capture_output=True, text=True)
        if result.returncode == 0:
            return 1  # Valid semantics
        else:
            print(f"Kubernetes semantic validation failed:\n{result.stdout}\n{result.stderr}")
            return 0  # Invalid semantics
    finally:
        os.remove("temp.yaml")

def validate_critical_key_values(original_yaml, generated_yaml, critical_fields):
    match_count = 0
    mismatch_count = 0
    for field in critical_fields:
        original_value = original_yaml.get(field)
        generated_value = generated_yaml.get(field)
        if original_value == generated_value:
            match_count += 1
        else:
            mismatch_count += 1
    return match_count, mismatch_count

def validate_kubectl_dry_run(yaml_content):
    try:
        with open("temp.yaml", "w") as temp_file:
            temp_file.write(yaml_content)
        
        result = subprocess.run(["kubectl", "apply", "--dry-run=client", "-f", "temp.yaml"], capture_output=True, text=True)
        return 1 if result.returncode == 0 else 0  # 1 for success, 0 for failure
    finally:
        os.remove("temp.yaml")

def load_yaml_from_file(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

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
    return results

def validate_configurations(original_file, zero_shot_file, few_shot_file, critical_fields):
    original_yaml = load_yaml_from_file(original_file)
    zero_shot_yaml = load_yaml_from_file(zero_shot_file)
    few_shot_yaml = load_yaml_from_file(few_shot_file)
    
    # Validate Zero-Shot Configuration
    zero_shot_results = validate_single_configuration(original_yaml, zero_shot_yaml, critical_fields, "Zero-Shot")
    
    # Validate Few-Shot Configuration
    few_shot_results = validate_single_configuration(original_yaml, few_shot_yaml, critical_fields, "Few-Shot")

    return zero_shot_results, few_shot_results

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
