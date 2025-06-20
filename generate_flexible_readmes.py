
import os
import json
import subprocess
import xml.etree.ElementTree as ET
import re

BASE_DIR = os.path.expanduser("~/java-projects")  # Change this to your actual path
LOG_FILE = os.path.join(BASE_DIR, "readme_generation_log.txt")

def detect_project_type(path):
    if os.path.exists(os.path.join(path, "pom.xml")):
        return "Java-Maven"
    if os.path.exists(os.path.join(path, "angular.json")):
        return "Angular"
    if os.path.exists(os.path.join(path, "package.json")):
        return "Node"
    if os.path.exists(os.path.join(path, "index.html")):
        return "UI"
    for file in os.listdir(path):
        if file.endswith((".yaml", ".yml", ".json", ".env")):
            return "Config"
    return "Unknown"

def parse_java_pom(path):
    java_version, version, artifact_id = None, None, None
    props = {}
    try:
        tree = ET.parse(os.path.join(path, "pom.xml"))
        root = tree.getroot()
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        artifact_id = root.find("m:artifactId", ns)
        version = root.find("m:version", ns)
        props_node = root.find("m:properties", ns)
        if props_node is not None:
            for child in props_node:
                props[child.tag.split("}")[1]] = child.text
        java_version = props.get("java.version") or props.get("maven.compiler.source")
        return (artifact_id.text if artifact_id is not None else None,
                version.text if version is not None else None,
                java_version)
    except:
        return artifact_id, version, java_version

def parse_node_package(path):
    try:
        with open(os.path.join(path, "package.json")) as f:
            data = json.load(f)
        return data.get("name"), data.get("version"), data.get("scripts", {})
    except:
        return None, None, {}

def write_readme(path, name, proj_type, meta, structure):
    lines = [f"# {name}\n", f"## Project Type\n{proj_type}\n"]

    if proj_type == "Java-Maven":
        lines.append("This is a Java project using Maven.\n")
        if meta.get("version"):
            lines.append(f"**Project Version:** {meta['version']}\n")
        if meta.get("java_version"):
            lines.append(f"**Java Version:** {meta['java_version']}\n")
        lines.append("### Build\n```bash\nmvn clean install\n```")
        lines.append("### Run\n```bash\njava -cp target/classes/ path.to.Main  # Adjust main class path\n```")

    elif proj_type == "Node":
        lines.append("This is a Node.js project.\n")
        if meta.get("version"):
            lines.append(f"**Version:** {meta['version']}\n")
        lines.append("### Install\n```bash\nnpm install\n```")
        if "start" in meta.get("scripts", {}):
            lines.append("### Start\n```bash\nnpm start\n```")

    elif proj_type == "Angular":
        lines.append("This is an Angular project.\n")
        lines.append("### Run\n```bash\nnpm install\nng serve\n```")

    elif proj_type == "UI":
        lines.append("Static HTML/CSS/JS project.\n")
        lines.append("### View\nOpen `index.html` in browser.")

    elif proj_type == "Config":
        lines.append("Configuration repository containing YAML/JSON files.\n")

    else:
        lines.append("General purpose repository.\n")

    lines.append("\n## Project Structure\n```\n" + structure + "\n```")

    with open(os.path.join(path, "README.md"), "w") as f:
        f.write("\n".join(lines))

def main():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    log = open(LOG_FILE, "w")

    for entry in os.scandir(BASE_DIR):
        if not entry.is_dir():
            continue

        project_path = entry.path
        readme_path = os.path.join(project_path, "README.md")
        if os.path.exists(readme_path):
            log.write(f"Skipping {entry.name}: README exists.\n")
            continue

        proj_type = detect_project_type(project_path)
        name = entry.name
        meta = {}

        if proj_type == "Java-Maven":
            artifact_id, version, java_version = parse_java_pom(project_path)
            if artifact_id:
                name = artifact_id
            meta = {"version": version, "java_version": java_version}

        elif proj_type == "Node":
            name, version, scripts = parse_node_package(project_path)
            meta = {"version": version, "scripts": scripts}

        structure = subprocess.getoutput(f"tree -L 2 {project_path} 2>/dev/null")
        write_readme(project_path, name or entry.name, proj_type, meta, structure)
        log.write(f"Generated README for {name or entry.name} ({proj_type})\n")

    log.close()

if __name__ == "__main__":
    main()
