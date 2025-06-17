# GCP IAM Policy Reporter

A tool to generate a comprehensive CSV report of all IAM policies assigned to Projects and Folders within a Google Cloud Organization.

The script processes data exported from the Google Cloud Asset Inventory, enriches it with human-readable names for projects and folders, and formats it into a clean, easy-to-filter spreadsheet.

## Features

-   Reports on IAM policies attached directly to **Projects** and **Folders**.
-   Enriches the report with human-readable Project Names and Parent Folder Names.
-   Includes the parent **Organization ID** for each permission.
-   Expands bindings with multiple members into individual rows for easy analysis.
-   Skips special, system-owned projects to reduce noise.
-   Produces a clean, reliable CSV output file.

## Prerequisites

Before you begin, ensure you have the following:

1.  **Google Cloud SDK (`gcloud`)**: The script relies on `gcloud` to look up resource names.
    -   [Installation Guide](https://cloud.google.com/sdk/docs/install)
    -   After installing, you must authenticate:
        ```bash
        gcloud auth login
        gcloud auth application-default login
        ```

2.  **Python 3**: The script is written in Python.
    -   You can check your version with `python3 --version`.

3.  **Required IAM Permissions**: The user or service account running the export and script needs the following IAM permissions in the target organization:
    -   `cloudasset.assets.searchAllIamPolicies`
    -   `resourcemanager.projects.get`
    -   `resourcemanager.folders.get`

## Usage Instructions

Follow these three steps to generate your report.

### Step 1: Export IAM Data from Google Cloud

First, you must export the IAM policies from your organization into a JSON file. This command can take several minutes to run on large organizations.

Run the following command in your terminal, replacing `YOUR_ORG_ID` with your actual organization ID:

```bash
gcloud asset search-all-iam-policies --scope='organizations/YOUR_ORG_ID' --format="json" > iam_policies.json
```

*This will create a file named `iam_policies.json` in your current directory.*

**Note:** If you need to report on multiple organizations, run this command for each one and save the output to a different file (e.g., `iam_policies_org2.json`).

### Step 2: Configure the Script

Open the `iam_policy_reporter.py` script in a text editor. At the top of the file, you will see a configuration section.

```python
# --- Configuration ---
# Update these values before running the script.

# The name of the JSON file exported from the `gcloud asset` command.
INPUT_JSON = 'iam_policies.json'
# The name of the final CSV report that will be generated.
OUTPUT_CSV = 'iam_report_final.csv'
# -------------------
```
-   Update `INPUT_JSON` to match the name of the file you created in Step 1.
-   You can optionally change `OUTPUT_CSV` to your desired report name.

### Step 3: Run the Script

Once configured, run the script from your terminal:

```bash
python3 iam_policy_reporter.py
```

The script will process the JSON file, look up resource names, and generate the final CSV report.

## Output File

The script will produce a CSV file (e.g., `iam_report_final.csv`) with the following columns:

| Column         | Description                                                                 |
| :------------- | :-------------------------------------------------------------------------- |
| OrganizationID | The ID of the organization the permission belongs to.                       |
| ResourceType   | The type of resource (`Project` or `Folder`).                               |
| ResourceID     | The unique ID of the Project or Folder.                                     |
| ResourceName   | The human-readable display name of the Project or Folder.                   |
| Parent         | The display name of the resource's parent folder.                           |
| Role           | The IAM role that was assigned (e.g., `roles/editor`).                      |
| Member         | The principal granted the permission (e.g., `user:`, `group:`, `serviceAccount:`). |
