import os
import pandas as pd
import requests
import time
from datetime import datetime

# Define paths
xlsx_file_path = "../inputs/LLM_Intents.xlsx"
few_shot_folder = "../outputs/configurations/few-shot/"
log_dir = "../logs"
output_dir = "../outputs/configurations"
examples_folder = "../inputs/configurations/"

# Define the API endpoint URL
api_url = "http://localhost:8000/generate/"

# Ensure directories exist
os.makedirs(few_shot_folder, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# Log directories
prompt_log_dir = os.path.join(log_dir, "prompts")
response_log_dir = os.path.join(log_dir, "responses")
os.makedirs(prompt_log_dir, exist_ok=True)
os.makedirs(response_log_dir, exist_ok=True)

# Few-shot template with examples and corresponding intents
few_shot_template = """
Here are some examples of Kubernetes deployment configurations based on intent:

{examples}

Now, based on the following intent, generate the corresponding Kubernetes deployment configuration:

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

# Function to load the specific intent for a given filename from the Excel file
def load_filename_to_intent_map(xlsx_file, filename):
    df = pd.read_excel(xlsx_file)
    intent_row = df[df['Deployment'] == filename]
    if not intent_row.empty:
        return intent_row['Intent'].values[0]
    else:
        return "Unknown Intent"

# Function to load examples and their intents for few-shot learning
def load_few_shot_examples_with_intents(files):
    examples = []
    for file in files:
        filename = os.path.basename(file)
        intent = load_filename_to_intent_map(xlsx_file_path, filename)
        with open(file, 'r') as f:
            example_content = f.read()
            examples.append(f"Intent: {intent}\nConfiguration:\n{example_content}")
    return "\n\n".join(examples)

# Function to run batch inferencing
def run_batch_inferencing(xlsx_file_path, few_shot_folder):
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    intents_and_files = load_intents_and_files(xlsx_file_path)
    total_items = len(intents_and_files)
    complete_count = 0
    print(f"Starting batch inferencing for {total_items} items...\n")

    for index, item in enumerate(intents_and_files, start=1):
        print(f"Processing: {complete_count}")
        complete_count += 1
        original_file = item['Deployment']
        intent = item['Intent']

        # Get the next log index
        log_index = get_next_log_index(prompt_log_dir, current_date)

        # Log filenames
        prompt_log_file = os.path.join(prompt_log_dir, f"{current_date}_{log_index}.txt")
        response_log_file = os.path.join(response_log_dir, f"{current_date}_{log_index}.txt")
        
        # Example files and their corresponding intents for few-shot learning
        example_files = [
            "deployment_8.yaml",
            "deployment_19.yaml",
            "deployment_12.yaml",
            "deployment_129.yaml",
            "deployment_151.yaml"
        ]
        example_files = [os.path.join(examples_folder, ef) for ef in example_files]
        few_shot_examples = load_few_shot_examples_with_intents(example_files)

        # Create the prompt by including examples and the intent
        prompt = few_shot_template.format(examples=few_shot_examples, intent=intent)

        # Log the prompt
        with open(prompt_log_file, "w") as prompt_log:
            prompt_log.write(prompt)

        # Run few-shot inference
        start_time = time.time()
        few_shot_config = run_inference(prompt, response_log_file)
        elapsed_time = time.time() - start_time

        few_shot_filename = os.path.basename(original_file).replace('.yaml', '_fs.yaml')
        few_shot_file = os.path.join(few_shot_folder, few_shot_filename)
        
        if few_shot_config:
            save_yaml(few_shot_config, few_shot_file)
            print(f"[{index}/{total_items}] Few-shot configuration saved to {few_shot_file} (Time: {elapsed_time:.2f} seconds)\n")

    print(f"Batch inferencing completed for {total_items} items.")


    start = time.time()

    # Define the request payload
    payload = {
        "prompt": prompt,
        "max_length": 20000  # Adjust the max length as needed
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

def run_inference(prompt, response_log_file):
    start = time.time()

    # Define the request payload
    payload = {
        "prompt": prompt,
        "max_length": 20000  # Adjust the max length as needed
    }

    # Make the POST request to the API
    response = requests.post(api_url, json=payload)

    if response.status_code == 200:
        generated_config = response.json()["generated_code"]
        with open(response_log_file, "w") as response_log:
            response_log.write(generated_config)

        # Find the last occurrence of "Intent" and extract the content after it
        last_intent_position = generated_config.rfind("Intent")

        if last_intent_position != -1:
            # Extract content after the last "Intent"
            yaml_content = generated_config[last_intent_position:].strip()

            # Optionally, identify the start of the YAML configuration
            yaml_start = yaml_content.find("```yaml")

            if yaml_start != -1:
                # Extract the content starting from the first occurrence of "```yaml"
                yaml_content = yaml_content[yaml_start + len("```yaml"):].strip()

                # Optionally remove trailing code block delimiter "```" if it exists
                yaml_end = yaml_content.find("```")
                if yaml_end != -1:
                    yaml_content = yaml_content[:yaml_end].strip()
            else:
                print("No YAML content found after the last Intent.")
                yaml_content = None
        else:
            print("No 'Intent' found in the generated content.")
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
    run_batch_inferencing(xlsx_file_path, few_shot_folder)
