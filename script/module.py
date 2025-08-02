import os
import requests
import shutil


current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
plugin_all_dir = os.path.join(current_dir, "extern", "ProxyResource", "plugin")


def recreate_path(pathname: str):
    try:
        if os.path.exists(pathname):
            shutil.rmtree(pathname)
        os.makedirs(pathname)
    except Exception as e:
        print(f"error when recreate path '{pathname}': {e}")
        exit(1)


def get_url_text_content(url: str):
    content, err_info = "", None
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
    if content.find("Response code 404 (Not Found)") != -1:
        content = ""
    return content


def save_content(content: str, filename: str):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, mode="w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        print(f"Error when saving content to {filename}: {e}")


def extract_components(lines: list[str]):
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


def modify_content_common(content: str, file_ext: str):
    lines = content.splitlines()
    empty_content = True
    for line in lines:
        if len(line) > 0 and line[0] == "[" and line.lower() != "[mitm]":
            empty_content = False
            break
    if empty_content:
        return ""

    data = extract_components(lines)

    data["title"] = [
        item
        for item in data["title"]
        if (
            item.find("system=") == -1
            and item.find("system_version=") == -1
            and item.find("loon_version=") == -1
        )
    ]

    if "[Script]" in data:
        arguments: set[str] = set([])
        for i, line in enumerate(data["[Script]"]):
            if line.startswith("#") or line.find("script-path") == -1:
                continue
            if file_ext == "sgmodule":
                line = line.strip()
                arg_pos_begin = line.find("argument=")
                if arg_pos_begin != -1:
                    arg_pos_end = line.find("}]", arg_pos_begin)
                    if arg_pos_end != -1:
                        arg_pos_end += 2
                        args = line[arg_pos_begin + 11 : arg_pos_end - 1]
                        pos_temp = line[:arg_pos_begin].rfind(",")
                        if arg_pos_end < len(line) and line[arg_pos_end] == '"':
                            arg_pos_end += 1
                        line = line[:pos_temp] + line[arg_pos_end:] + ", argument="
                        args = [item.strip()[1:-1] for item in args.split(",")]
                        for arg_idx in range(0, len(args)):
                            arguments.add(args[arg_idx])
                            if arg_idx > 0:
                                line = f"{line}&"
                            line = (
                                f'{line}{args[arg_idx]}="{{{{{{{args[arg_idx]}}}}}}}"'
                            )
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


def modify_content_bilibili(content: str):
    lines = content.splitlines()
    data = extract_components(lines)

    data["title"] = [
        item
        for item in data["title"]
        if (
            item.find("system=") == -1
            and item.find("system_version=") == -1
            and item.find("loon_version=") == -1
        )
    ]
    if "[Body Rewrite]" in data:
        for i, line in enumerate(data["[Body Rewrite]"]):
            if line.startswith("http-response-jq #"):
                data["[Body Rewrite]"][i] = line.replace(
                    "http-response-jq #", "# http-response-jq"
                )

    if "[Script]" in data:
        for i, line in enumerate(data["[Script]"]):
            if line.startswith("#") or line.find("script-path") == -1:
                continue
            line = line.strip()
            arg_pos_begin = line.find("argument=")
            if (
                arg_pos_begin != -1
                and line.find("Bilibili_proto_response_kokoryh") != -1
            ):
                arg_pos_end = line.find("}]", arg_pos_begin)
                if arg_pos_end != -1:
                    arg_pos_end += 2
                    pos_temp = line[:arg_pos_begin].rfind(",")
                    if arg_pos_end < len(line) and line[arg_pos_end] == '"':
                        arg_pos_end += 1
                    line = (
                        line[:pos_temp]
                        + line[arg_pos_end:]
                        + ', argument="{"showUpList":"{{{动态最常访问}}}","filterTopReplies":{{{过滤置顶评论广告}}}","airborne":{{{空降助手}}}","logLevel":{{{日志等级}}}}"'
                    )
            data["[Script]"][i] = f"{line}, script-update-interval=-1\n"

    line_arg = (
        "#!arguments=动态最常访问:auto,过滤置顶评论广告:1,空降助手:false,日志等级:off\n"
    )
    line_arg += "#!arguments-desc=动态最常访问: [true, false, auto]\\n- true: 始终显示\\n- false: 始终隐藏\\n- auto: 仅当列表中存在直播状态时显示\\n\\n过滤置顶评论广告: [1, 0]\\n- 1: 开启\\n- 0: 关闭\\n\\n空降助手: [false, true]\\n- 1: 开启\\n- 0: 关闭\\n\\n日志等级: [off, error, warn, info, debug]\n"
    for i, line in enumerate(data["title"]):
        if i == len(data["title"]) - 1 or len(data["title"][i + 1].strip()) == 0:
            data["title"][i] = line + line_arg
            break

    ret = ""
    for key, sub_data in data.items():
        str_tmp = f"{key}\n" if key != "title" else ""
        for line in sub_data:
            str_tmp = str_tmp + line
        ret = ret + str_tmp

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
        i += 1

    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1
    return ret


def process_file(
    filename: str, file_ext: str, dst_dir: str, url_dir: str, categoty: str
):
    url = f"https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/{url_dir}/{filename}"
    request_url = f"http://localhost:9101/file/_start_/{url}/_end_/sample.txt?type=loon-plugin&del=true&nore=true&category={categoty}"
    if file_ext == "sgmodule":
        request_url = (
            f"{request_url}&target=surge-module&sni=REJECT&pm=REJECT&jqEnabled=true"
        )
    else:
        request_url = f"{request_url}&target=stash-stoverride&jqEnabled=true"

    content = get_url_text_content(request_url)
    if len(content.strip()) != 0:
        if file_ext == "sgmodule":
            if filename == "Bilibili_remove_ads.plugin":
                content = modify_content_bilibili(content)
            else:
                content = modify_content_common(content, file_ext)

            if filename == "Taobao_remove_ads.plugin":
                content = modify_content_taobao(content)
            if filename == "Zhihu_remove_ads.plugin":
                content = modify_content_zhihu(content)

            if len(content.strip()) != 0:
                save_content(
                    content,
                    os.path.join(
                        dst_dir, f"{filename[:filename.rfind('.')]}.{file_ext}"
                    ),
                )
        else:
            save_content(
                content,
                os.path.join(dst_dir, f"{filename[:filename.rfind('.')]}.{file_ext}"),
            )


###############################################################################
#
# main
#
###############################################################################

if __name__ == "__main__":
    for file_ext in ["sgmodule", "stoverride"]:
        dst_dir = os.path.join(current_dir, file_ext)
        recreate_path(dst_dir)
        for filename in os.listdir(plugin_all_dir):
            process_file(
                filename,
                file_ext,
                dst_dir=dst_dir,
                url_dir="plugin/raw",
                categoty="iKeLee",
            )
