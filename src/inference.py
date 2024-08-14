import requests
import os
import re
import time
from datetime import datetime

# The API endpoint URL
api_url = "http://localhost:8000/generate/"

# Define the prompt with examples
prompt = """
Deploy an Nginx web server with high availability and basic health checks
"""
start = time.time()

# Define the request payload
payload = {
    "prompt": prompt,
    "max_length": 5000  # Adjust the max length as needed
}

# Make the POST request
response = requests.post(api_url, json=payload)

# Get the current date
current_date = datetime.now().strftime("%Y-%m-%d")

# Log directories
log_dir = "../logs"
prompt_log_dir = os.path.join(log_dir, "prompts")
response_log_dir = os.path.join(log_dir, "responses")
os.makedirs(prompt_log_dir, exist_ok=True)
os.makedirs(response_log_dir, exist_ok=True)

# Determine the log index
def get_next_log_index(log_dir, date_prefix):
    existing_logs = [f for f in os.listdir(log_dir) if f.startswith(date_prefix)]
    return len(existing_logs)

# Get the next log index
log_index = get_next_log_index(prompt_log_dir, current_date)

# Log filenames
prompt_log_file = os.path.join(prompt_log_dir, f"{current_date}_{log_index}.txt")
response_log_file = os.path.join(response_log_dir, f"{current_date}_{log_index}.txt")

# Log the prompt
with open(prompt_log_file, "w") as prompt_log:
    prompt_log.write(prompt)

# Check if the request was successful
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

    if yaml_content:
        print("Extracted YAML Content:")
        print(yaml_content)

        # Save the extracted YAML configuration to a file
        output_dir = "../outputs/configurations"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "java_microservice_deployment.yaml")
        
        with open(output_file, "w") as file:
            file.write(yaml_content)
        
        print(f"Configuration saved to {output_file}")
    else:
        print("Failed to extract a valid YAML configuration.")
else:
    print(f"Failed to generate configuration: {response.status_code}")
    print(response.text)

end = time.time()

print("Time Taken: ", end-start)
