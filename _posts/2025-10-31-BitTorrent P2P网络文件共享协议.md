---
layout: post
title: BitTorrent P2P网络文件共享协议
category: "Other"
date: 2025-10-31
---


本文针对 BitTorrent 协议的相关内容做概述，包括种子文件、BitTorrent 具体的通信协议以及磁力链接；社区版本BitTorrent 协议应用的Private Tracker (PT)

## BitTorrent 协议

BitTorrent 协议是架构于 TCP/IP 协议之上的一个 P2P 文件传输协议

**协议流程**

* **制作种子文件**：BitTorrent 协议要求，将源文件虚拟化分成大小相等的块（由于是虚拟分块，硬盘上并不产生各个块文件），并把每个块的索引信息和 Hash 值写入 `.torrent` 文件（即种子文件）中，作为被下载文件的“索引”

> 当要下载文件内容，需要先得到相应的 .torrent 文件，然后使用 BT 客户端下载 

* **询问Tracker服务器**：用户通过 BT 客户端解析 `.torrent` 文件得到种子文件中记录的 Tracker 服务器地址，然后请求连接 Tracker 服务器。Tracker 服务器回应请求，提供其他下载者（包括发布者）的 IP 等信息。

> BitTorrent 网络内的主机依靠互相交换自身持有的资源来完成资源共享，而 Tracker 协议会告诉用户哪些 IP 有种子文件中标注的资源

* **下载源文件**：用户通过Tracker 服务器返回的 IP 连接其他下载者，根据 `.torrent` 文件中记录的源文件块信息，用户之间告知自己已经有的块，然后交换彼此没有的数据

  > 此时不需要其他服务器参或者其他网络节点的参与

* **校验**：下载过程中，用户每下载一个块，需要算出下载块的 Hash 值与 `.torrent` 文件中的对比，如果一样则说明块正确，不一样则需要重新下载这个块
* **做种**：下载成功后，只要本地 BT 客户端进程存在，会允许其他用户通过网络协议连接到本地，下载本地的源文件

> 制作种子文件和做种 Seeding 概念不同：前者是对本地源文件使用软件/工具专门生成新的种子文件；后者是从p2p网络中下载源文件完成后，BT客户端的自动行为

从 BT 客户端角度来看**协议流程**：

1. 根据 BitTorrent 协议，文件发布者会根据要发布的文件生成提供一个 `.torrent` 文件。用户从各种途径得到种子文件，并从中得到 Tracker 服务器 URL 或 DHT 网络 nodes 等信息。
2. 根据 Tracker URL 与 Tracker 服务器建立连接，并从服务器上得到 Peers 信息。或者根据 nodes 与 DHT 网络中节点通信，并从节点上得到 Peers 信息。
3. 根据 Peers 信息与多个 Peer 建立连接，依据 Peer wire 协议完成握手，并从 Peer 端下载数据文件。同时监听 Peer 的连接，并给 Peer 上传数据文件。

> nodes 指在 DHT 网络中参与的其他 BitTorrent 客户端用户

### 制作种子文件

种子文件主要内容，`.torrent` 文件编码方式 `Bencode` 编码，因此无法通过 utf-8 编码的记事本方式看到明文文本

1. 各个文件虚拟块的哈希值：对文件虚拟分块分别进行哈希计算得到的各个块的 hash 值，用于验证文件以及文件块
2. 文件名及目录结构信息：用于下载完成后显示下载的文件名及目录结构。
3. Tracker URL地址：用于连接到Tracker服务器，获取其他用户的IP地址和端口号，以进行P2P文件下载。
4. 文件大小

制作种子文件需要通过 BitTorrent 客户端，指定本地源文件，并向种子文件中写入指定的 Tracker 服务器

![image-20251030214622309](/pic/image-20251031205528031.png)

种子制作成功后，在本地 BitTorrent 客户端加载该种子后，客户端将向种子文件中提到的 Tracker 服务器发送 Announce，表明本地的 IP 信息等等

> Tracker 服务器也可以在本地服务器 / 远程服务器搭建，不一定需要知名度高的服务器

### Tracker 协议

从协议流程中可以看到，bittorrent 协议通信方式有多种，包括 DHT 网络、Peer wire 协议等等

完整的BitTorrent 协议簇解析 [BitTorrent 协议簇概述 – 寂静花园](https://www.addesp.com/archives/5236)

* Tracker 协议，指用户连接 Tracker 服务器的通信协议规定
  [BitTorrent Tracker 协议详解 – 寂静花园](https://www.addesp.com/archives/5313)

* DHT 网络，称为分布式散列表协议，散列表是一种由键值对组成的列表，分布式散列表是一个网络内所有的节点共同维护的一种散列表，每个用户都是该网络中的 Tracker 服务器，即node，提供连接到其他用户的IP信息（路由表）以及源文件信息
  [BitTorrent 分布式散列表（DHT）协议详解 – 寂静花园](https://www.addesp.com/archives/5428)
* Peer 协议，是一个运行在 TCP 或者 UTP 协议之上的应用层协议，被用于两个 BitTorrent 客户端之间的通信，如上传和下载
  [BitTorrent 伙伴（Peer）协议详解 – 寂静花园](https://www.addesp.com/archives/5271)

除此以外，还有具体的协议格式规范 [BitTorrent协议解析 - 知乎](https://zhuanlan.zhihu.com/p/406071341)

### MagNet 磁力链接 

磁力链接必须利用 DHT 网络来下载，由于链接中没有文件的元数据信息，客户端先从有效的网络节点node中，获取元数据，再进行下载，下载过程与通过种子文件下载过程一致

**磁力链接的生成**

上传者使用种子文件中的哈希值和Tracker服务器地址等信息，生成一个磁力链接。磁力链接的格式通常为

````bash
magnet:?xt=urn:btih:<Hash_Value>&dn=<File_name>&tr=<Tracker Server IP/URL>
````

其中，`xt` 定义资源的唯一标识，`urn:btih` 表示BT种子文件的哈希值，`dn` 表示文件名，`tr` 表示Tracker服务器地址

## Private Tracker (PT)

PT在正常 BitTorrent 协议中增加了规则，保证社区内部的下载 / 上传种子环境，规则如下

1. 种子文件设定为私密，保证仅有社区内的小范围下载
2. 进行流量统计，其根据上传量决定下载

提供 PT 服务的社区网站是不公开的，网站内部用户注册采用邀请制或是不定时开放注册

用户注册后会得到一个`passkey`，用于识别各个用户，用户登录网站从中下载种子后，该种子将带有用户的 passkey

> 其他客户端使用同一个种子文件下载，也计入种子文件对应 passkey 的用户下载量中

**私有种子**

私有种子将强制禁止 DHT 网络连接下载，这代表只能通过指定的 Tracker 服务器获取下载源文件的信息

实际在种子文件中设置字段 `private: 1`

![image-20251031203824993](/pic/image-20251031203824993.png)

**常见名词**

* 上传量：主要是看你上传了多少数据
* 下载量：需要下载数据，主要是统计“分享率”而设定的中间量；
* 分享率：上传量除以下载量就是分享率，正常情况下需要分享率大于1；
* 魔力值：分享的种子数量越多，魔力值就越多，如果有较好的资源发布，有更多的魔力值；

以上指标均是网站确定用户可以有多少下载量的指标

**禁止部分BT客户端**

许多 PT 网站对部分 BT 客户端有限制，用户通过这些客户端无法从 Tracker 服务器拿到有效的下载信息

**辅种机制**

其他人抢先发布了某个资源，但本地刚好也有这个资源。那么当下载别人制作的种子之后，只要本地资源文件通过了 hash 校验就会变成做种状态。

**BT客户端官网无法访问**

本地 VPN 对应的机场将 BT 客户端官网链接屏蔽了，使用平常网络访问即可

## Reference

[BitTorrent 原理简介 - Jamin Zhang](https://jaminzhang.github.io/p2p/BitTorrent-Principle-Introduction/)

[搭建一个简单的私有 BT Tracker 服务](https://blog.waynecommand.com/post/bt-tracker-server)

[常用下载方式的区别-BT下载、磁力链接、电驴 - 潘小白？ - 博客园](https://www.cnblogs.com/pxb2018/p/10793115.html)

[揭开PT的真实面纱–PT（Private Tracker）萌新到小白的过程 | Boris的备份库房](https://boriskp.github.io/PT/)

[制作BT(BitTorrent)种子和磁力链接教程通过BT分享文件 - 博客文章 - 任霏的个人博客网站](https://blog.renfei.net/posts/1003434)

[怎么制作bt种子？ - 知乎](https://www.zhihu.com/question/62389792)

[一文理解BT种子和磁力链接原理及使用方法 - 知乎](https://zhuanlan.zhihu.com/p/624728723)

[从零开始玩PT-入门到精通 | 夜法之书](https://v20blog.17lai.site/posts/9806d7f1/)

[https://www.qbittorrent.org/ 你们能打开吗？为啥我换节点也打不开-美国VPS综合讨论-全球主机交流论坛 - Powered by Discuz!](https://hostloc.com/thread-1169134-1-1.html)
