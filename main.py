import requests
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# GitHub API token and headers
#*********************************************************************************
GITHUB_TOKEN = '361677'      
CITY='moscow'    
FOLLOWERS=50     
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}

# Helper function to clean up company names
def clean_company_name(company):
    return company.strip().lstrip('@').upper() if company else None

# Function to fetch users from the GitHub API
def fetch_users(city=CITY, min_followers=FOLLOWERS):
    users = []
    page = 1
    while True:
        url = f"https://api.github.com/search/users?q=location:{city}+followers:>{min_followers}&page={page}&per_page=100"
        response = requests.get(url, headers=HEADERS)
        data = response.json()

        if 'items' not in data or not data['items']:
            break  # Stop if no users found

        for user in data['items']:
            # Get full user info
            user_url = user['url']
            user_response = requests.get(user_url, headers=HEADERS)
            user_data = user_response.json()

            # Extract required fields
            users.append({
                'login': user_data['login'],
                'name': user_data['name'],
                'company': clean_company_name(user_data['company']),
                'location': user_data['location'],
                'email': user_data['email'],
                'hireable': user_data['hireable'],
                'bio': user_data['bio'],
                'public_repos': user_data['public_repos'],
                'followers': user_data['followers'],
                'following': user_data['following'],
                'created_at': user_data['created_at'],
            })
        
        page += 1
        time.sleep(1)  # To avoid hitting rate limits

    return users

# Function to fetch repositories for a user with a max limit of 500
def fetch_repositories(user_login, max_repos=500):
    repositories = []
    page = 1
    while len(repositories) < max_repos:
        url = f"https://api.github.com/users/{user_login}/repos?sort=pushed&per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        repo_data = response.json()

        if not repo_data:
            break

        for repo in repo_data[:max_repos - len(repositories)]:
            repositories.append({
                'login': user_login,
                'full_name': repo['full_name'],
                'created_at': repo['created_at'],
                'stargazers_count': repo['stargazers_count'],
                'watchers_count': repo['watchers_count'],
                'language': repo['language'],
                'has_projects': repo['has_projects'],
                'has_wiki': repo['has_wiki'],
                'license_name': repo['license']['key'] if repo['license'] else None,
            })

        if len(repo_data) < 100:
            break

        page += 1
        time.sleep(0.5)  # Minimal delay to avoid hitting rate limits

    return repositories

# Function to save data to CSV
def save_to_csv(data, filename):
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def main():
    print("Fetching users...")
    users = fetch_users()
    save_to_csv(users, "users.csv")
    users_df = pd.read_csv('users.csv')

    # Check the data types and structure
    print(users_df.head())

    # Replace True/False with true/false in the hireable column
    users_df['hireable'] = users_df['hireable'].replace({True: 'true', False: 'false'})

    # Save the modified DataFrame back to the same CSV file
    users_df.to_csv('users.csv', index=False)

    # Check the data types and structure
    print(users_df.head())


    #print("Updated CSV file saved successfully.")
    print(f"Saved {len(users)} users to users.csv")

    print("Fetching repositories in parallel...")
    all_repositories = []

    # Use ThreadPoolExecutor to fetch repositories for multiple users concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_repositories, user["login"]): user for user in users}
        for future in as_completed(futures):
            user = futures[future]
            try:
                user_repos = future.result()
                all_repositories.extend(user_repos)
                print(f"Fetched {len(user_repos)} repositories for user {user['login']}")
            except Exception as e:
                print(f"Error fetching repositories for {user['login']}: {e}")
        

    save_to_csv(all_repositories, "repositories.csv")
    repositories_df = pd.read_csv('repositories.csv')

    # Check the data types and structure
    print(repositories_df.head())

    # Replace True/False with true/false
    repositories_df['has_projects'] = repositories_df['has_projects'].replace({True: 'true', False: 'false'})
    repositories_df['has_wiki'] = repositories_df['has_wiki'].replace({True: 'true', False: 'false'})

    # Save the modified DataFrame back to the same CSV file
    repositories_df.to_csv('repositories.csv', index=False)

    # Check the data types and structure
    print(repositories_df.head())

    #print("Updated CSV file saved successfully.")
    print(f"Saved {len(all_repositories)} repositories to repositories.csv")

if __name__ == "__main__":
    main()
