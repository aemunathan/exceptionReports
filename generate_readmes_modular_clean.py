
import os
import subprocess
import re
import time
import psutil

# Configuration
CUSTOM_OLLAMA_MODEL_PATH = "/your/custom/path"
BASE_DIR = os.path.expanduser("~/java-projects")  # Replace with your actual project base path
OLLAMA_MODEL = "codellama"
README_LOG = os.path.join(BASE_DIR, "readme_ollama_log.txt")

os.environ["OLLAMA_MODELS"] = CUSTOM_OLLAMA_MODEL_PATH

TEMPLATE_TEXT = """# Application Name
{{APP_NAME}}

## Table of Contents
{{TOC}}

## Description
{{DESCRIPTION}}

## Architecture
For more details on the architecture, please visit [this link](https://confluence.com/confluence/display/abc/abc+Inta).

## Tech Stack
{{TECH_STACK}}

## Dependencies
{{DEPENDENCIES}}

## Running Locally
{{RUN_STEPS}}

## Contribution Guidelines
<Static content - You will update this manually later.>
"""

SECTION_MAP = {
    "APP_NAME": "Application name from directory or artifactId",
    "DESCRIPTION": "Summary from repo structure or README",
    "TECH_STACK": "Detected technologies",
    "DEPENDENCIES": "Maven/Node package list",
    "RUN_STEPS": "Run steps like npm install or mvn spring-boot:run",
}

def log(msg):
    with open(README_LOG, "a") as logf:
        logf.write(msg + "\n")
    print(msg)

def patch_variable_with_note(text):
    return re.sub(r"(\$\{[^}]+\})", r"\1 _(This is determined during the build process.)_", text)

def detect_tech_stack(repo_path):
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        return "Java with Maven"
    elif os.path.exists(os.path.join(repo_path, "package.json")):
        if os.path.exists(os.path.join(repo_path, "angular.json")):
            return "Angular (Node.js)"
        return "Node.js"
    elif "config" in repo_path.lower():
        return "Configuration repository"
    return ""

def extract_app_name(repo_path):
    pom_file = os.path.join(repo_path, "pom.xml")
    if os.path.exists(pom_file):
        with open(pom_file) as f:
            content = f.read()
            match = re.search(r"<artifactId>(.*?)</artifactId>", content)
            if match:
                return match.group(1)
    return os.path.basename(repo_path)

def detect_dependencies(repo_path):
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        return "Dependencies managed by Maven (see pom.xml)"
    elif os.path.exists(os.path.join(repo_path, "package.json")):
        return "Dependencies managed by npm (see package.json)"
    return ""

def generate_run_steps(repo_path):
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        return ("To run the service locally, follow these steps:\n"
                "1. Clone the repository to your local machine.\n"
                "2. Navigate to the project directory.\n"
                "3. Run `mvn clean install`.\n"
                "4. Start the service using `mvn spring-boot:run`.")
    elif os.path.exists(os.path.join(repo_path, "package.json")):
        return ("To run the service locally, follow these steps:\n"
                "1. Clone the repository.\n"
                "2. Navigate to the directory.\n"
                "3. Run `npm install`.\n"
                "4. Start using `npm start`.")
    return ""

def generate_description(stack):
    if "config" in stack.lower():
        return "This repository contains configuration files for various services."
    return f"This project is implemented using {stack}."

def build_toc(sections):
    toc = []
    for key in ["DESCRIPTION", "TECH_STACK", "DEPENDENCIES", "RUN_STEPS"]:
        if sections.get(key):
            title = key.replace("_", " ").title()
            link = title.lower().replace(" ", "-")
            toc.append(f"- [{title}](#{link})")
    toc.append("- [Contribution Guidelines](#contribution-guidelines)")
    return "\n".join(toc)

def is_ollama_running():
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if 'ollama' in proc.info['name'] and 'serve' in ' '.join(proc.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def start_ollama_serve():
    log("Starting ollama serve in background...")
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

def generate_readme(repo_path):
    readme_file = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_file):
        log(f"Skipped (README exists): {repo_path}")
        return

    sections = {}

    stack = detect_tech_stack(repo_path)
    sections["APP_NAME"] = extract_app_name(repo_path)
    sections["TECH_STACK"] = stack
    sections["DESCRIPTION"] = generate_description(stack)
    sections["DEPENDENCIES"] = detect_dependencies(repo_path)
    sections["RUN_STEPS"] = generate_run_steps(repo_path)

    # Build dynamic ToC
    sections["TOC"] = build_toc(sections)

    readme_content = TEMPLATE_TEXT
    for key, value in sections.items():
        if value:
            readme_content = readme_content.replace(f"{{{{{key}}}}}", patch_variable_with_note(value))
        else:
            # Remove section header if value is missing
            section_pattern = rf"## {key.replace('_', ' ')}\n.*?(?=(\n##|\Z))"
            readme_content = re.sub(section_pattern, "", readme_content, flags=re.DOTALL)
            readme_content = readme_content.replace(f"{{{{{key}}}}}", "")

    with open(readme_file, "w") as f:
        f.write(readme_content + "\n")
    log(f"Generated README.md for: {repo_path}")

def main():
    if not is_ollama_running():
        start_ollama_serve()

    if os.path.exists(README_LOG):
        os.remove(README_LOG)

    for entry in os.scandir(BASE_DIR):
        if entry.is_dir():
            generate_readme(entry.path)

if __name__ == "__main__":
    main()
