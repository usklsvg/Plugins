import os
import requests
import shutil

current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
plugin_all_dir = os.path.join(current_dir, "extern", "ProxyResource", "plugin")
sgmodule_dir = os.path.join(current_dir, "sgmodule")
module_dir = os.path.join(current_dir, "module")


def recreate_path(pathname: str):
    try:
        if os.path.exists(pathname):
            shutil.rmtree(pathname)
        os.makedirs(pathname)
    except Exception as e:
        print(f"error when recreate path '{pathname}': {e}")
        exit(1)


def get_url_text_content(url: str):
    content, err_info = None, None
    for _ in range(3):
        try:
            for i in range(3):
                response = requests.get(url, stream=True)
                content = response.text
                if content != None:
                    break
        except requests.exceptions.RequestException as e:
            err_info = e
        err_info = None
        break
    if err_info:
        print(f"error : {err_info}")
    return content


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
# convert plugin to module
#
###############################################################################


def modify_content_common(content: str, type: str):
    lines = content.splitlines()
    empty_content = True
    for line in lines:
        if len(line) > 0 and line[0] == "[" and line.lower() != "[mitm]":
            empty_content = False
            break
    if empty_content:
        return None

    data = extract_components(lines)
    if not "[Script]" in data:
        return content

    arguments: set[str] = set([])
    for i, line in enumerate(data["[Script]"]):
        if line.startswith("#") or line.find("script-path") == -1:
            continue
        if type == "sr":
            data["[Script]"][i] = line.replace(
                "Script-Hub-Org/Script-Hub/main/scripts/body-rewrite.js",
                f"usklsvg/Plugins/refs/heads/main/script/body-rewrite-sr.js",
            )
        else:
            items = [item.strip() for item in line.split(", ")]
            line = items[0]
            for j in range(1, len(items)):
                if (
                    items[j].lower().startswith("argument")
                    and items[j].lower().find("{") != -1
                ):
                    sub_arguments = items[j].split("},{")
                    sub_arguments[0] = sub_arguments[0][
                        sub_arguments[0].find("{") + 1 :
                    ]
                    sub_arguments[-1] = sub_arguments[-1][: sub_arguments[-1].find("}")]
                    items[j] = "argument="
                    for k, item in enumerate(sub_arguments):
                        arguments.add(item)
                        if k != 0:
                            items[j] += "&"
                        items[j] += item + '="{{{' + item + '}}}"'
                    _ = 1
                line = f"{line}, {items[j]}"
            data["[Script]"][i] = f"{line}, script-update-interval=-1\n"

    if len(arguments) > 0:
        arg_exist = False
        for line in data["title"]:
            if line.startswith("#!arguments"):
                arg_exist = True
                break
        if not arg_exist:
            line_arg = "#!arguments="
            for i, arg in enumerate(sorted(list(arguments))):
                if i == 0:
                    line_arg += arg
                else:
                    line_arg += f", {arg}"
            line_arg += "\n"
            for i, line in enumerate(data["title"]):
                if (
                    i == len(data["title"]) - 1
                    or len(data["title"][i + 1].strip()) == 0
                ):
                    data["title"][i] = line + line_arg
                    break

    ret = ""
    for key, sub_data in data.items():
        str_tmp = f"{key}\n" if key != "title" else ""
        for line in sub_data:
            str_tmp = str_tmp + line
        ret = ret + str_tmp

    return ret


def modify_content_amap(content: str):
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].find("search\\/sp") != -1:
            lines[i] = lines[i].replace("|search\\/sp|", "|")
        i += 1

    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1
    return ret


def modify_content_bilibili(content: str):
    lines = content.splitlines()

    for i, line in enumerate(lines):
        if (
            line.startswith("#")
            or line.find("script-path") == -1
            or line.find("argument") == -1
        ):
            continue
        items = [item.strip() for item in line.split(", ")]
        line = items[0]
        for j in range(1, len(items)):
            if (
                items[j].lower().startswith("argument")
                and items[j].lower().find("{") != -1
            ):
                continue
            line = f"{line}, {items[j]}"
        lines[i] = line

    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1
    return ret


def modify_content_taobao(content: str):
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        lines[i] = lines[i].replace(
            "https://kelee.one/Resource/Script/Taobao/Taobao_remove_ads.js",
            "https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/script/Taobao_remove_ads.js",
        )
        i += 1
    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1
    return ret


def modify_content_zhihu(content: str):
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        lines[i] = lines[i].replace(
            "https://kelee.one/Resource/Script/Zhihu/Zhihu_remove_ads.js",
            "https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/script/Zhihu_remove_ads.js",
        )
        if lines[i].find("next-(?:bff|data|render)") != -1:
            temp = lines[i]
            temp_0 = temp.replace("next-(?:bff|data|render)", "next-(?:bff|data)")
            temp_1 = temp.replace(
                "next-(?:bff|data|render)",
                "next-render(?!.*sub_scenes=billboard_weekly)",
            )
            lines[i] = f"{temp_0}\n\n{temp_1}"
        i += 1

    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1
    return ret


def process_file(type: str, src_dir: str, dst_dir: str, url_dir: str, categoty: str):
    for filename in os.listdir(src_dir):
        url = f"https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/{url_dir}/{filename}"
        request_url = f"http://localhost:9101/file/_start_/{url}/_end_/sample.sgmodule.txt?type=loon-plugin&del=true&nore=true&category={categoty}"
        if type == "sr":
            request_url = f"{request_url}&target=shadowrocket-module"
        else:
            request_url = (
                f"{request_url}&target=surge-module&sni=REJECT&pm=REJECT&jqEnabled=true"
            )

        content = get_url_text_content(request_url)
        if content != None:
            if filename == "Bilibili_remove_ads.plugin":
                content = modify_content_bilibili(content)

            content = modify_content_common(content, type)

            if filename == "Amap_remove_ads.plugin":
                content = modify_content_amap(content)
            if filename == "Taobao_remove_ads.plugin":
                content = modify_content_taobao(content)
            if filename == "Zhihu_remove_ads.plugin":
                content = modify_content_zhihu(content)

            if content != None:
                module_name = f"{filename[:filename.rfind('.')]}.{'module' if type == 'sr' else 'sgmodule'}"
                save_content(
                    content,
                    os.path.join(dst_dir, module_name),
                )


###############################################################################
#
# main
#
###############################################################################

if __name__ == "__main__":
    recreate_path(sgmodule_dir)
    process_file(
        "sg",
        src_dir=plugin_all_dir,
        dst_dir=sgmodule_dir,
        url_dir="plugin/raw",
        categoty="iKeLee",
    )

    recreate_path(module_dir)
    process_file(
        "sr",
        src_dir=plugin_all_dir,
        dst_dir=module_dir,
        url_dir="plugin/raw",
        categoty="iKeLee",
    )
