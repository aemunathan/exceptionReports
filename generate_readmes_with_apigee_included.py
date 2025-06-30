def is_apigee_project(path):
    possible_paths = [
        os.path.join(path, "apiproxy"),
        os.path.join(path, "apigee", "apigee-proxy"),
        os.path.join(path, "edge", "apiproxy"),
    ]
    expected_subfolders = {"policies", "proxies", "targets"}

    for base_path in possible_paths:
        if os.path.isdir(base_path):
            subdirs = set(os.listdir(base_path))
            if not expected_subfolders.isdisjoint(subdirs):
                return True
    return False

def apigee_tech_stack():
    return [
        "Apigee Edge or Apigee X",
        "XML-based policy configuration",
        "OAuth2/JWT security",
        "ProxyEndpoint/TargetEndpoint setup",
        "Deployment via Apigee CLI or Maven"
    ]

def apigee_description():
    return "This project is an Apigee API proxy used to expose backend services via RESTful APIs. It follows Apigee’s standard proxy structure using XML-based policies and proxy endpoints."

def apigee_architecture():
    return "The architecture follows Apigee's proxy model including ProxyEndpoint, TargetEndpoint, and policy configurations for mediation, security, and traffic management."

def apigee_commands():
    return (
        "apigeecli apis import --org your-org --env test --file ./apiproxy",
        "apigeecli apis deploy --name your-proxy --env test --org your-org"
    )



import os
import re
import json
from pathlib import Path

BASE_DIR = os.path.expanduser("~/java-projects")  # Change this to your actual base directory
DL_EMAIL = "DL-MyTeam-AI@example.com"

README_TEMPLATE = """# {APP_NAME}

## Table of Contents
- [Description](#description)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Dependencies](#dependencies)
- [Running Locally](#running-locally)
- [Contribution Guidelines](#contribution-guidelines)

## Description
{DESCRIPTION}

## Architecture
{ARCHITECTURE}

## Tech Stack
{TECH_STACK}

## Dependencies
{DEPENDENCIES}

## Running Locally
To run the service locally, follow these steps:

1. Clone the repository to your local machine.
```
git clone {GIT_CLONE}
```

2. Navigate to the project directory.
```
cd {DIR_NAME}
```

3. Install the dependencies
```
{INSTALL_CMD}
```

4. Start the service
```
{START_CMD}
```

## Contribution Guidelines
This project follows standard contribution practices. Feel free to fork the repository and submit pull requests.  
Please contact us at [{DL_EMAIL}](mailto:{DL_EMAIL}) for contribution-related questions.
"""

def guess_project_type(files):
    if "pom.xml" in files:
        return "java-maven"
    elif "package.json" in files:
        return "nodejs"
    elif "angular.json" in files:
        return "angular"
    elif any(f.endswith(".py") for f in files):
        return "python"
    elif any("config" in f.lower() for f in files):
        return "config"
    return "unknown"

def tech_stack_for(project_type):
    stacks = {
        "java-maven": "- Java\n- Spring Boot\n- Maven",
        "nodejs": "- Node.js\n- Express.js\n- MongoDB",
        "angular": "- Angular\n- TypeScript\n- RxJS",
        "python": "- Python\n- Flask or Django\n- pip",
        "config": "- Configuration Files\n- YAML/JSON",
        "unknown": "- General Purpose"
    }
    return stacks.get(project_type, "- General Purpose")

def commands_for(project_type):
    if project_type == "java-maven":
        return "mvn install", "mvn spring-boot:run"
    elif project_type == "nodejs":
        return "npm install", "npm start"
    elif project_type == "angular":
        return "npm install", "ng serve"
    elif project_type == "python":
        return "pip install -r requirements.txt", "python app.py"
    else:
        return "<manual-steps>", "<start-command>"

def description_for(project_type):
    descriptions = {
        "java-maven": "This project is implemented using Java and Maven.",
        "nodejs": "This project is a Node.js-based service using Express.",
        "angular": "This project is a front-end web application built with Angular.",
        "python": "This project is developed in Python.",
        "config": "This repository contains environment or deployment configuration files.",
        "unknown": "Project details are inferred from the available files."
    }
    return descriptions.get(project_type)

def architecture_for(project_type):
    return "Standard layered architecture. (This is determined during the build process.)"

def extract_dependencies(repo_path, project_type):
    try:
        if project_type == "java-maven":
            pom = Path(repo_path) / "pom.xml"
            if pom.exists():
                return "\n".join(sorted(set(re.findall(r'<artifactId>(.*?)</artifactId>', pom.read_text()))))
        elif project_type in ["nodejs", "angular"]:
            pkg = Path(repo_path) / "package.json"
            if pkg.exists():
                data = json.loads(pkg.read_text())
                deps = data.get("dependencies", {})
                return "\n".join(f"- {k}: {v}" for k, v in deps.items())
        elif project_type == "python":
            req = Path(repo_path) / "requirements.txt"
            if req.exists():
                return "\n".join(f"- {line.strip()}" for line in req.read_text().splitlines() if line.strip())
        elif project_type == "config":
            return "- Various configuration files (YAML, JSON, etc.)"
    except Exception as e:
        return f"- Failed to extract dependencies: {e}"
    return "- No dependencies found."

def get_git_url(repo_path):
    try:
        output = subprocess.check_output(
            ["git", "-C", repo_path, "config", "--get", "remote.origin.url"],
            stderr=subprocess.DEVNULL
        )
        return output.decode().strip()
    except Exception:
        return "<git-url-unavailable>"

def generate_readme(repo_path):
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        print(f"README already exists in {repo_path}")
        return

    if is_apigee_project(repo_path):
        project_type = "apigee"
    else:
        files = os.listdir(repo_path)
        project_type = guess_project_type(files)

    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        return

    files = os.listdir(repo_path)
    project_type = guess_project_type(files)
    app_name = os.path.basename(repo_path)
    git_url = get_git_url(repo_path)

    tech_stack = tech_stack_for(project_type)
    install_cmd, start_cmd = commands_for(project_type)
    dependencies = extract_dependencies(repo_path, project_type)
    if project_type == "apigee":
        tech_stack = "\n".join(f"- {item}" for item in apigee_tech_stack())
        description = apigee_description()
        architecture = apigee_architecture()
        install_cmd, start_cmd = apigee_commands()
    else:
        tech_stack = tech_stack_for(project_type, dependencies)
        description = description_for(project_type)
        architecture = architecture_for(project_type)
        install_cmd, start_cmd = commands_for(project_type)


    content = README_TEMPLATE.format(
        APP_NAME=re.sub(r'[_\-]+', ' ', app_name).strip().title(),
        DESCRIPTION=description_for(project_type),
        ARCHITECTURE=architecture_for(project_type),
        TECH_STACK=tech_stack,
        DEPENDENCIES=dependencies,
        GIT_CLONE=git_url,
        DIR_NAME=app_name,
        INSTALL_CMD=install_cmd,
        START_CMD=start_cmd,
        DL_EMAIL=DL_EMAIL
    )

    with open(readme_path, "w") as f:
        f.write(content.strip() + "\n")

def main():
    for entry in os.scandir(BASE_DIR):
        if entry.is_dir():
            generate_readme(entry.path)

if __name__ == "__main__":
    main()
