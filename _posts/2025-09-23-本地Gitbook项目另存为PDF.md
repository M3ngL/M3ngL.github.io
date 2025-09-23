---
layout: post
title: 本地Gitbook项目另存为PDF
category: "Other"
date: 2025-09-23
---


环境：WSL2 Ubuntu 20.04.6 LTS / Windows11

在本地通过工具 `Gitbook-cli` 或 `mdbook` 将以顺序（章节）排序的多个markdown文件，衔接转换成html book的形式，并进一步转换为pdf book。

> [gitbook官方](https://www.gitbook.com/)现在推荐在线上编辑并导出gitbook项目，其中网页专业版，似乎能直接在网页界面导出为pdf。但如果不是专业版，网页上就没有专门的导出为pdf的操作，也因此才有本文尝试在本地导出gitbook为pdf

## Gitbook-CLI

> Gitbook-cli目前停止维护了，导致该工具支持的插件与语法都是旧版本的，需要下载旧版本的依赖才可以运行
>
> 因此不建议使用该程序，尤其是Windows11，因为`nvm`似乎对windows的支持性不好，导致`npm`版本无法方便地切换

以下过程是使用 WSL2 Ubuntu 20.04.6 LTS 完成

### Install

下载Gitbook终端命令

````bash
npm install -g gitbook-cli
````

下载完成后，调用其命令，使其自动下载其他依赖程序

````bash
gitbook --verison
````

等待该命令自动下载`gitbook`

下载过程中会报错

````powershell
$ gitbook -V
CLI version: 2.3.2
Installing GitBook 3.2.3
/home/m3/.nvm/versions/node/v14.21.3/lib/node_modules/gitbook-cli/node_modules/npm/node_modules/graceful-fs/polyfills.js:287
      if (cb) cb.apply(this, arguments)
                 ^

TypeError: cb.apply is not a function
    at /home/m3/.nvm/versions/node/v14.21.3/lib/node_modules/gitbook-cli/node_modules/npm/node_modules/graceful-fs/polyfills.js:287:18
    at FSReqCallback.oncomplete (fs.js:193:5)
````

原因是目前默认下载的 `node.js` **过新，不支持以前的语法**，可以通过 `nvm` 管理`node.js`的版本，**安装旧版本**的 `Node.js`。

安装 `node.js` 的版本管理器`nvm`：

````bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
````

> `nvm` 是 `node.js` 的版本管理器，设计为按用户安装，并按外壳调用。nvm可以在任何符合POSIX的shell（sh、dash、ksh、zsh、bash）上运行，尤其是在以下平台上：unix、macOS和windows WSL。

安装`node.js`的指定旧版本，`node.js`和`npm`二者是捆绑下载的

````bash
nvm install v10.24.1
nvm use v10.24.1
````

> 其中 `v12.22.12` 旧版本依然不足以支持 `gitbook`的语法，需要更旧。

继续安装 `calibre`，以支持 ebook-convert，这是因为 GitBook CLI 依赖于 Calibre 来生成 PDF。


````
sudo apt install calibre
````

否则会报错：

````bash
m3@M3ngL:~/test/test-for-gitbook/xv6-chinese$ gitbook pdf . book.pdf
info: 7 plugins are installed
info: 6 explicitly listed
info: loading plugin "highlight"... OK
info: loading plugin "search"... OK
info: loading plugin "lunr"... OK
info: loading plugin "sharing"... OK
info: loading plugin "fontsettings"... OK
info: loading plugin "theme-default"... OK
info: found 14 pages
info: found 19 asset files

InstallRequiredError: "ebook-convert" is not installed.
Install it from Calibre: https://calibre-ebook.com
````

而如果曾经在python3-pip中下载过 `lxml`，很可能造成 `calibre` 的依赖冲突，报错：

````bash
EbookError: Error during ebook generation: Conversion options changed from defaults:
 ....................
1% Converting input to HTML...
InputFormatPlugin: HTML Input running
on /tmp/tmp-11092VbAn55ECRFpP/SUMMARY.html
Traceback (most recent call last):
  File "/usr/bin/ebook-convert", line 21, in <module>
    sys.exit(main())
  File "/usr/lib/calibre/calibre/ebooks/conversion/cli.py", line 419, in main
    plumber.run()
  File "/usr/lib/calibre/calibre/ebooks/conversion/plumber.py", line 1108, in run
    self.oeb = self.input_plugin(stream, self.opts,
  File "/usr/lib/calibre/calibre/customize/conversion.py", line 242, in __call__
    ret = self.convert(stream, options, file_ext,
  File "/usr/lib/calibre/calibre/ebooks/conversion/plugins/html_input.py", line 83, in convert
    from calibre.ebooks.metadata.html import get_metadata
  File "/usr/lib/calibre/calibre/ebooks/metadata/html.py", line 14, in <module>
    from html5_parser import parse
  File "/usr/lib/python3/dist-packages/html5_parser/__init__.py", line 31, in <module>
    raise RuntimeError(
RuntimeError: html5-parser and lxml are using different versions of libxml2. This happens commonly when using pip installed versions of lxml. Use pip install --no-binary lxml lxml instead. libxml2 versions: html5-parser: (2, 9, 13) != lxml: (2, 12, 9)
````

删去原来 `python-pip` 中下载的 `lxml` 即可

````bash
pip3 uninstall lxml
````

至此，`gitbook-cli`的安装过程彻底完成

### Application

切换到目标gitbook本地项目文件夹中，调用命令即可转换成PDF

````bash
gitbook pdf . book.pdf
````

这里的 `.` 指示当前目录作为输入，`book.pdf` 是输出文件名。GitBook CLI 会读取项目根目录中的 `SUMMARY.md` 来确定文件顺序并生成 PDF。

更多的使用方式见， https://tonydeng.github.io/gitbook-zh/gitbook-howtouse/

## mdbook CLI

> 使用 Rust 开发的gitbook本地管理工具，下载安装起来更加方便

以下过程是使用 Windows11完成，但WSL2 ubuntu应该也能完成

### Install

Rust语言包下载 https://www.rust-lang.org/tools/install

WSL2 安装 Rust

````bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
````

验证Rust是否成功安装：

````powershell
> rustup toolchain list
stable-x86_64-pc-windows-msvc (active, default)
````

mdbook中文指南 https://mdbook-guide.irust.net/zh-cn/guide/installation.html

> mdBook 当前至少需要 Rust 1.46，默认安装的Rust为最新版本，远超 `v1.46`

下载 mdbook：

````bash
cargo install mdbook
````

下载转换PDF依赖的插件：

````bash
cargo install mdbook-pdf
````

### Application

本地初始化

````bash
mdbook init
````

![image-20250923171322198](/pic/image-20250923171322198.png)

这将会自动生成`book.toml`，`src/chapter_1.md, src/SUMMARY.md`以及空文件夹 `book/`

````cmd
C:\Users\24287\Desktop\gitbook-test>tree /f
卷 Windows-SSD 的文件夹 PATH 列表
卷序列号为 749A-BA1A
C:.
│  book.toml
│
├─book
└─src
        chapter_1.md
        SUMMARY.md
````

生成的 `book.toml` 内容为

````toml
[book]
authors = ["M3nglin"]
language = "en"
src = "src"
title = "123"
````

增加内容 `[output.pdf]` 以及 `[output.html]`并修改，使其为

> 字符串`output.pdf` 不能更改，更改后无法成功生成PDF
>
> `[output.pdf]`的可选参数 https://github.com/HollowMan6/mdbook-pdf/blob/main/README_CN.md

````toml
[book]
authors = ["M3nglin"]
language = "ch"
src = "./"
title = "Your-title"

[output.html]

[output.pdf]
````

其中`src`字段后是定位`SUMMARY.md`所在的目录路径且要求`content`文件夹在 `SUMMARY.md` 的所在目录的子目录中

而一般的gitbook项目结构默认满足以上结构，

````cmd
C:.
│  SUMMARY.md
│  ...
└─content
        chapter0.md
        chapter1.md
        chapter2.md
        chapter3.md
        chapter4.md
        chapter5.md
        chapter6.md
        cover.md
````

因此 `src = "./"`，其余字段均是生成html 或者 PDF文件中页眉页脚的指定内容。

开始构建：

````bash
mdbook build
````

这将构建**Html网页版本的gitbook + PDF gitbook**，生成的结果将保存在 `book/` 文件夹中，为 `book/pdf/` 以及 `book/html/`

另外，也可以只生成部分章节，修改 `SUMMARY.md` 即可

## Reference

https://tonydeng.github.io/gitbook-zh/gitbook-howtouse/

https://mdbook-guide.irust.net/zh-cn/guide/installation.html

https://www.aye10032.com/2023/09/12/2023-09-12-mdbook/

https://github.com/HollowMan6/mdbook-pdf/blob/main/README_CN.md