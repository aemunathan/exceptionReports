
import os
import json
import xml.etree.ElementTree as ET
import subprocess
import re

BASE_DIR = os.path.expanduser("~/java-projects")  # Update to your actual repo base path
README_LOG = os.path.join(BASE_DIR, "readme_generation_log.txt")

def log(message):
    with open(README_LOG, "a") as log_file:
        log_file.write(message + "\n")
    print(message)

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

def extract_java_version(path):
    mvn_file = os.path.join(path, "pom.xml")
    if not os.path.exists(mvn_file):
        return None
    try:
        text = open(mvn_file).read()
        match = re.search(r"<java\.version>(.*?)<\/java\.version>", text)
        if match:
            return match.group(1)
    except:
        pass
    return None

def parse_java_pom(path):
    pom_file = os.path.join(path, "pom.xml")
    if not os.path.exists(pom_file):
        return None
    try:
        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
        tree = ET.parse(pom_file)
        root = tree.getroot()
        artifact = root.findtext("m:artifactId", namespaces=ns)
        group = root.findtext("m:groupId", namespaces=ns)
        version = root.findtext("m:version", namespaces=ns)
        start_class = root.findtext("m:properties/m:start-class", namespaces=ns)
        java_version = root.findtext("m:properties/m:java.version", namespaces=ns)

        parent_group = root.findtext("m:parent/m:groupId", namespaces=ns)
        parent_artifact = root.findtext("m:parent/m:artifactId", namespaces=ns)
        parent_version = root.findtext("m:parent/m:version", namespaces=ns)

        deps = []
        for dep in root.findall(".//m:dependencies/m:dependency", ns):
            g = dep.findtext("m:groupId", namespaces=ns)
            a = dep.findtext("m:artifactId", namespaces=ns)
            if g and a:
                deps.append(f"{g}:{a}")

        docker_profiles = []
        for profile in root.findall(".//m:profile", ns):
            profile_id = profile.findtext("m:id", namespaces=ns)
            if profile_id and "docker" in profile_id.lower():
                docker_profiles.append(profile_id)

        return {
            "type": "Java-Maven",
            "name": artifact,
            "version": version,
            "group": group,
            "start_class": start_class,
            "java_version": java_version or extract_java_version(path),
            "dependencies": deps,
            "docker_profiles": docker_profiles,
            "parent_group": parent_group,
            "parent_artifact": parent_artifact,
            "parent_version": parent_version
        }
    except:
        return None

def parse_node_package(path):
    try:
        with open(os.path.join(path, "package.json")) as f:
            pkg = json.load(f)
        return {
            "type": "Node",
            "name": pkg.get("name"),
            "version": pkg.get("version"),
            "scripts": pkg.get("scripts", {})
        }
    except:
        return None

def get_git_info(path):
    if not os.path.exists(os.path.join(path, ".git")):
        return {}
    try:
        url = subprocess.getoutput(f"git -C {path} remote get-url origin")
        last_commit = subprocess.getoutput(f"git -C {path} log -1 --pretty=format:'%h - %s (%ci)'")
        branch = subprocess.getoutput(f"git -C {path} symbolic-ref refs/remotes/origin/HEAD").split('/')[-1].strip()
        return {
            "remote": url,
            "commit": last_commit,
            "branch": branch
        }
    except:
        return {}

def write_readme(path, meta, gitinfo):
    name = meta.get("name") or os.path.basename(path)
    readme_path = os.path.join(path, "README.md")
    lines = [f"# {name}", ""]

    lines.append("## Description")
    lines.append("More information available at the confluence link https://confluence.com/abcd\n")

    if meta["type"] == "Java-Maven":
        if meta.get("parent_group"):
            lines.append("## CCP Version")
            lines.append(f"**groupId:** {meta['parent_group']}")
            lines.append(f"**artifactId:** {meta['parent_artifact']}")
            lines.append(f"**version:** {meta['parent_version']}\n")

        if meta.get("version"):
            lines.append("## Version")
            lines.append(f"{meta['version']}\n")

        if meta.get("java_version"):
            lines.append("## Java Version")
            lines.append(f"{meta['java_version']}\n")

        if meta.get("dependencies"):
            lines.append("## Dependencies")
            for dep in meta["dependencies"]:
                lines.append(f"- {dep}")
            lines.append("")

        lines.append("## Building the Project")
        lines.append("```bash\nmvn clean install\n```\n")

        if meta.get("start_class"):
            lines.append("## Running the Service")
            lines.append(f"The main class for the application is `{meta['start_class']}`.")
            lines.append("```bash\nmvn spring-boot:run\n```\n")

        if meta["docker_profiles"]:
            lines.append("## Deployment")
            lines.append("This project can be deployed using the following profiles:")
            for p in meta["docker_profiles"]:
                lines.append(f"- {p}")
            lines.append("")
            lines.append("### Docker Deployment")
            lines.append("```bash\nmvn install -P DockerBuild -Ddocker.image.name=<image_name> \
  -Ddocker.image.tag=<image_tag> -Drepository.server.id=<repository_id>\n```\n")

    elif meta["type"] == "Node":
        if meta.get("version"):
            lines.append("## Version")
            lines.append(f"{meta['version']}\n")

        lines.append("## Installing Dependencies")
        lines.append("```bash\nnpm install\n```\n")

        if "start" in meta.get("scripts", {}):
            lines.append("## Running the App")
            lines.append("```bash\nnpm start\n```\n")

    elif meta["type"] == "Angular":
        lines.append("## Running the Angular App")
        lines.append("```bash\nnpm install\nng serve\n```\n")

    elif meta["type"] == "UI":
        lines.append("## Viewing")
        lines.append("Open `index.html` in a browser.\n")

    elif meta["type"] == "Config":
        lines.append("## Configuration")
        lines.append("This repository contains configuration files such as YAML, JSON, or ENV.\n")

    if meta["type"] in ["Java-Maven", "Node"]:
        lines.append("## API Documentation")
        lines.append("This service provides Swagger documentation at:")
        lines.append("https://apis.abcd.com:8000/swagger-ui/index.html\n")

    if gitinfo:
        lines.append("## Git Information")
        if gitinfo.get("remote"):
            lines.append(f"- Remote: {gitinfo['remote']}")
        if gitinfo.get("branch"):
            lines.append(f"- Default Branch: {gitinfo['branch']}")
        if gitinfo.get("commit"):
            lines.append(f"- Last Commit: {gitinfo['commit']}")
        lines.append("")

    with open(readme_path, "w") as f:
        f.write("\n".join(lines))

def main():
    if os.path.exists(README_LOG):
        os.remove(README_LOG)

    for item in os.scandir(BASE_DIR):
        if not item.is_dir():
            continue
        proj_path = item.path
        readme_file = os.path.join(proj_path, "README.md")
        if os.path.exists(readme_file):
            log(f"Skipped (README exists): {proj_path}")
            continue

        proj_type = detect_project_type(proj_path)
        meta = None

        if proj_type == "Java-Maven":
            meta = parse_java_pom(proj_path)
        elif proj_type == "Node":
            meta = parse_node_package(proj_path)
        elif proj_type in ["Angular", "UI", "Config"]:
            meta = {"type": proj_type, "name": item.name}

        if not meta:
            log(f"Skipped (unrecognized or incomplete): {proj_path}")
            continue

        gitinfo = get_git_info(proj_path)
        write_readme(proj_path, meta, gitinfo)
        log(f"Generated README.md for: {proj_path}")

if __name__ == "__main__":
    main()
