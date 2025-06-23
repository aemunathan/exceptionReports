
import os
import subprocess
import re
import time
import psutil

# Configuration
CUSTOM_OLLAMA_MODEL_PATH = "/your/custom/path"
BASE_DIR = os.path.expanduser("~/java-projects")  # Replace with your actual path
OLLAMA_MODEL = "codellama"
README_LOG = os.path.join(BASE_DIR, "readme_ollama_log.txt")
TEMPLATE_README_PATH = os.path.expanduser("~/sample_readme_template.md")  # Replace with your sample file path

os.environ["OLLAMA_MODELS"] = CUSTOM_OLLAMA_MODEL_PATH

def log(msg):
    with open(README_LOG, "a") as logf:
        logf.write(msg + "\n")
    print(msg)

def patch_variable_with_note(text):
    return re.sub(r"(\$\{[^}]+\})", r"\1 _(This is determined during the build process.)_", text)

def build_prompt(repo_path, template_text):
    prompt = f"""
Use the following README format as a reference template. Analyze the project at: {repo_path} and generate a README.md file by replacing sections such as name, purpose, technologies, build instructions, and git info appropriately. If any version, artifactId, groupId or other info contains variables like ${{...}}, include a note that they are determined during build time.

### Reference Template
{template_text}

Only output the completed README content, no explanation.
"""
    return prompt

def get_git_metadata(repo_path):
    if not os.path.exists(os.path.join(repo_path, ".git")):
        return ""
    try:
        remote = subprocess.getoutput(f"git -C {repo_path} remote get-url origin")
        branch = subprocess.getoutput(f"git -C {repo_path} symbolic-ref refs/remotes/origin/HEAD").split('/')[-1].strip()
        return f"Git remote: {remote}\nDefault branch: {branch}\n"
    except:
        return ""

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

def run_ollama(prompt):
    try:
        result = subprocess.run(
            ['ollama', 'run', OLLAMA_MODEL],
            input=prompt,
            capture_output=True,
            text=True
        )
        if result.stderr:
            print("Ollama stderr:", result.stderr)
        return result.stdout.strip()
    except Exception as e:
        return f"Error running Ollama: {e}"

def generate_readme(repo_path, template_text):
    readme_file = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_file):
        log(f"Skipped (README exists): {repo_path}")
        return

    prompt = build_prompt(repo_path, template_text)
    readme_text = run_ollama(prompt)

    if readme_text:
        readme_text = patch_variable_with_note(readme_text)
        with open(readme_file, "w") as f:
            f.write(readme_text + "\n")
        log(f"Generated README.md for: {repo_path}")
    else:
        log(f"Failed to generate README.md for: {repo_path}")

def main():
    if not os.path.exists(TEMPLATE_README_PATH):
        print(f"Template README not found at {TEMPLATE_README_PATH}")
        return

    with open(TEMPLATE_README_PATH, "r") as tf:
        template_text = tf.read()

    if not is_ollama_running():
        start_ollama_serve()

    if os.path.exists(README_LOG):
        os.remove(README_LOG)

    for entry in os.scandir(BASE_DIR):
        if entry.is_dir():
            generate_readme(entry.path, template_text)

if __name__ == "__main__":
    main()
