import os
import requests
import shutil

current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
plugin_all_dir = os.path.join(current_dir, "extern", "ProxyResource", "plugin")
plugin_no_script_dir = os.path.join(current_dir, "plugin", "no_script")
plugin_only_script_dir = os.path.join(current_dir, "plugin", "only_script")
module_all_dir = os.path.join(current_dir, "module", "all")
module_no_script_dir = os.path.join(current_dir, "module", "no_script")
module_only_script_dir = os.path.join(current_dir, "module", "only_script")


def recreate_path(pathname: str):
    try:
        if os.path.exists(pathname):
            shutil.rmtree(pathname)
        os.makedirs(pathname)
    except Exception as e:
        print(f"error when recreate path '{pathname}': {e}")
        exit(1)


def get_url_text_content(url: str):
    content = None
    try:
        for i in range(3):
            response = requests.get(url, stream=True)
            content = response.text
            if content != None:
                break
    except requests.exceptions.RequestException as e:
        print(f"error : {e}")
    return content


def save_content(content: str, filename: str):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, mode="w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        print(f"Error when saving content to {filename}: {e}")


def modify_content_common(content: str):
    lines = content.splitlines()

    empty_content = True
    for line in lines:
        if len(line) > 0 and line[0] == "[" and line.lower() != "[mitm]":
            empty_content = False
            break
    if empty_content:
        return None

    i = 0
    while i < len(lines):
        if lines[i].lower() == "[script]":
            i += 1
            break
        i += 1
    while i < len(lines):
        if len(lines[i]) > 1:
            if lines[i][0] != "#" and lines[i].find("script-path") != -1:
                lines[i] = lines[i].replace(
                    "Script-Hub-Org/Script-Hub/main/scripts/body-rewrite.js",
                    "usklsvg/Plugins/refs/heads/main/script/body-rewrite.js",
                )
                lines[i] += ", script-update-interval=-1"
            elif lines[i][0] == "[":
                break
        i += 1

    ret = ""
    i = 0
    while i < len(lines):
        ret += f"{lines[i]}\n"
        i += 1

    return ret


def modify_content_bilibili(content: str):
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].find("Popular") != -1:  # 注释移除热门话题
            lines[i] = f"# {lines[i]}"
        elif lines[i].find("DmView") != -1:  # 注释移除交互式弹幕
            lines[i] = f"# {lines[i]}"
        elif lines[i].find("resource\/show\/tab\/v2") != -1:  # 注释精简首页顶部标签
            lines[i] = f"# {lines[i]}"
        elif lines[i].find("search\/square") != -1:  # 注释移除热搜广告
            lines[i] = f"# {lines[i]}"
        elif lines[i].find("account") != -1:  # 注释精简我的页面
            lines[i] = f"# {lines[i]}"
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
        # 注释 我的页面
        if lines[i].startswith("^https:\/\/api\.zhihu\.com\/me\/guides"):
            lines[i] = f"# {lines[i]}"
        elif lines[i].startswith(
            "^https:\/\/api\.zhihu\.com\/people\/homepage_entry_v2"
        ):
            lines[i] = f"# {lines[i]}"
        elif lines[i].startswith("^https:\/\/api\.zhihu\.com\/unlimited\/go\/my_card"):
            lines[i] = f"# {lines[i]}"
        elif lines[i].startswith("^https:\/\/www\.zhihu\.com\/appview\/v3\/zhmore"):
            lines[i] = f"# {lines[i]}"
        # elif lines[i].find("^https:\/\/api\.zhihu\.com\/search\/recommend_query\/v2\?") != -1:
        #     lines[i] = f"# {lines[i]}"
        elif lines[i].find("script-path") != -1:
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


def modify_content_taobao(content: str):
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].find("script-path") != -1:
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


def process_file(src_dir: str, dst_dir: str, url_dir: str, categoty: str):
    recreate_path(dst_dir)
    for filename in os.listdir(src_dir):
        url = f"https://raw.githubusercontent.com/usklsvg/Plugins/refs/heads/main/{url_dir}/{filename}"
        request_url = f"http://localhost:9101/file/_start_/{url}/_end_/sample.sgmodule.txt?type=loon-plugin&target=surge-module&sni=REJECT&del=true&category={categoty}"
        content = get_url_text_content(request_url)
        if content == None:
            continue

        content = modify_content_common(content)
        if filename == "Bilibili_remove_ads.plugin":
            content = modify_content_bilibili(content)
        elif filename == "Zhihu_remove_ads.plugin":
            content = modify_content_zhihu(content)
        elif filename == "Taobao_remove_ads.plugin":
            content = modify_content_taobao(content)

        if content == None:
            continue
        module_name = f"{filename[:filename.rfind('.')]}.sgmodule"
        save_content(
            content,
            os.path.join(dst_dir, module_name),
        )


if __name__ == "__main__":
    process_file(
        src_dir=plugin_all_dir,
        dst_dir=module_all_dir,
        url_dir="extern/ProxyResource/plugin",
        categoty="iKeLee",
    )

    process_file(
        src_dir=plugin_no_script_dir,
        dst_dir=module_no_script_dir,
        url_dir="plugin/no_script",
        categoty=f"iKeLee%20-%20Rules%20%26%20Rewrites",
    )

    process_file(
        src_dir=plugin_only_script_dir,
        dst_dir=module_only_script_dir,
        url_dir="plugin/only_script",
        categoty=f"iKeLee%20-%20Scripts",
    )
