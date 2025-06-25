
import os
import subprocess
import ollama
import re
import time
from pathlib import Path

BASE_DIR = os.path.expanduser("~/java-projects")  # Update this to your actual repos directory
MODEL_NAME = "codellama"
MAX_FILES = 3
MAX_CHARS_PER_FILE = 500
RETRY_LIMIT = 2
README_LOG = os.path.join(BASE_DIR, "readme_codellama_log.txt")

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

def collect_code_samples(repo_path):
    code_samples = []
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith((".java", ".xml", ".json", ".ts", ".py", ".js", ".yml", ".yaml", ".properties")):
                try:
                    with open(os.path.join(root, file), "r") as f:
                        content = f.read(MAX_CHARS_PER_FILE)
                        code_samples.append(f"--- FILE: {file} ---\n{content}")
                        if len(code_samples) >= MAX_FILES:
                            return code_samples
                except:
                    continue
    return code_samples

def clean_app_name(name):
    return re.sub(r"[_\-]+", " ", name).strip().title()

def call_codellama(prompt):
    for attempt in range(RETRY_LIMIT):
        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that writes README.md sections from code context."},
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "stop": ["\n\n"],
                },
                stream=False
            )
            print("RAW RESPONSE:", response)
            output = response.get("message", {}).get("content", "").strip()
            if len(output) > 50:
                return output
        except Exception as e:
            print("Model error:", e)
        time.sleep(2)
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
    code_context = "\n\n".join(collect_code_samples(repo_path))

    prompt = f"""You will be given partial source code of a software project. Analyze it and respond to the following:

1. Write a 2-3 line **project description**.
2. Summarize the **architecture** used in the application.
3. List and briefly describe the **tech stack** used.
4. Write steps on how to **run this project locally**.

--- CODE START ---
{code_context}
--- CODE END ---
"""".strip()

    model_response = call_codellama(prompt)
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
