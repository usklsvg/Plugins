import os
import shutil
import requests
import zipfile
import time
import random


current_dir = os.path.dirname(os.path.abspath(__file__))
extern_dir = os.path.join(current_dir, "extern", "ProxyResource")
extern_plugin_dir = os.path.join(extern_dir, "plugin")
extern_script_dir = os.path.join(extern_dir, "script")


def sleep_ms(milliseconds: float):
    start = time.perf_counter()
    end = start + milliseconds / 1000.0
    while time.perf_counter() < end:
        pass


def get_url_text_content(url: str):
    content = None
    try:
        response = requests.get(url, stream=True)
        content = response.text
        sleep_ms(50 + random.random() * 100)
    except requests.exceptions.RequestException as e:
        print(f"error : {e}")
    return content


def recreate_path(pathname: str):
    try:
        if os.path.exists(pathname):
            shutil.rmtree(pathname)
        os.makedirs(pathname)
    except Exception as e:
        print(f"error when recreate path '{pathname}'.")
        exit(1)


def save_content(content: str, filename: str):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, mode="w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        print(f"Error when saving content to {filename}: {e}")


def colllect_files():
    readme = get_url_text_content(
        "https://raw.githubusercontent.com/luestr/ProxyResource/refs/heads/main/README.md"
    )
    save_content(readme, os.path.join(extern_dir, "README"))

    filenames = []
    recreate_path(extern_plugin_dir)
    for item in readme.split('"'):
        if not item.endswith(".plugin"):
            continue

        plugin_url = item[46:]
        plugin_content = get_url_text_content(plugin_url)
        if plugin_content == None:
            continue

        plugin_filename = os.path.join(extern_plugin_dir, item.split("/")[-1])
        save_content(plugin_content, plugin_filename)
        filenames.append(plugin_filename)

    return filenames


def save_plugin_scripts(plugin_name: str, data: list[str]):
    local_dir = os.path.join(extern_script_dir, plugin_name)
    recreate_path(local_dir)

    for line in data:
        if line[0] == "[" or line[0] == "#" or line[0] == ";" or line[0] == "\n":
            continue
        item = line.split(",")[0]
        pos = item.find("script-path")
        if pos == -1:
            continue
        script_url = item.split("=")[-1].strip()
        script_content = get_url_text_content(script_url)
        if script_content == None:
            continue

        script_filename = os.path.join(local_dir, script_url.split("/")[-1])
        save_content(script_content, script_filename)

        sleep_ms(50 + random.random() * 100)

    if not os.listdir(local_dir):
        try:
            shutil.rmtree(local_dir)
        except Exception as e:
            print(f"error when remove path '{local_dir}'.")
            exit(1)


def extract_components(plugin_name: str, content: str):
    lines = []
    for line in content:
        lines.append(line.strip())

    data = {}
    line_index = 0
    data["title"] = []
    while line_index < len(lines):
        if len(lines[line_index]) == 0:
            data["title"].append("\n")
            line_index += 1
        elif lines[line_index][0] != "[":
            data["title"].append(f"{lines[line_index]}\n")
            line_index += 1
        else:
            break

    while line_index < len(lines):
        item_name = lines[line_index]
        line_index += 1
        data[item_name] = []
        while line_index < len(lines):
            if len(lines[line_index]) == 0:
                data[item_name].append("\n")
                line_index += 1
            elif lines[line_index][0] != "[":
                data[item_name].append(f"{lines[line_index]}\n")
                line_index += 1
            else:
                break

    empty_keys = []
    for key in data:
        if key == "title":
            continue
        empty = True
        for line in data[key]:
            if line[0] != "[" and line[0] != "#" and line[0] != ";" and line[0] != "\n":
                empty = False
                break
        if empty:
            empty_keys.append(key)
    for key in empty_keys:
        del data[key]

    script_key = ""
    has_script = False
    for key in data:
        if str(key).lower() == "[script]":
            has_script = True
            script_key = key
    if has_script:
        save_plugin_scripts(plugin_name, data[script_key])

    ret = {}
    for key in data:
        ret[key] = ""
        for line in data[key]:
            ret[key] += line

    return ret


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
    data = extract_components(filename.split(".")[0], content)

    has_content = False
    content_without_script = data["title"]
    for key in data:
        if key == "title" or str(key).lower() == "[script]":
            continue
        if str(key).lower() != "[mitm]":
            has_content = True
        content_without_script += f"{key}\n{data[key]}"
    if has_content:
        output_filename_without_scripts = os.path.join(
            current_dir, "plugin_without_script", filename
        )
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
        output_filename_scripts = os.path.join(
            current_dir, "plugin_with_script", filename
        )
        save_content(content_scripts, output_filename_scripts)


if __name__ == "__main__":
    random.seed(time.time())

    filenames = colllect_files()

    recreate_path(extern_script_dir)
    recreate_path(os.path.join(current_dir, "plugin_without_script"))
    recreate_path(os.path.join(current_dir, "plugin_with_script"))

    for filename in filenames:
        process_file(filename)
