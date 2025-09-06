import os
import requests
import shutil
from tqdm import tqdm


current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
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
            if file_ext == "sgmodule":
                line = line.strip()
                data["[Script]"][i] = f"{line}, script-update-interval=-1\n"

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
            "https://kelee.one/Resource/JavaScript/Taobao/Taobao_remove_ads.js",
            "https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/script/Taobao_remove_ads.js",
        )
        i += 1
    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1
    return ret


def modify_content_bilibili(content: str):
    lines = content.splitlines()
    data = extract_components(lines)

    for i, line in enumerate(data["title"]):
        if line.startswith("#!arguments"):
            data["title"][
                i
            ] = '#!arguments=动态最常访问:show,移除评论区置顶广告:1,空降助手:0,日志等级:"off"\n'
            data["title"][
                i
            ] += "#!arguments-desc=动态最常访问: [show, hide, auto]\\n- show: 始终显示\\n- hide: 始终隐藏\\n- auto: 仅当列表中存在直播状态时显示"
            data["title"][
                i
            ] += "\\n\\n移除评论区置顶广告: [1, 0]\\n- 1: 开启\\n- 0: 关闭"
            # data["title"][i] += "\\n\\n空降助手: [1, 0]\\n- 1: 开启\\n- 0: 关闭"
            data["title"][
                i
            ] += '\\n\\n日志等级: ["off", "error", "warn", "info", "debug"]\n'

    for i, line in enumerate(data["[Script]"]):
        if line.startswith("#") or line.find("script-path") == -1:
            continue
        if line.find("Bilibili_proto_request_kokoryh") != -1:
            data["[Script]"][i] = f"# {data["[Script]"][i]}"
            continue
        line = line.strip()
        arg_pos_begin = line.find("argument=")
        if arg_pos_begin == -1:
            continue
        arg_pos_end = line.find("}]", arg_pos_begin)
        if arg_pos_end == -1:
            continue
        arg_pos_end += 2
        pos_temp = line[:arg_pos_begin].rfind(",")
        if arg_pos_end < len(line) and line[arg_pos_end] == '"':
            arg_pos_end += 1
        line = (
            line[:pos_temp]
            + line[arg_pos_end:]
            + ', argument="{"showUpList":"{{{动态最常访问}}}","purifyTopReplies":{{{移除评论区置顶广告}}},"airborne":0,"logLevel":{{{日志等级}}}}"'
        )
        data["[Script]"][i] = f"{line}\n"

    ret = ""
    for key, sub_data in data.items():
        str_tmp = f"{key}\n" if key != "title" else ""
        for line in sub_data:
            str_tmp = str_tmp + line
        ret = ret + str_tmp

    return ret


def process_file(
    filename: str, file_ext: str, dst_dir: str, url_dir: str, categoty: str
):
    url = f"https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/{url_dir}/{filename}"
    request_url = f"http://localhost:9100/file/_start_/{url}/_end_/sample.txt?type=loon-plugin&del=true&nore=true&category={categoty}"
    if file_ext == "sgmodule":
        request_url = (
            f"{request_url}&target=surge-module&sni=REJECT&pm=REJECT&jqEnabled=true"
        )
    else:
        request_url = f"{request_url}&target=stash-stoverride&jqEnabled=true"

    content = get_url_text_content(request_url)
    if len(content.strip()) != 0:
        if file_ext == "sgmodule":
            content = modify_content_common(content, file_ext)

            if filename.find("Taobao_remove_ads.") != -1:
                content = modify_content_taobao(content)
            if filename.find("Bilibili_remove_ads.") != -1:
                content = modify_content_bilibili(content)

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
        for filename in tqdm(os.listdir(plugin_all_dir)):
            process_file(
                filename,
                file_ext,
                dst_dir=dst_dir,
                url_dir="plugin",
                categoty="iKeLee",
            )
        if file_ext == "sgmodule":
            with open(
                os.path.join(dst_dir, "Node_detection_tool.sgmodule"),
                mode="w",
                encoding="utf-8",
            ) as f:
                f.write(
                    """#!name=节点检测工具
#!desc=节点检测工具，可进行地理位置、节点解锁、入口落地等查询。
#!author=xream[https://github.com/xream], Keywos[https://github.com/Keywos], KOP-XIAO[https://github.com/KOP-XIAO], dcpengx[https://github.com/dcpengx]
#!icon=https://raw.githubusercontent.com/luestr/IconResource/main/Other_icon/120px/Node_detection_tool.png
#!category=iKeLee
#!tag=节点检测
#!homepage=https://hub.kelee.one
#!date=2025-06-10 23:31:23

[Panel]
入口落地查询 = script-name=入口落地查询, title="入口落地查询", content="请刷新面板"
地理位置查询 = script-name=地理位置查询, title="地理位置查询", content="请刷新面板"
节点解锁查询 = script-name=节点解锁查询, title="节点解锁查询", content="请刷新面板"

[Script]
入口落地查询 = type=generic, script-path=https://kelee.one/Resource/JavaScript/Node_detection_tool/NetworkEntryAndExitQueries.js, script-update-interval=-1
地理位置查询 = type=generic, script-path=https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/script/LocationDetection.js, script-update-interval=-1
节点解锁查询 = type=generic, script-path=https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/script/NodeUnlockDetection.js, script-update-interval=-1"""
                )
