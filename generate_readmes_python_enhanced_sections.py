
import os
import re
from pathlib import Path

BASE_DIR = os.path.expanduser("~/java-projects")  # Change this to your actual base directory

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
{TECH_STACK}

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
        return

    files = os.listdir(repo_path)
    project_type = guess_project_type(files)
    app_name = os.path.basename(repo_path)
    git_url = "<replace with actual repo clone url>"

    tech_stack = tech_stack_for(project_type)
    install_cmd, start_cmd = commands_for(project_type)

    content = README_TEMPLATE.format(
        APP_NAME=re.sub(r'[_\-]+', ' ', app_name).strip().title(),
        DESCRIPTION=description_for(project_type),
        ARCHITECTURE=architecture_for(project_type),
        TECH_STACK=tech_stack,
        GIT_CLONE=git_url,
        DIR_NAME=app_name,
        INSTALL_CMD=install_cmd,
        START_CMD=start_cmd
    )

    with open(readme_path, "w") as f:
        f.write(content.strip() + "\n")

def main():
    for entry in os.scandir(BASE_DIR):
        if entry.is_dir():
            generate_readme(entry.path)

if __name__ == "__main__":
    main()
