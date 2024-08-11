import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

def check_rate_limit():
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
    }
    url = 'https://api.github.com/rate_limit'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    rate_limit = response.json()['rate']['remaining']
    reset_time = response.json()['rate']['reset']
    return rate_limit, reset_time

def search_github_deployments(query, max_pages=10, delay=2):
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    results = []
    for page in range(1, max_pages + 1):
        rate_limit, reset_time = check_rate_limit()
        if rate_limit == 0:
            wait_time = reset_time - time.time() + 5
            print(f"Rate limit reached. Waiting for {wait_time / 60:.2f} minutes until reset...")
            time.sleep(wait_time)
        
        url = f'https://api.github.com/search/code?q={query}&per_page=100&page={page}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 403:
            wait_time = int(response.headers.get('Retry-After', delay))
            print(f"Rate limit exceeded. Retrying after {wait_time} seconds...")
            time.sleep(wait_time)
            continue
        
        response.raise_for_status()
        items = response.json()['items']
        results.extend(items)
        if len(items) < 100:
            break
        time.sleep(delay)
    return results

def download_file_content(item):
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3.raw',
    }
    file_url = item['html_url'].replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
    response = requests.get(file_url, headers=headers)
    response.raise_for_status()
    return response.text

def is_deployment_only(file_content):
    helm_keywords = ['{{', '}}', '.Values', '.Release', 'helm.sh/chart', 'heritage: Helm', 'releaseName', 'Chart.yaml']
    non_deployment_kinds = ['Service', 'Namespace', 'ConfigMap', 'Secret', 'Ingress', 'PersistentVolume', 'PersistentVolumeClaim', 'Job', 'DaemonSet', 'StatefulSet', 'HorizontalPodAutoscaler', 'CronJob']
    
    lines = file_content.split('\n')
    is_deployment = False
    
    for line in lines:
        stripped_line = line.strip()
        
        if any(keyword in stripped_line for keyword in helm_keywords):
            return False
        
        if stripped_line.startswith('kind:'):
            if 'Deployment' in stripped_line:
                is_deployment = True
            else:
                return False
        
        if any(kind in stripped_line for kind in non_deployment_kinds):
            return False
    
    return is_deployment

queries = [
    'apiVersion: apps/v1 kind: Deployment language:yaml',
    'apiVersion: apps/v1beta1 kind: Deployment language:yaml',
    'kind: Deployment filename:deployment.yaml language:yaml',
    'kind: Deployment path:deployments/ language:yaml',
]

output_dir = '../inputs/configurations'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

id = 0
for query in queries:
    results = search_github_deployments(query, max_pages=10)
    print(f"Found {len(results)} results for query: {query}")
    for idx, item in enumerate(results):
        print("__________________________________________________________________________________________________")
        file_content = download_file_content(item)
        if is_deployment_only(file_content):
            file_name = f"deployment_{id+1}.yaml"
            id += 1
            with open(os.path.join(output_dir, file_name), 'w') as f:
                f.write(file_content)
            print(f"Saved {file_name} to {output_dir}")
        else:
            print(f"Skipped {item['name']} as it contains non-Deployment configurations or Helm templates")
        print("__________________________________________________________________________________________________")
