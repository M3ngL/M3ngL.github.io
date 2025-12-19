import os
import re
from datetime import datetime
import shutil
from urllib.parse import urlparse
import requests

def updateTitle(fileName):
    with open("./tmp/img_done/" + filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    title = None
    content_lines = []

    for line in lines:
        if title is None:
            match_title = re.match(r'^#\s+(.+)', line.strip())
            if match_title:
                title = match_title.group(1).strip()
                continue  # 不保留这行标题
            
        # 匹配代码块语言为assembly，替换为nasm
        # blog使用的Rouge不支持assembly，只支持nasm
        if re.match(r'^````assembly\b', line.strip()):
            line = re.sub(r'^````assembly\b', '````nasm\n', line.strip())
        content_lines.append(line)

    if title is None:
        print(f"文件 {fileName} 中未找到一级标题，跳过")
        return

    # 构建 front-matter
    front_matter = f"""---
layout: post
title: {title}
category: "{category}"
date: {today}
---

"""
    return front_matter, content_lines
    
    
def updateImg(fileName):
    # 匹配 markdown 图片链接的正则
    img_pattern = re.compile(r'!\[([^\]]*)\]\((https?://[^\)]+)\)')
    with open("./tmp/" + fileName, "r", encoding="utf-8") as f:
        content = f.read()
    
    matches = img_pattern.findall(content)
    modified = content

    for alt_text, url in matches:
        try:
            # 从 URL 中提取文件名
            img_name = os.path.basename(urlparse(url).path)
            local_path = os.path.join(img_dir, img_name)
            # 如果图片不存在则下载
            if not os.path.exists(local_path):
                print(f"🌐 下载图片: {url}")
                response = requests.get(url)
                with open(local_path, "wb") as img_file:
                    img_file.write(response.content)

            # 替换 Markdown 中的图片链接
            new_md_img = f"![{alt_text}](/{img_dir}/{img_name})" # 注意是/开头的路径
            old_md_img = f"![{alt_text}]({url})"
            modified = modified.replace(old_md_img, new_md_img)
        except Exception as e:
            print(f"⚠️ 下载失败: {url}，原因: {e}")
            return

    # 保存修改后的文件
    with open("./tmp/img_done/" + fileName, "w", encoding="utf-8") as f:
        f.write(modified)

if __name__ == "__main__":
    # 设置当前日期作为 front-matter 的日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    category = "Other"

    img_dir = "pic"
    os.makedirs(img_dir, exist_ok=True)

    os.makedirs("tmp/img_done", exist_ok=True)
    

    # 遍历当前目录下的所有 .md 文件
    for filename in os.listdir("./tmp"):
        if filename.endswith(".md") and filename not in os.listdir("./tmp/img_done"):
            # 处理图片
            updateImg(filename)
            # 更新标题
            front_matter, content_lines = updateTitle(filename)
            
            new_filename = f"_posts/{today}-{filename}"
            # 写入新文件
            with open(new_filename, "w", encoding="utf-8") as f:
                f.write(front_matter)
                f.writelines(content_lines)

            print(f"✅ 已处理文件: {filename} -> {new_filename}")
        
        