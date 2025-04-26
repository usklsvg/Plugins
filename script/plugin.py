import os
import shutil
import requests


current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
extern_dir = os.path.join(current_dir, "extern", "ProxyResource")
extern_plugin_dir = os.path.join(extern_dir, "plugin")
extern_script_dir = os.path.join(extern_dir, "script")
extern_jq_dir = os.path.join(extern_dir, "jq")
plugin_raw_dir = os.path.join(current_dir, "plugin", "raw")
plugin_no_script_dir = os.path.join(current_dir, "plugin", "no_script")
plugin_only_script_dir = os.path.join(current_dir, "plugin", "only_script")


def get_url_text_content(url: str):
    content = None
    try:
        response = requests.get(url, stream=True)
        content = response.text
    except requests.exceptions.RequestException as e:
        print(f"error : {e}")
    return content


def download_url_file(url: str, filename: str):
    headers = {"User-Agent": "script-hub/1.0.0"}
    err_info = None
    for _ in range(3):
        try:
            response = requests.get(url, headers=headers, stream=True)
            if response.status_code == 200:
                with open(filename, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            f.flush()
        except requests.exceptions.RequestException as e:
            err_info = e
        err_info = None
        break
    if err_info:
        print(f"error : {err_info}")


def recreate_path(pathname: str):
    try:
        if os.path.exists(pathname):
            shutil.rmtree(pathname)
        os.makedirs(pathname)
    except Exception as e:
        print(f"error when recreate path '{pathname}': {e}")
        exit(1)


def save_content(content: str, filename: str):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, mode="w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        print(f"Error when saving content to {filename}: {e}")


def extract_components(lines: str):
    lines = [line.strip() for line in lines]

    data: dict[str, list[str]] = {}
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

    return data


###############################################################################
#
# download extern
#
###############################################################################


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
        script_filename = os.path.join(local_dir, script_url.split("/")[-1])
        download_url_file(script_url, script_filename)

    if not os.listdir(local_dir):
        try:
            shutil.rmtree(local_dir)
        except Exception as e:
            print(f"error when remove path '{local_dir}': {e}")
            exit(1)


def save_plugin_jqs(plugin_name: str, data: list[str]):
    local_dir = os.path.join(extern_jq_dir, plugin_name)
    recreate_path(local_dir)

    for line in data:
        if line[0] == "[" or line[0] == "#" or line[0] == ";" or line[0] == "\n":
            continue
        items = [item for item in line.split() if item.find("jq-path") != -1]
        if len(items) == 0:
            continue

        script_url = items[0].split("=")[-1].strip()
        if script_url[0] == '"' or script_url[0] == "'":
            script_url = script_url[1:]
        if script_url[-1] == '"' or script_url[-1] == "'":
            script_url = script_url[:-1]
        script_filename = os.path.join(local_dir, script_url.split("/")[-1])
        download_url_file(script_url, script_filename)

    if not os.listdir(local_dir):
        try:
            shutil.rmtree(local_dir)
        except Exception as e:
            print(f"error when remove path '{local_dir}': {e}")
            exit(1)


def colllect_files():
    readme = get_url_text_content(
        "https://raw.githubusercontent.com/luestr/ProxyResource/refs/heads/main/README.md"
    )
    save_content(readme, os.path.join(extern_dir, "README.md"))

    filenames = []
    recreate_path(extern_plugin_dir)
    for item in readme.split('"'):
        if not item.endswith(".plugin"):
            continue

        plugin_url = item[46:]
        plugin_name = item.split("/")[-1]
        plugin_filename = os.path.join(extern_plugin_dir, plugin_name)
        download_url_file(plugin_url, plugin_filename)
        try:
            with open(plugin_filename, mode="r", encoding="utf-8") as f:
                content = f.readlines()
        except IOError as e:
            print(f"Error when reading content from {plugin_filename}: {e}")
            continue
        filenames.append(plugin_filename)
        data: dict[str, list[str]] = extract_components(content)

        script_key = ""
        has_script = False
        for key in data:
            if str(key).lower() == "[script]":
                has_script = True
                script_key = key
        if has_script:
            save_plugin_scripts(plugin_name[: plugin_name.rfind(".")], data[script_key])

        script_key = ""
        has_rewrite = False
        for key in data:
            if str(key).lower() == "[rewrite]":
                has_rewrite = True
                script_key = key
        if has_rewrite:
            save_plugin_jqs(plugin_name[: plugin_name.rfind(".")], data[script_key])

    return filenames


###############################################################################
#
# adjust
#
###############################################################################


def modify_content_bilibili(lines: list[str]):
    i = 0
    while i < len(lines):
        # 注释精简首页顶部标签
        if lines[i].find("resource\\/show\\/tab\\/v2") != -1:
            lines[i] = f"# {lines[i]}"
        # 注释精简我的页面
        if lines[i].find("account\\/mine") != -1:
            lines[i] = f"# {lines[i]}"
        # 注释移除热搜广告
        lines[i] = lines[i].replace("|v2\\/search\\/square|", "|")
        # 注释移除热门话题
        lines[i] = lines[i].replace("|show\\.v1\\.Popular\\/Index|", "|")
        # 注释移除交互式弹幕
        lines[i] = lines[i].replace(
            "|community\\.service\\.dm\\.v1\\.DM\\/DmView|", "|"
        )

        i += 1
    return lines


def modify_content_zhihu(lines: list[str]):
    i = 0
    while i < len(lines):
        # 注释 我的页面 - 项目列表、会员卡片
        if (
            lines[i].find("^https:\\/\\/api\\.zhihu\\.com\\/me\\/guides") != -1
            or lines[i].find(
                "^https:\\/\\/api\\.zhihu\\.com\\/people\\/homepage_entry_v2"
            )
            != -1
            or lines[i].find(
                "^https:\\/\\/api\\.zhihu\\.com\\/unlimited\\/go\\/my_card"
            )
            != -1
            or lines[i].find("^https:\\/\\/www\\.zhihu\\.com\\/appview\\/v3\\/zhmore")
            != -1
        ):
            lines[i] = f"# {lines[i]}"
        # 每周必看
        lines[i] = lines[i].replace(
            "next-(?:bff|data|render) ",
            "next-(?:bff|data|render(?!.*sub_scenes=billboard_weekly)) ",
        )

        i += 1
    return lines


def process_file(filename: str):
    try:
        with open(filename, mode="r", encoding="utf-8") as f:
            lines = f.readlines()
    except IOError as e:
        print(f"Error when reading content from {filename}: {e}")
        return

    filename = (filename.split("/")[-1]).split("\\")[-1]
    if filename.endswith("Bilibili_remove_ads.plugin"):
        lines = modify_content_bilibili(lines)
    elif filename.endswith("Zhihu_remove_ads.plugin"):
        lines = modify_content_zhihu(lines)

    data: dict[str, str] = {}
    for key, sub_data in extract_components(lines).items():
        str_tmp = f"{key}\n" if key != "title" else ""
        for line in sub_data:
            str_tmp = str_tmp + line
        data[key] = str_tmp

    content_raw = ""
    for key in data:
        content_raw += f"{data[key]}"
    output_filename_raw = os.path.join(plugin_raw_dir, filename)
    save_content(content_raw, output_filename_raw)

    has_content = False
    content_without_script = data["title"]
    for key in data:
        if key == "title" or str(key).lower() == "[script]":
            continue
        elif str(key).lower() != "[argument]" and str(key).lower() != "[mitm]":
            has_content = True
        content_without_script += f"{data[key]}"
    if has_content:
        output_filename_without_scripts = os.path.join(plugin_no_script_dir, filename)
        save_content(content_without_script, output_filename_without_scripts)

    has_script = False
    content_scripts = data["title"]
    for key in data:
        if str(key).lower() == "[script]":
            has_script = True
            content_scripts += f"{data[key]}"
        elif str(key).lower() == "[argument]" or str(key).lower() == "[mitm]":
            content_scripts += f"{data[key]}"
    if has_script:
        output_filename_scripts = os.path.join(plugin_only_script_dir, filename)
        save_content(content_scripts, output_filename_scripts)


if __name__ == "__main__":
    recreate_path(extern_script_dir)
    recreate_path(extern_jq_dir)
    filenames = colllect_files()

    recreate_path(plugin_raw_dir)
    recreate_path(plugin_no_script_dir)
    recreate_path(plugin_only_script_dir)
    for filename in filenames:
        process_file(filename)
