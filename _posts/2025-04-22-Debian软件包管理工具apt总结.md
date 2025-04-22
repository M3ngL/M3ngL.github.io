---
layout: post
title: Debian软件包管理工具apt总结
category: "Defalut"
date: 2025-04-22
---


 APT适用于基于Debian的Linux发行版，一般是Ubuntu

## apt使用

apt在使用时会根据以下文件中写的软件源地址进行操作

- `/etc/apt/sources.list`
- `/etc/apt/sources.list.d/*.list`

apt和apt-get的区别：简单来说，apt比apt-get更新，其功能在终端使用时更方便，运行过程展示细节更多

dpkg（底层工具）-> apt-get（上层工具）-> apt（apt-get的再封装）

### update / install

更新所有可用软件包列表（从 `/etc/apt/sources.list`以及`source.list.d/`文件夹中的软件源中下载）

````bash
sudo apt update
````

 根据可用软件包列表更新已安装的软件包（不删除任何已安装的软件包）

````bash
sudo apt upgrade    
````

升级后会根据新包的依赖关系，将不需要的依赖包删掉

````bash
sudo apt dist-upgrade
````

通过卸载 + 安装 + 升级来更新软件包，即升级前会先删除需要更新软件包

````bash
sudo apt full-upgrade
````

### remove / clean

卸载软件包

````bash
sudo apt remove <package>
````

卸载软件包, 并删除所有配置和数据文件

````bash
sudo apt purge <package>
````

卸载所有为满足依赖而自动安装但现在已不再需要被依赖的软件包

````bash
sudo apt autoremove
````

删除已下载 / 已安装的软件包的本地缓存

````bash
sudo apt clean
````

只保留软件包最新版的本地缓存，清理掉旧版本缓存

````bash
sudo apt autoclean
````

### list / search

查询满足列出条件（参数）的软件包

````bash
sudo apt list <package>				 # 根据软件包名匹配，匹配规则glob					
<<Params
	--installed						# 列出所有已安装的软件包
	--upgradable					# 列出所有可更新的软件包
	-a, --all-versions				# 列出所有可用版本
Params
````

主要根据软件包名称查询软件包，匹配规则为regex

````bash
sudo apt search <package>
````

在通过软件名匹配上，二者的区别在于匹配规则

* Glob：是 shell（如 Bash）用的简化的模式匹配规则，一般用于匹配文件名、路径。
* Regex（正则表达式）：更复杂的文本模式匹配规则

## apt与dpkg

二者的区别联系

* apt 基于dpkg，侧重于远程包的下载和依赖管理，相当于 dpkg 的前端
* dpkg 侧重于本地软件的管理

dpkg命令可以执行指定本地软件包的安装，但不会自动获取以及下载安装该软件包的依赖包

````bash
dpkg -i package.deb
````

在dpkg命令的其他参数作用中，也有类似于apt的功能

````bash
dpkg --list <package>	# 查看指定包的版本，架构和描述信息
dpkg -L <package>		# 查看包的安装路径
dpkg --status <package>	# 查看包的详细信息
dpkg --search <file_path>	# 查看某个文件由哪个包产生
````

安装结束后，一般存放在

* `/bin`： 存放二进制可执行文件，这些文件通常是系统启动和恢复时所需要的。
* `/sbin`： 与/bin相似，但这里存放的是只有管理员才能使用的系统管理程序。
* `/lib`： 存放着与系统启动相关的文件。
* `/usr`： 包含了许多子目录，比如
  * `/usr/bin` 存放的是用户可执行文件
  * `/usr/sbin` 存放的是超级用户可执行的系统管理程序
  * `/usr/lib` 存放的是和程序的运行相关的文件。
* `/etc`： 存放系统管理所需要的配置文件和子目录。

## 更换apt软件源

换源的本质即是，针对`source.list`文件进行修改，将默认软件源地址更换，以达到在使用apt下载远程软件包时，从指定的源地址进行下载安装deb软件包

* 使用sed命令快速换源

````bash
cp /etc/apt/sources.list /etc/apt/sources.list.backup
sudo sed -e 's|^deb http://archive.ubuntu.com/ubuntu | deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ |g' \
         -e 's|^deb-src http://archive.ubuntu.com/ubuntu | deb-src https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ |g' \
         /etc/apt/sources.list.backup | sudo tee /etc/apt/sources.list > /dev/null
````

* 恢复默认软件源

````bash
sudo apt install software-properties-gtk
sudo software-properties-gtk
````

### .list内容格式

`/etc/apt/sources.list` 和 `/etc/apt/sources.list.d/*.list` 均是以下格式：

````bash
deb/deb-src URI codename component1 component2...
# deb http://archive.ubuntu.com/ubuntu jammy main universe restricted multiverse
# deb-src http://archive.ubuntu.com/ubuntu jammy main universe restricted multiverse
# deb http://archive.ubuntu.com/ubuntu jammy-security main universe restricted multiverse
# deb-src http://archive.ubuntu.com/ubuntu jammy-security main universe restricted multiverse
````

* `deb/deb-src`，实际使用中二选一
  * `deb`，代表软件包安装的二进制可执行文件
  * `deb-src`，代表软件包的源码
* `URI`，软件源地址（可以是网络地址，也可以是本地的镜像地址）
* `codename`，是ubuntu不同版本的代号，比如jammy、focal等，在代号后会通过`-`连接一些参数
  * `security`: 重要的安全更新
  * `updates`: 建议的更新
  * `proposed` : 预发布的更新
  * `backports` : 不支持的更新（没有维护且有潜在问题）
* `components`，主要区分软件的自由度，参数如下
  * `main`: 包是免费的/开源的，并受 ubuntu 官方的支持
  * `restricted`: 限制开源授权但常用的软件，比如设备的专用驱动程序
  * `universe`: 包是免费的/开源的，由社区支持
  * `multiverse`：由于法律/版权问题，这些软件包受到限制

一般情况下，`components` 4个参数选项以及`codename`中后连接的各个参数都会选择，代表启用了所有类型的软件源，相当于会从软件源地址中展示的四个文件夹中去寻找软件包

除此以外，`.list`文件里的配置按行顺序解析，因此有潜在问题的软件源链接一般放在最后，如 `jammy-backports`

http://archive.ubuntu.com/ubuntu/dists/jammy-backports/

![image-20250422170736680](/pic/image-20250422170736680.png)

>  查看ubuntu版本代号
>
> ````bash
> lsb_release -cs
> ````

### deb文件

deb文件，即Debian包。是Unixar的标准归档，将包文件信息以及包内容，经过gzip和tar打包而成

deb文件包含三部分

* 数据包，包含实际安装的程序数据，文件名为 data.tar.XXX
* 安装信息及控制脚本包，包含 deb 的安装说明，标识，脚本等，文件名为 control.tar.gz
* deb 文件的二进制数据，包括文件头等信息

deb包在Linux操作系统中类似于Windows中的软件包（msi）

处理这些包的经典程序是dpkg，经常是通过Debian的apt来运作

## 添加第三方软件源

添加第三方软件源和换源不同，换源是在默认的`source.list`中更换，第三方软件源添加是在 `sources.list.d/` 文件夹中添加新的文件

那么为什么有第三方软件源的存在？为什么不能直接写入`source.list`？

* 为了模块化设计
* 独立管理第三方源，删除修改软件源更方便，且不会污染系统默认源（将官方源和第三方源分的清楚）

如果第三方软件源直接写入`source.list`，会有什么影响？需要密钥吗？

* 不会有任何影响
* 但不导入第三方源对应的公钥的话，会拒绝使用该源安装软件包，报错如下

````
The following signatures couldn't be verified because the public key is not available: NO_PUBKEY XXXXXXXXXXXXXXXX
````

---

将第三方软件源地址按照格式写入一个新文件，并放入`/etc/apt/sources.list.d/` 文件夹内，文件名可以随意，但后缀固定为`.list`

````bash
echo "deb http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list
````

`tee` 命令读取标准输入的数据，并将其内容输出成文件。由于这里要操作的文件位于`/etc/apt/`下，需要`sudo`或者`su`，不能直接使用重定向

---

添加第三方软件源后，还要添加公钥（GPG 公钥），来证明从该软件源下载的包可信，包括

* 软件包是否被人篡改过
* 软件源是不是伪造的

若不添加key，则会报错，apt将拒绝安装来自第三方软件源的软件包

但当ubuntu22使用apt-key时，该软件会有警告

````bash
W: http://packages.osrfoundation.org/gazebo/ubuntu-stable/dists/jammy/InRelease: Key is stored in legacy trusted.gpg keyring (/etc/apt/trusted.gpg), see the DEPRECATION section in apt-key(8) for details.
````

这是因为apt-key该软件的现有功能逻辑被认为是有风险的，有更安全的方式采用，已有的替代机制 `signed-by`

### apt-key

apt-key 命令用于管理 GPG 公钥，验证来自软件包存储库的包是否合法并且未被篡改。

常用命令

* 从文件中添加密钥到系统的信任密钥库中

````bash
sudo apt-key add <file>
````

* 更新过期的密钥

````bash
sudo apt-key update		# 从APT官方密钥服务器更新密钥
sudo apt-key net-update	# 从APT源列表中的密钥服务器上更新过期的密钥
````

* 常用组合 wget + apt-key

````bash
wget https://packages.osrfoundation.org/gazebo.key -O - | sudo apt-key add -
````

即wget从url下载密钥文件，输出到输出流中，再由apt-key添加当前输出流的数据（即密钥文件）到系统的信任密钥库中。

> 短横线 `-` 代表输出流

### apt-key的替代方法

原来的 `apt-key add` 命令会直接将下载的密钥文件以追加的方式写到 `/etc/apt/trusted.gpg` 文件中，存在风险：

* 将所有密钥放在同一个文件中容易遭受篡改风险，尤其是在多密钥管理的情况下

因此有了替代方案，将每个密钥作为单独的文件保存到统一的目录下或者任一目录，如

* 统一存储到 `/etc/apt/trusted.gpg.d/` 或者 `/etc/apt/keyrings/`

````bash
wget https://packages.osrfoundation.org/gazebo.key -O - | sudo tee /etc/apt/trusted.gpg.d/gazebo.key
````

> 自 APT 2.4 版本起，APT推荐将密钥存储到 `/etc/apt/keyrings/` 目录

* 也可以存放在任一目录后，在`sources.list`中确定密钥文件与特定软件源的关联关系（即 `signed-by` 机制）

````bash
# /etc/apt/sources.list
deb [signed-by=/etc/apt/keyrings/myrepo.asc] https://myrepo.example/ubuntu/ focal main
````

条件：`sources.list` 支持使用`signed-by`选项，等价于APT版本高于2.4

该机制的作用，将单个密钥仅与特定软件源相关联，减少了密钥泄漏和滥用的风险

### GPG密钥

GPG 密钥用于保护消息的隐私和完整性，例如加密电子邮件和文件签名

apt-key使用的文件后缀建议标准（可以用任意后缀名，但本质上必须是GPG密钥文件）

* 对于 ASCII 格式的密钥，文件扩展名应使用 `.asc`
* 对于二进制 OpenPGP 格式的密钥，则应使用 `.gpg`

> 如果APT 版本是 1.4 或更高版本，推荐使用 `.asc` 格式。

##  $Reference$​ 

https://www.debian.org/doc/manuals/debian-faq/pkgtools.zh-cn.html

https://blog.csdn.net/xietansheng/article/details/117204343

https://blog.csdn.net/m0_47696151/article/details/119703623

https://bashcommandnotfound.cn/article/linux-apt-key-command

https://blog.csdn.net/Stromboli/article/details/145270765