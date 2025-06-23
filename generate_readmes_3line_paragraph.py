
import os
import subprocess
import re
import time
import psutil

CUSTOM_OLLAMA_MODEL_PATH = "/your/custom/path"
BASE_DIR = os.path.expanduser("~/java-projects")  # Replace as needed
OLLAMA_MODEL = "codellama"
README_LOG = os.path.join(BASE_DIR, "readme_ollama_log.txt")
os.environ["OLLAMA_MODELS"] = CUSTOM_OLLAMA_MODEL_PATH

TEMPLATE_TEXT = """# Application Name
{{APP_NAME}}

## Table of Contents
{{TOC}}

{{SECTION_DESCRIPTION}}

{{SECTION_ARCHITECTURE}}

{{SECTION_TECH_STACK}}

{{SECTION_DEPENDENCIES}}

{{SECTION_RUNNING_LOCALLY}}

## Contribution Guidelines
<Static content - You will update this manually later.>
"""

SECTION_HEADERS = {
    "DESCRIPTION": "## Description",
    "ARCHITECTURE": "## Architecture\nFor more details on the architecture, please visit [this link](https://confluence.com/confluence/display/abc/abc+Inta).",
    "TECH_STACK": "## Tech Stack",
    "DEPENDENCIES": "## Dependencies",
    "RUNNING_LOCALLY": "## Running Locally",
}

def log(msg):
    with open(README_LOG, "a") as logf:
        logf.write(msg + "\n")
    print(msg)

def patch_variable_with_note(text):
    return re.sub(r"(\$\{[^}]+\})", r"\1 _(This is determined during the build process.)_", text)

def detect_tech_stack(repo_path):
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        return "Java with Spring Boot (Maven)"
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
        return "Dependencies are defined in the Maven pom.xml file."
    elif os.path.exists(os.path.join(repo_path, "package.json")):
        return "Dependencies are managed via npm in the package.json file."
    return ""

def get_git_clone_command(repo_path):
    try:
        url = subprocess.getoutput(f"git -C {repo_path} remote get-url origin").strip()
        if url:
            return f"1. Clone the repository to your local machine:\n   `git clone {url}`"
    except:
        pass
    return "1. Clone the repository to your local machine."

def generate_run_steps(repo_path):
    steps = [get_git_clone_command(repo_path)]
    steps.append("2. Navigate to the project directory:\n   `cd <project-folder>`")
    if os.path.exists(os.path.join(repo_path, "pom.xml")):
        steps.append("3. Build the project:\n   `mvn clean install`")
        steps.append("4. Start the service:\n   `mvn spring-boot:run`")
    elif os.path.exists(os.path.join(repo_path, "package.json")):
        steps.append("3. Install dependencies:\n   `npm install`")
        steps.append("4. Start the service:\n   `npm start`")
    return "\n\n".join(steps)

def get_code_summary(repo_path):
    candidates = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(('.java', '.ts', '.js', '.py', '.yml', '.yaml', '.properties')):
                candidates.append(os.path.join(root, file))
            if len(candidates) >= 5:
                break
        if len(candidates) >= 5:
            break
    if not candidates:
        return ""

    prompt = "Analyze the following code/config files and generate three lines of descriptive content in a professional tone. Then convert it into a single paragraph.\n\n"

    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read(1000)
                prompt += f"--- FILE: {os.path.basename(path)} ---\n{content}\n\n"
        except:
            continue

    try:
        result = subprocess.run(["ollama", "run", OLLAMA_MODEL],
                                input=prompt,
                                capture_output=True,
                                text=True,
                                timeout=60)
        return result.stdout.strip()
    except Exception as e:
        return f"Failed to generate description: {str(e)}"

def build_toc(sections):
    toc = []
    toc_map = {
        "SECTION_DESCRIPTION": "Description",
        "SECTION_ARCHITECTURE": "Architecture",
        "SECTION_TECH_STACK": "Tech Stack",
        "SECTION_DEPENDENCIES": "Dependencies",
        "SECTION_RUNNING_LOCALLY": "Running Locally"
    }
    for key, title in toc_map.items():
        if sections.get(key):
            toc.append(f"- [{title}](#{title.lower().replace(' ', '-')})")
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

    app_name = extract_app_name(repo_path)
    stack = detect_tech_stack(repo_path)
    summary = get_code_summary(repo_path)

    sections = {
        "APP_NAME": patch_variable_with_note(app_name),
        "SECTION_DESCRIPTION": f"{SECTION_HEADERS['DESCRIPTION']}\n{summary}",
        "SECTION_TECH_STACK": f"{SECTION_HEADERS['TECH_STACK']}\n{stack}" if stack else "",
        "SECTION_DEPENDENCIES": f"{SECTION_HEADERS['DEPENDENCIES']}\n{detect_dependencies(repo_path)}",
        "SECTION_RUNNING_LOCALLY": f"{SECTION_HEADERS['RUNNING_LOCALLY']}\n{generate_run_steps(repo_path)}",
        "SECTION_ARCHITECTURE": SECTION_HEADERS["ARCHITECTURE"]
    }

    sections["TOC"] = build_toc(sections)

    readme_content = TEMPLATE_TEXT
    for key, value in sections.items():
        readme_content = readme_content.replace(f"{{{{{key}}}}}", patch_variable_with_note(value) if value else "")

    with open(readme_file, "w") as f:
        f.write(readme_content.strip() + "\n")
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
