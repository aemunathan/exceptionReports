
import os
import subprocess
import re

# Set your custom model path here
CUSTOM_OLLAMA_MODEL_PATH = "/your/custom/path"
os.environ["OLLAMA_MODELS"] = CUSTOM_OLLAMA_MODEL_PATH

BASE_DIR = os.path.expanduser("~/java-projects")  # Change to your repo base
OLLAMA_MODEL = "codellama"
README_LOG = os.path.join(BASE_DIR, "readme_ollama_log.txt")

def log(msg):
    with open(README_LOG, "a") as logf:
        logf.write(msg + "\n")
    print(msg)

def patch_variable_with_note(text):
    if re.search(r"\$\{[^}]+\}", text):
        return f"{text} _(This is determined during the build process.)_"
    return text

def build_prompt(repo_path):
    prompt_parts = []

    # Add basic project structure info
    prompt_parts.append(f"Generate a concise, professional README.md file for the project at: {repo_path}.")
    prompt_parts.append("Include only the sections that are relevant based on the project contents.")
    prompt_parts.append("If any version, artifactId, groupId or other info contains ${...}, mention that it is determined during the build process.")
    prompt_parts.append("Include build/run steps and Swagger URL if applicable.")
    prompt_parts.append("Include Git remote and default branch from metadata if available.")
    prompt = "\n".join(prompt_parts)
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

def run_ollama(prompt):
    try:
        result = subprocess.run(
            ['ollama', 'run', OLLAMA_MODEL, '-p', prompt],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error running Ollama: {e}"

def generate_readme(repo_path):
    readme_file = os.path.join(repo_path, "README.md")
    if os.path.exists(readme_file):
        log(f"Skipped (README exists): {repo_path}")
        return

    prompt = build_prompt(repo_path)
    git_info = get_git_metadata(repo_path)
    full_prompt = prompt + "\n" + git_info

    readme_text = run_ollama(full_prompt)
    if readme_text:
        readme_text = patch_variable_with_note(readme_text)
        with open(readme_file, "w") as f:
            f.write(readme_text + "\n")
        log(f"Generated README.md for: {repo_path}")
    else:
        log(f"Failed to generate README.md for: {repo_path}")

def main():
    if os.path.exists(README_LOG):
        os.remove(README_LOG)

    for entry in os.scandir(BASE_DIR):
        if entry.is_dir():
            generate_readme(entry.path)

if __name__ == "__main__":
    main()
