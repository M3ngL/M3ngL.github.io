---
layout: post
title: 判断本地Git项目(ArduPilot)的版本
category: "ArduPilot仿真"
date: 2025-05-14
---


* 没有与远程github仓库连接的项目
* 仍与github远程仓库有连接的项目

本文主要是针对有（无）远程仓库连接的ardupilot本地项目寻找版本，其中某些方法也适用于其他github仓库的寻找

两个目的，

* 自己修改的ardupilot本地项目（处于开发分支上），由于工作分支上没有版本号，需要找到一个与之相近的稳定版本的版本号
* 复现前人克隆下来的ardupilot项目，该项目已经不再和ardupilot远程仓库连接，但要找到与之接近的版本

## $Introduction$

Ardupilot项目中有很多个分支，主要分为开发者分支 `master` 以及稳定版本分支（其他几乎所有分支都是稳定/发行版本）

>  通过命令查看当前ardupilot远程仓库现有的分支信息，以及该分支上最新提交的commit hash
>
> ````bash
> git ls-remote --heads https://github.com/ArduPilot/ardupilot.git
> 
> 77319bb7b28e81051131a5644b060348e416cd14        refs/heads/APMrover2-3.1.1
> 0fa522b805b97c438aa3976e8bea45598c46d4a9        refs/heads/APMrover2-release
> a732f99ec41db3a0783e195fc64ebf61fd4adbc4        refs/heads/AP_Periph-1.0
> ...
> 9ede67141bc3367ab025a74cef9b61ba023d0371        refs/heads/plane3.9
> b319b275d51de8acf4c86efc4b3337c6923a5e7e        refs/heads/plane4.0
> ````
>
> `refs/heads/` 是 Git 用来跟踪和管理分支的机制。它将每个分支的名称映射到该分支上最新的提交。

具体来看ArduPilot的各个分支

* APMrover
  * Rover 是一款先进的开源固件，专为地面和水上车辆的自动驾驶仪设计。该固件不仅支持传统的三轮或四轮配置，还扩展到船舶、帆船、平衡机器人和步行机器人。这款多功能系统能够完全自主地执行任务，这些任务可以通过任务规划软件定义，也可以由驾驶员手动预先记录。
* AP_Periph
  * ArduPilot Peripheral 的缩写，即基于现有 ArduPilot 代码的 ArduPilot 外设。它采用 ArduPilot 的外设驱动程序库，并对其进行适配，使其能够在独立的外设上运行，并通过 CAN、MSP 或其他外设总线协议与主飞控通信
* AntennaTracker（Tracker），该两个分支实际上是同一个工作流
  * AntennaTracker 项目提供固件，可将支持的飞行控制板用作天线跟踪器。该跟踪器通过自身的 GPS 数据以及来自直升机、探测车或飞机的遥测数据来确定远程车辆的位置，并利用这些信息将定向天线对准车辆。这种对准方式可以显著增强地面站的发射和接收范围。
* ArduPlane（Plane / plane），该三个分支实际上是同一个工作流
  * 针对任何固定翼飞机使其都具备完全自主飞行的能力。Plane 固件还支持以不同配置悬停和巡航的垂直起降 (VTOL) 固定翼飞机。
* Copter（ArduCopter），该两个分支实际上是同一个工作流
  * 包括多旋翼飞行器，直升机（单旋翼飞行器）
* Sub
  * 可以远程控制并有自主控制能力的水下设备
* ArduPilot
  * 似乎从`v4.6.0` 版本开始，将ArduPlane，Copter，APMrover，Sub，AntennaTracker整合到了一起，统一在`ArduPilot`分支上
* master
  * **主工作分支**，所有新加入的代码统一加入到该分支，整合后再将该分支的提交合并到稳定版本的分支中

---

各个主要稳定版本分支中，各自的版本号基本维持一致，相同版本号的不同分支，其共同部分是一致的，都基于 ArduPilot 核心代码库，如`library`文件夹中的共同的控制代码部分。除了各分支共享的核心功能，各自分支在更新时可能也针对各自平台的硬件和应用进行了不同的优化。

但在较新的版本中，同版本号的各分支之间几乎没有区别（可能是为了`v4.6.0`版本以后将各分支合并到一起）

````bash
m3@M3ngL:~/test/ardupilot$ git diff --name-only Copter-4.5.3 Plane-4.5.3
AntennaTracker/ReleaseNotes.txt
````

在`v4.5.x`版本之前，相同版本号的各分支在`library`文件夹下以及各自平台文件夹下有较大的不同

## $Solution$​​​

### 通过Ardupilot固件版本确定

以Copter为例，其他文件夹中也有 `version.h`

`./ArduCopter/version.h` 中会记录编译出的copter二进制固件版本号

````cpp
#pragma once

#ifndef FORCE_VERSION_H_INCLUDE
#error version.h should never be included directly. You probably want to include AP_Common/AP_FWVersion.h
#endif

#include "ap_version.h"

#define THISFIRMWARE "ArduCopter V3.7.0-dev"

// the following line is parsed by the autotest scripts
#define FIRMWARE_VERSION 3,7,0,FIRMWARE_VERSION_TYPE_DEV

#define FW_MAJOR 3
#define FW_MINOR 7
#define FW_PATCH 0
#define FW_TYPE FIRMWARE_VERSION_TYPE_DEV
````

版本号后有`-dev`表示当前版本是开发者版本而非稳定版本`stable`或者发行版本`release`，因此原来处于`master`分支上

这里写的固件版本和ardupilot远程仓库的版本号有对应关系，该项目版本是`ArduCopter V3.7.0-dev`，虽然在ardupilot项目中不会有这个版本号选项（因为这是开发过程版本），但可以寻找邻近的稳定版本进行克隆

比如这里可以选择邻近的稳定版本 `Copter-3.6`切换到该分支上

> 如果tag和branch的名称一致，当使用git checkout 等命令切换版本/分支时，会采用git的引用解析顺序来解析命令参数
>
> 1. 本地分支: Git 首先会尝试将 `<name>` 解析为你的本地分支。如果存在一个名为 `<name>` 的本地分支，`git checkout <name>` 将会切换到该分支。
> 2. 标签 (Tag): 如果 Git 没有找到名为 `<name>` 的本地分支，它会尝试将其解析为一个标签。如果存在一个名为 `<name>` 的标签，`git checkout <name>` 将会使你的仓库处于一个**分离 HEAD (detached HEAD)** 的状态，指向该标签所标记的 commit。
> 3. 远程跟踪分支: 如果 Git 既没有找到本地分支也没有找到标签，它会尝试将其解析为一个远程跟踪分支（例如 `origin/<name>`）。如果找到匹配的远程跟踪分支，`git checkout <name>` 通常会创建一个新的本地分支 `<name>` 并切换到它，同时将其设置为跟踪该远程分支。
>
> 可以显式地按照标签名切换，
>
> ````bash
> git checkout tags/<tag_name>
> ````

### 通过git信息确定

#### Github网址寻找

通过github网址查询，寻找离当前提交最近的版本

````url
https://github.com/<Name>/<Depository—Name>/commit/<short_hash>
````

`short_hash`值也可以是完整的hash值

如 https://github.com/ArduPilot/ardupilot/commit/4352129c4d66

![image-20250514153957951](/pic/image-20250514153957951.png)

其中可以在页面中间找到与之相关的版本 tag

#### Git命令寻找

寻找离当前`commit hash`值最近的tag，该命令可以识别当前代码基于哪个发布版本

````bash
git describe --tags <commit_hash>
````

该命令只显示搜索到的第一个tag，可能是指向当前commit的tag，也可能是离得最近的tag

````bash
m3@M3ngL:~/test/ardupilot$ git describe --tags 2a3dc4b7bf
ArduCopter-stable
````

---

通过commit的hash值寻找`git tag`，如果该commit有对应的tag，则会显示出来；若该commit没有对应的tag，则不会显示

````bash
git tag -l --points-at <commit_hash>
````

如下所示，该提交总共有3个tag指向

````bash
m3@M3ngL:~/test/ardupilot$ git tag -l --points-at 2a3dc4b7bf
ArduCopter-stable
ArduCopter-stable-heli
Copter-4.5.7
````

Tag 和 Commit Hash 之间的对应关系，

- Tag 是一个指向特定 Commit 的引用。创建一个tag实际上是在为某个特定的 commit 起一个别名（版本号）
- 一个 Tag 只能指向一个特定的 Commit
- 一个 Commit 可以被多个 Tag 指向

在 Git 的工作分支（这里是`master`分支）上，一般不会有tag与之对应

> 查看远程仓库中的所有tag
>
> ````bash
> git ls-remote --tags https://github.com/ArduPilot/ardupilot.git
> ````

## $Reference$

https://ardupilot.org/

https://discuss.ardupilot.org/t/copter-4-5-7-released/125007

https://discuss.ardupilot.org/t/rover-4-5-7-has-been-released/125008
