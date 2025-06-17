# iam_policy_reporter.py
#
# A script to process Google Cloud IAM policy data exported from the Cloud Asset Inventory.
# It enriches the raw data with human-readable names for projects and folders,
# expands member lists, and produces a clean, comprehensive CSV report.
#
# Copyright 2025
# Released under the MIT License

import json
import csv
import subprocess
import os
import sys
import re
from typing import Dict

# --- Configuration ---
# Update these values before running the script.

# The name of the JSON file exported from the `gcloud asset` command.
INPUT_JSON = 'iam_policies.json'
# The name of the final CSV report that will be generated.
OUTPUT_CSV = 'iam_report_final.csv'
# -------------------

# In-memory cache to store looked-up folder names and avoid redundant API calls.
folder_cache: Dict[str, str] = {}

def get_folder_name(folder_id_str: str) -> str:
    """
    Looks up a folder's display name from its full ID string (e.g., 'folders/12345').
    Uses an in-memory cache to dramatically speed up the process on large exports.

    Args:
        folder_id_str: The full ID of the folder.

    Returns:
        The folder's display name or a status string if not found.
    """
    if folder_id_str in folder_cache:
        return folder_cache[folder_id_str]
    
    try:
        folder_id = folder_id_str.split('/')[1]
        result = subprocess.run(
            ['gcloud', 'resource-manager', 'folders', 'describe', folder_id, '--format=value(displayName)'],
            capture_output=True, text=True, check=True, encoding='utf-8'
        )
        name = result.stdout.strip()
        folder_cache[folder_id_str] = name
        return name
    except (subprocess.CalledProcessError, IndexError):
        # Cache failures as well to prevent retries
        folder_cache[folder_id_str] = "<not found>"
        return "<not found>"

def main():
    """
    Main function to parse the JSON asset data and generate the final CSV report.
    """
    if not os.path.exists(INPUT_JSON):
        print(f"FATAL ERROR: The input file '{INPUT_JSON}' was not found.")
        print("Please run the required `gcloud` command first to create this file.")
        sys.exit(1)

    print(f"--> Processing {INPUT_JSON} to create final comprehensive report...")
    
    final_rows = []
    try:
        with open(INPUT_JSON, 'r', encoding='utf-8') as f:
            all_policies = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FATAL ERROR: Could not parse '{INPUT_JSON}'. It may be empty or corrupted.")
        print(f"Details: {e}")
        sys.exit(1)

    for policy_doc in all_policies:
        resource = policy_doc.get('resource', '')
        # Get the Organization ID from the policy document
        organization_id = policy_doc.get('organization', 'organizations/UNKNOWN').split('/')[1]
        
        resource_type, resource_id, resource_name, parent_name = "", "", "", ""

        is_project = re.match(r'^//cloudresourcemanager.googleapis.com/projects/[^/]+$', resource)
        is_folder = re.match(r'^//cloudresourcemanager.googleapis.com/folders/[^/]+$', resource)

        if is_project:
            resource_type = "Project"
            resource_id = resource.split('/')[-1]
            if ':' in resource_id: continue # Skip special system-owned projects

            print(f"Processing Project: {resource_id}")
            # --- THIS BLOCK IS NOW CORRECTED ---
            try:
                # Get the project's name, its parent's type, and its parent's ID
                proc = subprocess.run(
                    ['gcloud', 'projects', 'describe', resource_id, '--format=value(name, parent.type, parent.id)'],
                    capture_output=True, text=True, check=True, encoding='utf-8'
                )
                name, parent_type, parent_id_str = proc.stdout.strip().split('\t')
                resource_name = name
                
                # Check if the parent is a folder or the organization
                if parent_type == 'folder':
                    parent_name = get_folder_name(f"folders/{parent_id_str}")
                else: # parent_type will be 'organization'
                    parent_name = "<Organization>"

            except (subprocess.CalledProcessError, ValueError):
                resource_name = "<project details not found>"
                parent_name = ""
        elif is_folder:
            resource_type = "Folder"
            resource_id = resource.split('/')[-1]
            print(f"Processing Folder: {resource_id}")
            resource_name = get_folder_name(f"folders/{resource_id}")
            # This advanced block looks up the folder's parent details.
            try:
                proc = subprocess.run(
                    ['gcloud', 'resource-manager', 'folders', 'describe', resource_id, '--format=value(parent)'],
                     capture_output=True, text=True, check=True, encoding='utf-8'
                )
                parent_path = proc.stdout.strip()
                # Check if the parent is another folder or the organization
                if 'folders/' in parent_path:
                    # If the parent is a folder, look up its name
                    parent_name = get_folder_name(parent_path)
                else:
                    # Otherwise, the parent is the organization
                    parent_name = "<Organization>"
            except (subprocess.CalledProcessError, ValueError):
                # If the lookup fails for any reason
                parent_name = "<Parent lookup failed>"
        else:
            # This skips permissions on all other resource types
            continue
        
        # Navigate the JSON structure to get roles and members
        bindings = policy_doc.get('policy', {}).get('bindings', [])
        for binding in bindings:
            role = binding.get('role', '')
            members = binding.get('members', [])
            for member in members:
                final_rows.append([
                    organization_id, resource_type, resource_id, resource_name, 
                    parent_name, role, member
                ])

    # Write all collected data to the final CSV file
    try:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['OrganizationID', 'ResourceType', 'ResourceID', 'ResourceName', 'Parent', 'Role', 'Member'])
            writer.writerows(final_rows)
        print("-" * 60)
        print(f"Success! The final, comprehensive report is ready: {OUTPUT_CSV}")
        print("-" * 60)
    except IOError as e:
        print(f"FATAL ERROR: Could not write the output file '{OUTPUT_CSV}'.")
        print(f"Details: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
