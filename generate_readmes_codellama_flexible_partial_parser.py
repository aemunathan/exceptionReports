
import os
import subprocess
import re
from pathlib import Path

BASE_DIR = os.path.expanduser("~/java-projects")  # Update to your local repo base directory
README_LOG = os.path.join(BASE_DIR, "readme_codellama_partial_log.txt")

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

def call_codellama(prompt, repo_path):
    log(f"Invoking ollama for repo: {repo_path}")
    log(f"Prompt sent to CodeLlama:\n{prompt}\n{'-'*40}")
    try:
        result = subprocess.run(
            ["ollama", "run", "codellama"],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300
        )
        stdout = result.stdout.decode("utf-8").strip()
        stderr = result.stderr.decode("utf-8").strip()
        log(f"STDOUT:\n{stdout}\n{'-'*40}")
        log(f"STDERR:\n{stderr}\n{'='*60}")
        return stdout
    except Exception as e:
        log(f"Error during subprocess call for repo {repo_path}: {str(e)}")
        return ""

def parse_sections_flexibly(text):
    sections = {"description": "", "architecture": "", "tech_stack": "", "running": ""}
    # Normalize headers like: Architecture:, TECH STACK:, etc.
    headings = {
        "description": re.compile(r"(?i)^.*description.*:", re.MULTILINE),
        "architecture": re.compile(r"(?i)^.*architecture.*:", re.MULTILINE),
        "tech_stack": re.compile(r"(?i)^.*tech.*(stack|nologies).*:", re.MULTILINE),
        "running": re.compile(r"(?i)^.*run.*locally.*:", re.MULTILINE),
    }

    matches = []
    for key, pattern in headings.items():
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end(), key))

    matches.sort()  # sort by start index
    for i, (start, end, key) in enumerate(matches):
        section_start = end
        section_end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        content = text[section_start:section_end].strip()
        if content:
            sections[key] = content

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

Please analyze this repository and generate the following sections with headers ending with colons:

Brief Project Description:
Architecture:
Key Technologies Used:
How to Run Locally:

Each section should be clear and professional.
"""".strip()

    model_response = call_codellama(prompt, repo_path)
    results = parse_sections_flexibly(model_response)

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
