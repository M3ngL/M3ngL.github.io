import base64
import json
import os
import re
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import PathCompleter

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

PASSWORD_FILE = ".blog_lock_key"
POSTS_DIR = "_posts"
IMG_DIR = "pic"
ITERATIONS = 200000


def encrypt_html(html: str, password: str) -> str:
    """使用 AES-256-GCM + PBKDF2-SHA256 加密 HTML，返回 Base64 编码的密文包。"""
    salt = os.urandom(16)
    iv = os.urandom(12)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(iv, html.encode("utf-8"), None)
    payload = {
        "v": 1,
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
        "iter": ITERATIONS,
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


def render_markdown_to_html(md_text: str) -> str:
    """将 Markdown 渲染为 HTML，用于加密前本地处理。"""
    if not MARKDOWN_AVAILABLE:
        raise RuntimeError("请先安装 Python 依赖：pip install markdown pygments")
    md = markdown.Markdown(
        extensions=["extra", "codehilite"],
        extension_configs={
            "codehilite": {
                "css_class": "highlight",
                "use_pygments": True,
            }
        },
    )
    return md.convert(md_text)


def password_is_set() -> bool:
    return Path(PASSWORD_FILE).exists()


def read_password() -> str:
    with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def write_password(password: str):
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        f.write(password)


def set_password() -> str:
    while True:
        pw1 = getpass("请输入加密密码：")
        pw2 = getpass("请再次输入密码确认：")
        if not pw1:
            print("密码不能为空。")
            continue
        if pw1 != pw2:
            print("两次输入不一致，请重新设置。")
            continue
        write_password(pw1)
        print(f"密码已保存到 {PASSWORD_FILE}（该文件已被 .gitignore 忽略，请勿提交）。")
        return pw1


def ensure_password() -> str:
    if password_is_set():
        return read_password()
    print("尚未设置加密密码。")
    return set_password()


def process_images(md_text: str, img_dir: str = IMG_DIR) -> str:
    """下载远程图片到本地 pic/，并替换 Markdown 中的图片链接。"""
    img_pattern = re.compile(r"!\[([^\]]*)\]\((https?://[^\)]+)\)")
    matches = img_pattern.findall(md_text)
    modified = md_text

    os.makedirs(img_dir, exist_ok=True)

    for alt_text, url in matches:
        try:
            img_name = os.path.basename(urlparse(url).path)
            if not img_name:
                print(f"⚠️ 无法提取图片文件名: {url}，跳过")
                continue
            local_path = os.path.join(img_dir, img_name)
            if not os.path.exists(local_path):
                print(f"🌐 下载图片: {url}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                with open(local_path, "wb") as img_file:
                    img_file.write(response.content)

            new_md_img = f"![{alt_text}](/{img_dir}/{img_name})"
            old_md_img = f"![{alt_text}]({url})"
            modified = modified.replace(old_md_img, new_md_img)
        except Exception as e:
            print(f"⚠️ 下载失败: {url}，原因: {e}")

    return modified


def extract_title_and_content(md_text: str) -> tuple:
    """提取一级标题作为文章标题，并返回正文内容（移除标题行）。"""
    lines = md_text.splitlines(keepends=True)
    title = None
    content_lines = []

    for line in lines:
        if title is None:
            match_title = re.match(r"^#\s+(.+)", line.strip())
            if match_title:
                title = match_title.group(1).strip()
                continue

        # blog 使用的 Rouge 不支持 assembly，只支持 nasm
        if re.match(r"^````assembly\b", line.strip()):
            line = re.sub(r"^````assembly\b", "````nasm\n", line.strip())
        content_lines.append(line)

    return title, "".join(content_lines)


def find_existing_post(basename: str) -> Path | None:
    """根据源文件 basename 查找 _posts/ 中已生成的文章。"""
    posts_dir = Path(POSTS_DIR)
    if not posts_dir.exists():
        return None
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-" + re.escape(basename) + r"\.md$")
    for post in posts_dir.iterdir():
        if post.is_file() and pattern.match(post.name):
            return post
    return None


def extract_images(md_text: str) -> list[str]:
    """从 Markdown 正文中提取 pic/ 下的图片相对路径。"""
    pattern = re.compile(r"!\[([^\]]*)\]\((/?pic/[^\)]+)\)")
    return [m.group(2).lstrip("/") for m in pattern.finditer(md_text)]


def extract_lock_images(front_matter_text: str) -> list[str]:
    """从 front matter 的 lock_images 列表中提取图片路径。"""
    match = re.search(r"^lock_images:\s*(.*?)(?=^---|\Z)", front_matter_text, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    return [item.strip().strip('"\'') for item in re.findall(r"^\s*-\s*(.+)$", match.group(1), re.MULTILINE)]


def image_used_elsewhere(img_path: str, exclude_post: Path) -> bool:
    """检查某张图片是否被其他文章引用。"""
    posts_dir = Path(POSTS_DIR)
    if not posts_dir.exists():
        return False
    for post in posts_dir.glob("*.md"):
        if post.resolve() == exclude_post.resolve():
            continue
        try:
            text = post.read_text(encoding="utf-8")
            if img_path in text or f"/{img_path}" in text:
                return True
        except Exception:
            continue
    return False


def delete_post_and_images(post_path: Path):
    """删除旧文章及其未被其他文章引用的图片。"""
    print(f"🗑️  删除旧文章: {post_path}")
    text = post_path.read_text(encoding="utf-8")
    post_path.unlink()

    # 优先读取 front matter 中的 lock_images（加密文章正文已被加密）
    images = extract_lock_images(text)
    if not images:
        images = extract_images(text)

    for img_path in images:
        full_path = Path(img_path)
        if full_path.exists() and not image_used_elsewhere(img_path, post_path):
            print(f"🗑️  删除旧图片: {img_path}")
            full_path.unlink()
        elif full_path.exists():
            print(f"⏭️  图片仍被其他文章引用，保留: {img_path}")


def _choose_markdown(candidates: list[Path], base_dir: Path | None = None) -> str | None:
    """列出候选 Markdown 文件并让用户选择，仅一个时直接默认选中。"""
    candidates = sorted([c for c in candidates if c.is_file()])
    if not candidates:
        print("❌ 未找到 Markdown 文件。")
        return None

    if len(candidates) == 1:
        chosen = candidates[0]
        print(f"只有一个 Markdown 文件，自动选择：{chosen}")
        return str(chosen)

    for idx, path in enumerate(candidates, 1):
        if base_dir is not None:
            try:
                display = str(path.relative_to(base_dir))
            except ValueError:
                display = str(path)
        else:
            try:
                display = str(path.relative_to(Path.cwd()))
            except ValueError:
                display = str(path)
        print(f"{idx}. {display}")

    choice = input("请选择序号（默认 1）: ").strip()
    if not choice:
        choice = "1"
    if not choice.isdigit() or not (1 <= int(choice) <= len(candidates)):
        print("❌ 无效选择。")
        return None

    return str(candidates[int(choice) - 1])


def _read_path_prompt() -> str | None:
    """读取用户输入的路径；在交互式终端中通过 prompt_toolkit 提供 Tab 路径补全。"""
    if PROMPT_TOOLKIT_AVAILABLE and sys.stdin.isatty():
        completer = PathCompleter(expanduser=True)
        try:
            return prompt(
                "请输入 Markdown 文件路径: ",
                completer=completer,
            ).strip().strip('"')
        except (KeyboardInterrupt, EOFError):
            print()
            return None

    if not PROMPT_TOOLKIT_AVAILABLE:
        print("提示：安装 prompt_toolkit 后支持路径 Tab 补全。")
    return input("请输入 Markdown 文件路径: ").strip().strip('"')


def select_markdown_file() -> str | None:
    """获取 Markdown 文件路径，支持目录/glob/空输入/单文件默认选中。"""
    raw = _read_path_prompt()
    if raw is None:
        return None

    expanded = os.path.expanduser(raw)

    if not expanded:
        candidates = list(Path.cwd().glob("*.md"))
        return _choose_markdown(candidates, base_dir=Path.cwd())

    p = Path(expanded)
    if p.is_dir():
        candidates = list(p.glob("*.md"))
        return _choose_markdown(candidates, base_dir=p)

    if any(ch in expanded for ch in "*?["):
        import glob as glob_module

        candidates = [Path(m) for m in glob_module.glob(expanded)]
        return _choose_markdown(candidates)

    return expanded


def upload_post(src_path: str, category: str, encrypt: bool, reupload: bool):
    """处理单篇文章的上传/重新上传，可选择加密。"""
    src = Path(src_path)
    if not src.exists():
        print(f"❌ 文件不存在: {src_path}")
        return

    basename = src.stem
    today = datetime.now().strftime("%Y-%m-%d")

    if reupload:
        existing = find_existing_post(basename)
        if existing:
            delete_post_and_images(existing)
        else:
            print("ℹ️  未找到旧文章，跳过删除。")

    md_text = src.read_text(encoding="utf-8")
    md_text = process_images(md_text)
    title, content = extract_title_and_content(md_text)

    if not title:
        print(f"❌ 未找到一级标题，跳过: {src_path}")
        return

    os.makedirs(POSTS_DIR, exist_ok=True)

    local_images = extract_images(md_text)
    lock_images_lines = ""
    if local_images:
        lock_images_lines = "lock_images:\n" + "".join(f"  - {img}\n" for img in local_images)

    if encrypt:
        password = ensure_password()
        html = render_markdown_to_html(content)
        ciphertext = encrypt_html(html, password)
        body = f'<div class="locked-content" data-ciphertext="{ciphertext}"></div>\n'
        locked_line = "locked: true\n"
    else:
        body = content
        locked_line = ""

    front_matter = f"""---
layout: post
title: {title}
category: "{category}"
date: {today}
{locked_line}{lock_images_lines}---
"""

    out_path = Path(POSTS_DIR) / f"{today}-{basename}.md"
    out_path.write_text(front_matter + "\n" + body, encoding="utf-8")
    print(f"✅ 已生成: {out_path}")

    if encrypt:
        print("🔒 文章已加密。请确保源文件不提交到仓库。")


def print_menu() -> str:
    status = "已设置" if password_is_set() else "未设置"
    print("\n=== Jekyll 文档上传工具 ===")
    print(f"加密密码状态：{status}\n")
    print("请选择操作：")
    print("1. 上传文档")
    print("2. 重新上传文档（删除旧文章及关联图片）")
    print("3. 设置/修改加密密码")
    print("4. 退出")
    return input("请选择 [1-4]: ").strip()


def main():
    while True:
        choice = print_menu()
        if choice == "4":
            print("再见。")
            break
        elif choice == "3":
            set_password()
        elif choice in ("1", "2"):
            src_path = select_markdown_file()
            if not src_path:
                continue
            category = input("请输入分类（默认 Other）: ").strip() or "Other"
            encrypt_input = input("是否加密该文章？[y/N]: ").strip().lower()
            encrypt = encrypt_input in ("y", "yes")
            reupload = choice == "2"
            upload_post(src_path, category, encrypt, reupload)
        else:
            print("❌ 无效选项，请重新选择。")


if __name__ == "__main__":
    main()
