import os
import shutil
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


current_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
extern_dir = os.path.join(current_dir, "extern", "ProxyResource")
extern_plugin_dir = os.path.join(extern_dir, "plugin")
extern_script_dir = os.path.join(extern_dir, "script")
extern_jq_dir = os.path.join(extern_dir, "jq")
plugin_raw_dir = os.path.join(current_dir, "plugin", "raw")
plugin_no_script_dir = os.path.join(current_dir, "plugin", "no_script")
plugin_only_script_dir = os.path.join(current_dir, "plugin", "only_script")


def get_url_text_content(url: str):
    content = ""
    try:
        response = requests.get(url, stream=True)
        content = response.text
    except requests.exceptions.RequestException as e:
        print(f"error : {e}")
    return content


def download_url_file(url: str, filename: str):
    headers = {
        "User-Agent": "Loon/877 CFNetwork/3826.500.131 Darwin/24.5.0",
        "accept-language": "zh-CN,zh-Hans;q=0.0",
        "accept-encoding": "gzip, defalte, br",
    }
    err_info = None
    for _ in range(3):
        try:
            response = requests.get(url, headers=headers, stream=True)
            if response.status_code != 200:
                print(
                    f'status code {response.status_code} when downloading from "{url}"'
                )
                continue
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


def download_rendered_webpage(url, output_filename, wait_time):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = None

    try:
        print(f"Initialize with chromedriver path")
        service = Service()

        print(f"Opening URL: {url}")
        driver = webdriver.Chrome(service=service, options=chrome_options)

        driver.get(url)
        print(f"Waiting for {wait_time} seconds for JavaScript to execute...")
        time.sleep(wait_time)

        if not "loon://import?plugin=" in driver.page_source.lower():
            print("need process manually for Cloudflare challenge")
            return

        rendered_html = driver.page_source
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        print(f"Webpage successfully downloaded to {output_filename}")

    except WebDriverException as e:
        print(f"An error occurred with the WebDriver: {e}")
        print("Please ensure ChromeDriver is correctly installed and its path is set.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if driver:
            driver.quit()


def recreate_path(pathname: str):
    os.makedirs(pathname, exist_ok=True)
    # try:
    #     if os.path.exists(pathname):
    #         shutil.rmtree(pathname)
    #     os.makedirs(pathname)
    # except Exception as e:
    #     print(f"error when recreate path '{pathname}': {e}")
    #     exit(1)


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
    content_path = os.path.join(extern_dir, "pluginhub.html")
    download_rendered_webpage(
        "https://pluginhub.kelee.one/", output_filename=content_path, wait_time=5
    )
    with open(content_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    plugin_url_list = [
        item.split('"')[1][21:]
        for item in lines
        if item.find("loon://import?plugin=") != -1
    ]

    recreate_path(extern_plugin_dir)
    filenames = []
    for plugin_url in plugin_url_list:
        if not (plugin_url.endswith(".lpx") or plugin_url.endswith(".plugin")):
            continue

        plugin_name = plugin_url.split("/")[-1]
        plugin_name = plugin_name[: plugin_name.rfind(".")] + ".plugin"
        plugin_filename = os.path.join(extern_plugin_dir, plugin_name)
        download_url_file(plugin_url, plugin_filename)
        if not os.path.exists(plugin_filename):
            print(f'Error when downloading "{plugin_filename}" from "{plugin_url}".')
            continue

        try:
            with open(plugin_filename, mode="r", encoding="utf-8") as f:
                content = f.readlines()
        except IOError as e:
            print(f"Error when reading content from {plugin_filename}: {e}")
            continue
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
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
        lines[i] = lines[i].replace("show\\.v1\\.Popular\\/Index|", "")
        # 注释移除交互式弹幕
        lines[i] = lines[i].replace(
            "|community\\.service\\.dm\\.v1\\.DM\\/DmView|", "|"
        )
        # 注释空降助手
        if lines[i].find("Bilibili_airborne_kokoryh") != -1:
            lines[i] = f"# {lines[i]}"

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


###############################################################################
#
# create DNS plugin
#
###############################################################################


class TrieNode:
    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.end_of_word = False
        self.valid = True


class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, valid: bool = True):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.end_of_word = True
        node.valid = valid

    def get_prefix(self) -> list[str]:
        result: list[str] = []

        def dfs(node, current_prefix: str):
            if node.end_of_word:
                if node.valid:
                    result.append(current_prefix)
            else:
                for char, child in node.children.items():
                    dfs(child, f"{current_prefix}{char}")

        dfs(self.root, "")

        return result


class DomainRules:
    def __init__(self):
        self.domains: list[str] = []
        self.domain_suffixs: list[str] = []
        self.domain_keywords: list[str] = []


def get_rules(predefined: DomainRules, url: str):
    ## get rules

    domains: list[str] = []
    domain_suffixs: list[str] = []
    domain_keywords: list[str] = []

    content = get_url_text_content(url)
    rules = [item.strip() for item in content.split("\n") if item.startswith("D")]
    for rule in rules:
        items = [item for item in rule.split(",") if item.strip()]
        if rule.startswith("DOMAIN,"):
            domains.append(items[1])
        elif rule.startswith("DOMAIN-SUFFIX,"):
            domain_suffixs.append(f".{items[1]}")
        elif rule.startswith("DOMAIN-KEYWORD,"):
            domain_keywords.append(items[1])

    ## remove duplicate keywords

    domain_keywords = [
        item
        for item in domain_keywords
        if not any(keyword in item for keyword in predefined.domain_keywords)
    ]

    ## remove duplicate suffixs

    temp_list = [
        suffix
        for suffix in domain_suffixs
        if (
            (not any(keyword in suffix for keyword in domain_keywords))
            and (not any(keyword in suffix for keyword in predefined.domain_keywords))
        )
    ]
    trie = Trie()

    for suffix in temp_list:
        reversed_suffix = suffix[::-1]
        trie.insert(reversed_suffix)

    for suffix in predefined.domain_suffixs:
        reversed_suffix = suffix[::-1]
        trie.insert(reversed_suffix, False)

    domain_suffixs = sorted([item[::-1] for item in trie.get_prefix()])

    ## remove duplicate suffixs

    domains = [
        domain
        for domain in domains
        if (
            (not any(keyword in domain for keyword in domain_keywords))
            and (not any(keyword in domain for keyword in predefined.domain_keywords))
        )
    ]
    domains = [
        domain
        for domain in domains
        if (
            (not any(domain.endswith(suffix) for suffix in domain_suffixs))
            and (
                not any(domain.endswith(suffix) for suffix in predefined.domain_suffixs)
            )
        )
    ]

    current_rules = DomainRules()
    current_rules.domains = domains
    current_rules.domain_suffixs = domain_suffixs
    current_rules.domain_keywords = domain_keywords

    return current_rules


def create_dns_plugin():
    content_plugin = """#!name=Enhanced DNS
#!desc=使用系统 DNS 解析一部分苹果，微软，以及内地常见域名
#!icon=https://raw.githubusercontent.com/Koolson/Qure/master/IconSet/Color/Server.png
#!category=DNS

[Host]
"""

    # 包含内地常见域名
    rules_china = DomainRules()
    rules_china.domain_suffixs = [".cdn-apple.com"]
    rules_china = get_rules(
        rules_china,
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/ChinaDomain.list",
    )
    for domain in rules_china.domains:
        content_plugin = f"{content_plugin}{domain} = server:system\n"
    if len(rules_china.domain_suffixs) > 0:
        content_plugin = f"{content_plugin}\n"
    for suffix in rules_china.domain_suffixs:
        content_plugin = f"{content_plugin}*{suffix} = server:system\n"
    if len(rules_china.domain_keywords) > 0:
        content_plugin = f"{content_plugin}\n"
    for keyword in rules_china.domain_keywords:
        content_plugin = f"{content_plugin}*{keyword}* = server:system\n"

    # 不包含 AppleProxy
    rules_china.domain_suffixs.append(".cdn-apple.com")
    rules_apple_proxy = get_rules(
        rules_china,
        "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/refs/heads/master/rule/Loon/AppleProxy/AppleProxy.list",
    )
    rules_china.domain_suffixs.pop()
    rules_apple_proxy.domains += rules_china.domains
    rules_apple_proxy.domain_keywords += rules_china.domain_keywords
    rules_apple_proxy.domain_suffixs += rules_china.domain_suffixs

    # 包含 Apple
    rules_apple = get_rules(
        rules_apple_proxy,
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/Apple.list",
    )
    if len(rules_apple.domains) > 0:
        content_plugin = f"{content_plugin}\n"
    for domain in rules_apple.domains:
        content_plugin = f"{content_plugin}{domain} = server:system\n"
    if len(rules_apple.domain_suffixs) > 0:
        content_plugin = f"{content_plugin}\n"
    for suffix in rules_apple.domain_suffixs:
        content_plugin = f"{content_plugin}*{suffix} = server:system\n"
    if len(rules_apple.domain_keywords) > 0:
        content_plugin = f"{content_plugin}\n"
    for keyword in rules_apple.domain_keywords:
        content_plugin = f"{content_plugin}*{keyword}* = server:system\n"

    # 不包含 OneDrive
    rules_onedrive = DomainRules()
    rules_onedrive = get_rules(
        rules_onedrive,
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/OneDrive.list",
    )
    rules_onedrive.domains += rules_china.domains
    rules_onedrive.domain_keywords += rules_china.domain_keywords
    rules_onedrive.domain_suffixs += rules_china.domain_suffixs

    # 包含 Microsoft
    rules_ms = get_rules(
        rules_onedrive,
        "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/refs/heads/master/Clash/Microsoft.list",
    )
    if len(rules_ms.domains) > 0:
        content_plugin = f"{content_plugin}\n"
    for domain in rules_ms.domains:
        content_plugin = f"{content_plugin}{domain} = server:system\n"
    if len(rules_ms.domain_suffixs) > 0:
        content_plugin = f"{content_plugin}\n"
    for suffix in rules_ms.domain_suffixs:
        content_plugin = f"{content_plugin}*{suffix} = server:system\n"
    if len(rules_ms.domain_keywords) > 0:
        content_plugin = f"{content_plugin}\n"
    for keyword in rules_ms.domain_keywords:
        content_plugin = f"{content_plugin}*{keyword}* = server:system\n"

    module_path = os.path.join(current_dir, "plugin", "raw", "Enhanced_DNS.plugin")
    with open(module_path, "w", encoding="utf-8") as f:
        f.write(content_plugin)


if __name__ == "__main__":
    recreate_path(extern_script_dir)
    recreate_path(extern_jq_dir)
    filenames = colllect_files()

    recreate_path(plugin_raw_dir)
    recreate_path(plugin_no_script_dir)
    recreate_path(plugin_only_script_dir)
    for filename in filenames:
        process_file(filename)
    create_dns_plugin()
