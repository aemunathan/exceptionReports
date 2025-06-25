
import os
import subprocess
import re
from pathlib import Path

BASE_DIR = os.path.expanduser("~/java-projects")  # Update to your repo base dir
RETRY_LIMIT = 2
README_LOG = os.path.join(BASE_DIR, "readme_codellama_subprocess_debug_log.txt")

TEMPLATE = """# {APP_NAME}

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
{RUNNING}

## Contribution Guidelines
This project follows standard contribution practices. Feel free to fork the repository and submit pull requests.
"""

FALLBACK_TEXT = {
    "description": "This project is developed using Java and Maven. (This is determined during the build process.)",
    "architecture": "Standard layered architecture with controllers, services, and repositories. (This is determined during the build process.)",
    "tech_stack": "Java, Maven (This is determined during the build process.)",
    "running": "Clone the repository and run `mvn spring-boot:run`. (This is determined during the build process.)"
}

def log(msg):
    with open(README_LOG, "a") as f:
        f.write(msg + "\n")
    print(msg)

def clean_app_name(name):
    return re.sub(r"[_\-]+", " ", name).strip().title()

def call_codellama_via_subprocess(prompt, repo_path):
    log(f"Invoking ollama for repo: {repo_path}")
    log(f"Prompt sent to CodeLlama:\n{prompt}\n{'-'*40}")
    try:
        result = subprocess.run(
            ["ollama", "run", "codellama"],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180
        )
        stdout = result.stdout.decode("utf-8").strip()
        stderr = result.stderr.decode("utf-8").strip()
        log(f"STDOUT:\n{stdout}\n{'-'*40}")
        log(f"STDERR:\n{stderr}\n{'='*60}")
        return stdout
    except Exception as e:
        log(f"Error during subprocess call for repo {repo_path}: {str(e)}")
        return ""

def parse_response(response):
    sections = {"description": "", "architecture": "", "tech_stack": "", "running": ""}
    patterns = {
        "description": r"(?:^|\n)1\.\s*(.*?)\n2\.",
        "architecture": r"\n2\.\s*(.*?)\n3\.",
        "tech_stack": r"\n3\.\s*(.*?)\n4\.",
        "running": r"\n4\.\s*(.*)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, response, re.DOTALL)
        if match:
            sections[key] = match.group(1).strip()
    return sections

def generate_readme(repo_path):
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_path):
        log(f"Skipped (README exists): {repo_path}")
        return

    app_name = os.path.basename(repo_path)
    app_title = clean_app_name(app_name)

    prompt = f"""This is a software repository located at the following path on a local Linux machine:

{repo_path}

Please analyze this repository and generate the following:

1. A brief project description (2-3 lines)
2. A short explanation of the architecture used
3. The key technologies used (tech stack)
4. How to run this project locally

Return each as a numbered section.
"""".strip()

    model_response = call_codellama_via_subprocess(prompt, repo_path)
    results = parse_response(model_response)

    description = results["description"] or FALLBACK_TEXT["description"]
    architecture = results["architecture"] or FALLBACK_TEXT["architecture"]
    tech_stack = results["tech_stack"] or FALLBACK_TEXT["tech_stack"]
    running = results["running"] or FALLBACK_TEXT["running"]

    readme_content = TEMPLATE.format(
        APP_NAME=app_title,
        DESCRIPTION=description,
        ARCHITECTURE=architecture,
        TECH_STACK=tech_stack,
        RUNNING=running
    )

    with open(readme_path, "w") as f:
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
