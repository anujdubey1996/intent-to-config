import os
import pandas as pd
import requests
import time
from datetime import datetime

# Define paths
xlsx_file_path = "../inputs/LLM_Intents.xlsx"
zero_shot_folder = "../outputs/configurations/zero-shot/"
few_shot_folder = "../outputs/configurations/few-shot/"
log_dir = "../logs"
output_dir = "../outputs/configurations"

# Define the API endpoint URL
api_url = "http://localhost:8000/generate/"

# Ensure directories exist
os.makedirs(zero_shot_folder, exist_ok=True)
os.makedirs(few_shot_folder, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Log directories
prompt_log_dir = os.path.join(log_dir, "prompts")
response_log_dir = os.path.join(log_dir, "responses")
os.makedirs(prompt_log_dir, exist_ok=True)
os.makedirs(response_log_dir, exist_ok=True)

# Prompt template
prompt_template = """
Create a Kubernetes deployment workload configuration file based on the provided intent.

Intent: {intent}
"""

# Determine the log index
def get_next_log_index(log_dir, date_prefix):
    existing_logs = [f for f in os.listdir(log_dir) if f.startswith(date_prefix)]
    return len(existing_logs)

# Function to load the Excel file and return a list of intents and file paths
def load_intents_and_files(xlsx_file):
    df = pd.read_excel(xlsx_file)
    intents_and_files = df.to_dict(orient='records')
    return intents_and_files

# Function to run batch inferencing
def run_batch_inferencing(xlsx_file_path, zero_shot_folder, few_shot_folder):
    intents_and_files = load_intents_and_files(xlsx_file_path)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    total_items = len(intents_and_files)
    complete_count = 0
    print(f"Starting batch inferencing for {total_items} items...\n")

    for index, item in enumerate(intents_and_files, start=1):
        print("Processing: ", complete_count)
        complete_count += 1
        original_file = item['Deployment']
        intent = item['Intent']

        # Create the prompt by concatenating the intent to the template
        prompt = prompt_template.format(intent=intent)

        # Get the next log index
        log_index = get_next_log_index(prompt_log_dir, current_date)

        # Log filenames
        prompt_log_file = os.path.join(prompt_log_dir, f"{current_date}_{log_index}.txt")
        response_log_file = os.path.join(response_log_dir, f"{current_date}_{log_index}.txt")
        
        # Log the prompt
        with open(prompt_log_file, "w") as prompt_log:
            prompt_log.write(prompt)

        # Run zero-shot inference
        start_time = time.time()
        zero_shot_config = run_inference(prompt, response_log_file)
        elapsed_time = time.time() - start_time

        zero_shot_filename = os.path.basename(original_file).replace('.yaml', '_zs.yaml')
        zero_shot_file = os.path.join(zero_shot_folder, zero_shot_filename)
        
        if zero_shot_config:
            save_yaml(zero_shot_config, zero_shot_file)
            print(f"[{index}/{total_items}] Zero-shot configuration saved to {zero_shot_file} (Time: {elapsed_time:.2f} seconds)")

        # Run few-shot inference (modify the prompt or API call as needed for few-shot)
        start_time = time.time()
        few_shot_config = run_inference(prompt, response_log_file)
        elapsed_time = time.time() - start_time

        few_shot_filename = os.path.basename(original_file).replace('.yaml', '_fs.yaml')
        few_shot_file = os.path.join(few_shot_folder, few_shot_filename)
        
        if few_shot_config:
            save_yaml(few_shot_config, few_shot_file)
            print(f"[{index}/{total_items}] Few-shot configuration saved to {few_shot_file} (Time: {elapsed_time:.2f} seconds)\n")

    print(f"Batch inferencing completed for {total_items} items.")

def run_inference(prompt, response_log_file):
    start = time.time()

    # Define the request payload
    payload = {
        "prompt": prompt,
        "max_length": 5000  # Adjust the max length as needed
    }

    # Make the POST request to the API
    response = requests.post(api_url, json=payload)

    if response.status_code == 200:
        generated_config = response.json()["generated_code"]
        with open(response_log_file, "w") as response_log:
            response_log.write(generated_config)

        # Identify the start of the YAML configuration, which usually begins with "```yaml"
        yaml_start = generated_config.find("```yaml")

        if yaml_start != -1:
            # Extract the content starting from the first occurrence of "```yaml"
            yaml_content = generated_config[yaml_start + len("```yaml"):].strip()

            # Optionally remove trailing code block delimiter "```" if it exists
            yaml_end = yaml_content.find("```")
            if yaml_end != -1:
                yaml_content = yaml_content[:yaml_end].strip()
        else:
            # If "```yaml" is not found, the response might not contain valid YAML
            print("No YAML content found.")
            yaml_content = None

        end = time.time()
        print(f"Inference Time Taken: {end - start:.2f} seconds")

        return yaml_content
    else:
        print(f"Failed to generate configuration for prompt: {prompt}")
        print(f"Error: {response.status_code} - {response.text}")
        return None

def save_yaml(content, file_path):
    with open(file_path, 'w') as file:
        file.write(content)

if __name__ == "__main__":
    run_batch_inferencing(xlsx_file_path, zero_shot_folder, few_shot_folder)
