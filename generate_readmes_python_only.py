
import os
import json
import subprocess
import re
from datetime import datetime

BASE_DIR = os.path.expanduser("~/java-projects")  # Change this to your base repo directory
README_LOG = os.path.join(BASE_DIR, "readme_python_log.txt")

TEMPLATE_TEXT = """# {{APP_NAME}}

## Table of Contents
{{TOC}}

{{SECTION_DESCRIPTION}}

{{SECTION_ARCHITECTURE}}

{{SECTION_TECH_STACK}}

{{SECTION_DEPENDENCIES}}

{{SECTION_RUNNING_LOCALLY}}

## Contribution Guidelines
This project follows standard contribution practices. Feel free to fork the repository and submit pull requests.
"""

SECTION_HEADERS = {
    "DESCRIPTION": "## Description",
    "ARCHITECTURE": "## Architecture",
    "TECH_STACK": "## Tech Stack",
    "DEPENDENCIES": "## Dependencies",
    "RUNNING_LOCALLY": "## Running Locally"
}

PROJECT_HINTS = {
    "java": {
        "description": "This is a Java project using Maven as the build tool.",
        "tech": "Java, Maven",
        "run": "Run `mvn clean install` followed by `java -jar target/*.jar`.",
        "arch": "Typically follows a layered architecture with controllers, services, and repositories."
    },
    "node": {
        "description": "This is a Node.js application managed with npm.",
        "tech": "Node.js, npm",
        "run": "Run `npm install` and then `npm start`.",
        "arch": "Common structure includes routes, controllers, and models."
    },
    "angular": {
        "description": "This is a frontend application built with Angular.",
        "tech": "Angular, TypeScript",
        "run": "Run `npm install` and then `ng serve`.",
        "arch": "Component-based architecture with services and modules."
    },
    "python": {
        "description": "This is a Python application.",
        "tech": "Python",
        "run": "Run `pip install -r requirements.txt` and execute main script.",
        "arch": "Follows modular script or package-based structure."
    },
    "config": {
        "description": "This repository contains configuration files and templates.",
        "tech": "YAML, JSON, Properties files",
        "run": "No execution steps. Used for configuration and setup.",
        "arch": "Organized by environment or application configuration modules."
    }
}

def log(msg):
    with open(README_LOG, "a") as logf:
        logf.write(msg + "\n")
    print(msg)

def detect_project_type(repo_path):
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        return "java"
    elif os.path.exists(os.path.join(repo_path, "package.json")):
        if os.path.exists(os.path.join(repo_path, "angular.json")):
            return "angular"
        return "node"
    elif os.path.exists(os.path.join(repo_path, "requirements.txt")) or any(f.endswith(".py") for f in os.listdir(repo_path)):
        return "python"
    elif "config" in repo_path.lower():
        return "config"
    return "unknown"

def extract_git_metadata(repo_path):
    git_info = {}
    try:
        default_branch = subprocess.check_output(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=repo_path, text=True).strip().split("/")[-1]
        git_info["branch"] = default_branch
    except:
        git_info["branch"] = "main"

    try:
        url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=repo_path, text=True).strip()
        git_info["url"] = url
    except:
        git_info["url"] = "<unknown>"

    try:
        last_commit = subprocess.check_output(["git", "log", "-1", "--format=%cd"], cwd=repo_path, text=True).strip()
        git_info["last_updated"] = last_commit
    except:
        git_info["last_updated"] = "<unknown>"

    return git_info

def extract_dependencies(repo_path, project_type):
    deps = []
    if project_type == "java":
        pom = os.path.join(repo_path, "pom.xml")
        if os.path.exists(pom):
            with open(pom) as f:
                for line in f:
                    if "<dependency>" in line:
                        deps.append("Java dependency declared")
                        break
    elif project_type in ["node", "angular"]:
        package_json = os.path.join(repo_path, "package.json")
        if os.path.exists(package_json):
            with open(package_json) as f:
                try:
                    data = json.load(f)
                    deps = list(data.get("dependencies", {}).keys())
                except:
                    pass
    elif project_type == "python":
        reqs = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(reqs):
            with open(reqs) as f:
                deps = [line.strip() for line in f if line.strip()]
    return deps

def build_toc(sections):
    toc = []
    for key, title in SECTION_HEADERS.items():
        if sections.get(f"SECTION_{key}"):
            toc.append(f"- [{title[3:]}](#{title[3:].lower().replace(' ', '-')})")
    toc.append("- [Contribution Guidelines](#contribution-guidelines)")
    return "\n".join(toc)

def generate_readme(repo_path):
    readme_file = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_file):
        log(f"Skipped (README exists): {repo_path}")
        return

    app_name = os.path.basename(repo_path)
    project_type = detect_project_type(repo_path)
    hints = PROJECT_HINTS.get(project_type, PROJECT_HINTS["config"])
    git_info = extract_git_metadata(repo_path)
    deps = extract_dependencies(repo_path, project_type)

    sections = {
        "APP_NAME": app_name,
        "SECTION_DESCRIPTION": f"{SECTION_HEADERS['DESCRIPTION']}\n{hints['description']}",
        "SECTION_ARCHITECTURE": f"{SECTION_HEADERS['ARCHITECTURE']}\n{hints['arch']}",
        "SECTION_TECH_STACK": f"{SECTION_HEADERS['TECH_STACK']}\n{hints['tech']}",
        "SECTION_DEPENDENCIES": f"{SECTION_HEADERS['DEPENDENCIES']}\n" + ("\n".join(f"- {d}" for d in deps) if deps else "No specific dependencies listed."),
        "SECTION_RUNNING_LOCALLY": f"{SECTION_HEADERS['RUNNING_LOCALLY']}\n{hints['run']}",
        "TOC": ""
    }

    sections["TOC"] = build_toc(sections)

    readme_content = TEMPLATE_TEXT
    for key, value in sections.items():
        readme_content = readme_content.replace(f"{{{{{key}}}}}", value)

    with open(readme_file, "w") as f:
        f.write(readme_content.strip() + "\n")
    log(f"Generated README.md for: {repo_path}")

def main():
    if os.path.exists(README_LOG):
        os.remove(README_LOG)
    for entry in os.scandir(BASE_DIR):
        if entry.is_dir():
            generate_readme(entry.path)

if __name__ == "__main__":
    main()
