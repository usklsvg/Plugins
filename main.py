import os
import shutil
import requests
import zipfile


def save_content(content, filename):
    try:
        with open(filename, mode="w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        print(f"Error when saving content to {filename}: {e}")


def extract(content: str):
    lines = []
    for line in content:
        lines.append(line.strip())

    data = {}
    line_index = 0
    data["title"] = ""
    while line_index < len(lines):
        if len(lines[line_index]) == 0:
            data["title"] += f"\n"
            line_index += 1
        elif lines[line_index][0] != "[":
            data["title"] += f"{lines[line_index]}\n"
            line_index += 1
        else:
            break

    while line_index < len(lines):
        item_name = lines[line_index]
        line_index += 1
        data[item_name] = ""
        while line_index < len(lines):
            if len(lines[line_index]) == 0:
                data[item_name] += f"\n"
                line_index += 1
            elif lines[line_index][0] != "[":
                data[item_name] += f"{lines[line_index]}\n"
                line_index += 1
            else:
                break
    return data


def process_file(file_path: str):
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            content = f.readlines()
    except IOError as e:
        print(f"Error when reading content from {file_path}: {e}")
        return

    filename = file_path.split("/")[-1]
    filename = filename.split("\\")[-1]
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data = extract(content)

    has_content = False
    content_without_script = data["title"]
    for key in data:
        if key == "title" or str(key).lower() == "[script]":
            continue
        if str(key).lower() != "[mitm]":
            has_content = True
        content_without_script += f"{key}\n{data[key]}"
    if has_content:
        output_filename_without_scripts = os.path.join(current_dir, "plugins", filename)
        save_content(content_without_script, output_filename_without_scripts)

    has_script = False
    content_scripts = data["title"]
    for key in data:
        if str(key).lower() == "[script]":
            has_script = True
            content_scripts += f"{key}\n{data[key]}"
        elif str(key).lower() == "[argument]" or str(key).lower() == "[mitm]":
            content_scripts += f"{key}\n{data[key]}"
    if has_script:
        output_filename_scripts = os.path.join(current_dir, "plugins_scripts", filename)
        save_content(content_scripts, output_filename_scripts)


def download_repo():
    repo_url = (
        "https://gitlab.com/lodepuly/vpn_tool/-/archive/master/vpn_tool-master.zip"
    )
    try:
        response = requests.get(repo_url, stream=True)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"error : {e}")
        exit(1)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    zip_dir = os.path.join(current_dir, "vpn_tool-master.zip")
    try:
        with open(zip_dir, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        print(f"error when saving content to zip file : {e}")
        exit(1)

    target_path = os.path.join(current_dir, "extern")
    try:
        repo_dir = os.path.join(current_dir, "extern")
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        os.makedirs(repo_dir)

        with zipfile.ZipFile(zip_dir, "r") as zip_ref:
            zip_ref.extractall(target_path)

        os.remove(zip_dir)
        os.rename(
            os.path.join(target_path, "vpn_tool-master"),
            os.path.join(target_path, "vpn_tool"),
        )
    except Exception as e:
        print(f"error when extracting file: {e}")


if __name__ == "__main__":
    download_repo()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        output_dir_without_scripts = os.path.join(current_dir, "plugins")
        if os.path.exists(output_dir_without_scripts):
            shutil.rmtree(output_dir_without_scripts)
        os.makedirs(output_dir_without_scripts)

        output_dir_scripts = os.path.join(current_dir, "plugins_scripts")
        if os.path.exists(output_dir_scripts):
            shutil.rmtree(output_dir_scripts)
        os.makedirs(output_dir_scripts)
    except Exception as e:
        print(f"error when processing files")
        exit(1)

    plugins_path = os.path.join(
        current_dir, "extern", "vpn_tool", "Tool", "Loon", "Plugin"
    )
    for filename in os.listdir(plugins_path):
        if filename.lower().endswith(".plugin"):
            process_file(os.path.join(plugins_path, filename))
