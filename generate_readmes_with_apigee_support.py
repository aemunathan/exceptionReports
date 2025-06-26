
import os
import re
import sys
import json

README_TEMPLATE = """# {APP_NAME}

## Table of Contents
- [Description](#description)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Running Locally](#running-locally)
- [Contribution Guidelines](#contribution-guidelines)

## Description
{DESCRIPTION}

## Architecture
{ARCHITECTURE}

## Tech Stack
The project uses the following technologies:
{TECH_STACK}

## Running Locally
To run the service locally, follow these steps:

1. Clone the repository to your local machine:
```
git clone {GIT_CLONE}
```

2. Navigate to the project directory:
```
cd {DIR_NAME}
```

3. Install the dependencies:
```
{INSTALL_CMD}
```

4. Start the service:
```
{START_CMD}
```

## Contribution Guidelines
This project follows standard contribution practices. Feel free to fork the repository and submit pull requests.
"""

def is_apigee_project(path):
    return os.path.isdir(os.path.join(path, "apiproxy"))

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

def extract_dependencies(repo_path, project_type):
    deps = []
    if project_type == "java-maven":
        pom_file = os.path.join(repo_path, "pom.xml")
        if os.path.exists(pom_file):
            with open(pom_file) as f:
                for line in f:
                    if "<artifactId>" in line or "<groupId>" in line:
                        deps.append(line.strip().replace("<", "").replace(">", ""))
    elif project_type in ("nodejs", "angular"):
        pkg_file = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg_file):
            try:
                with open(pkg_file) as f:
                    data = json.load(f)
                    deps = [f"{k}@{v}" for k, v in data.get("dependencies", {}).items()]
            except Exception:
                pass
    elif project_type == "python":
        req_file = os.path.join(repo_path, "requirements.txt")
        if os.path.exists(req_file):
            with open(req_file) as f:
                deps = [line.strip() for line in f if line.strip()]
    return deps

def tech_stack_for(project_type, dependencies):
    base = {
        "java-maven": ["Java", "Spring Boot", "Maven"],
        "nodejs": ["Node.js", "Express.js"],
        "angular": ["Angular", "TypeScript"],
        "python": ["Python", "Flask or Django"],
        "config": ["Configuration Files (YAML/JSON)"],
        "unknown": ["General Purpose"]
    }.get(project_type, ["General Purpose"])
    if dependencies:
        base.extend(dependencies[:5])  # Limit to first few to avoid bloat
    return "\n".join(f"- {item}" for item in base)

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
    if project_type == "java-maven":
        return "This project is implemented using Java and Maven."
    elif project_type == "nodejs":
        return "This project is a Node.js-based service using Express."
    elif project_type == "angular":
        return "This project is a front-end web application built with Angular."
    elif project_type == "python":
        return "This project is developed in Python."
    elif project_type == "config":
        return "This repository contains environment or deployment configuration files."
    else:
        return "Project details are inferred from the available files."

def architecture_for(project_type):
    return "Standard layered architecture. (This is determined during the build process.)"

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

    app_name = os.path.basename(repo_path)
    git_url = "<replace with actual repo clone url>"

    content = README_TEMPLATE.format(
        APP_NAME=re.sub(r'[_\-]+', ' ', app_name).strip().title(),
        DESCRIPTION=description,
        ARCHITECTURE=architecture,
        TECH_STACK=tech_stack,
        GIT_CLONE=git_url,
        DIR_NAME=app_name,
        INSTALL_CMD=install_cmd,
        START_CMD=start_cmd
    )

    with open(readme_path, "w") as f:
        f.write(content.strip() + "\n")
    print(f"README.md generated in {repo_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_readmes_with_apigee_support.py <repo_path>")
        sys.exit(1)
    generate_readme(sys.argv[1])
