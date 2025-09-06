---
layout: post
title: ArduPilot Waf 交叉编译第三方库
category: "ArduPilot"
date: 2025-09-06
---


环境 + 版本

* `WSL2 Ubuntu 20.04.6 LTS`
* `Ardupilot v4.6.0-dev`
* 交叉编译链 `arm-none-eabi-g++ (GNU Arm Embedded Toolchain 10-2020-q4-major) 10.2.1 20201103 (release)`

Target：在Ardupilot中搭载Json格式的决策树模型，且**使用第三方库来解析以Json格式字符串存储的模型**，并交叉编译为 Pixhawk 2.4.8 适用的固件

> 本文在编译过程中尝试调用第三方库解析json文件时，交叉编译链`arm-none-eabi-g++`并不支持文件读取等相关函数，因此通过宏定义的方式禁用了一部分第三方库的功能，并使用硬编码的方式在ardupilot中存储json格式模型

## Background

Waf 是使用 Python 脚本`wscript`定义构建流程。

运行 Waf 命令，`./waf configure build`，会调用 `wscript` 中的函数，其核心函数包括：

- `options(ctx)`：定义命令行选项。
- `configure(ctx)`：检查编译环境、设置编译器、库路径等。
- `build(ctx)`：定义编译目标和规则。

在Ardupilot中，当调用Waf进行固件`--board`编译时，实际调用的是对应硬件相关的交叉编译链，可以通过命令回显查看到具体的编译工具链

````bash
$ ./waf configure --board fmuv3
...
Checking for 'g++' (C++ compiler)        : /opt/gcc-arm-none-eabi-10-2020-q4-major/bin/arm-none-eabi-g++ 
Checking for 'gcc' (C compiler)          : /opt/gcc-arm-none-eabi-10-2020-q4-major/bin/arm-none-eabi-gcc 
...
````

因此，若需要编译链接第三方库时，应该将相关的库文件路径也给到工具链，或者将第三方库核心头文件导入Ardupilot项目文件夹中

> 当Ardupilot/waf编译SITL时，调用的是本地系统的编译工具链g++，ta能够自动根据环境变量，找到本地系统安装好的第三方库文件，因此和交叉编译时不同

## Method

### 修改Waf编译配置脚本

虽然Ardupilot/waf给了 `--libdir` 的参数指令，但**该指令在交叉编译时似乎无效**

````bash
  Linux boards configure options:
    --prefix=PREFIX     installation prefix [default: '/usr/']
    --destdir=DESTDIR   installation root [default: '']
    --bindir=BINDIR     bindir
    --libdir=LIBDIR     libdir
````

**实际有效的方式**是在`./waf configure`后加上`CXXFLAGS=""`

````bash
./waf configure --board=xxx CXXFLAGS="-I/usr/local/include"
````

> 我这里因为只涉及到头文件的包含，并不需要指定共享库等等，但可以通过相同的方法将编译命令输入

还有更为麻烦的方式，由于 ardupilot/waf 在 configure 后**会生成对应固件的编译配置python脚本**，如使用

````bash
./waf configure --board=fmuv3
````

在项目根目录下会生成 `./build/c4che/fmuv3_cache.py`，该文件中写明在进行编译时，会传入的各种编译命令，如

> 所有固件的配置命令`./waf configure --board=XXX`执行后，均会生成对应的python编译配置脚本 `XXX_cache.py`，包括SITL

````python
...
CFLAGS = ['-ffunction-sections', ...]
CFLAGS_MACBUNDLE = ['-fPIC']
...
COMPILER_CC = 'gcc'
COMPILER_CXX = 'g++'
...
CXX = ['/opt/gcc-arm-none-eabi-10-2020-q4-major/bin/arm-none-eabi-g++']
CXXFLAGS = ['-Werror=implicit-fallthrough', ...]
CXXFLAGS_MACBUNDLE = ['-fPIC']
...
````

可以在这里在相应字段中加入自定义参数，如更换编译链，将 `CXX` 字段改为 `your_complier`

并且可以通过该文件的字段观察，确定在`./waf configure`后可以传入什么样的参数，比如这里，我们可以在终端命令中达到相同的效果

 ````
 ./waf configure --board=fmuv3 CXX=your_complier
 ````

### 修改交叉编译链的Include路径

通过`./waf configure`的相关回显可以确定编译链的选定，进一步找到编译链的include路径

````bash
arm-none-eabi-g++ -v -E -x c++ /dev/null 2>&1 | grep "include"
````

该命令是指定编译器使用C++语言，对空输入文件`/dev/null`进行预处理编译，并详细输出过程，这一过程中会显示编译器的搜索路径

之后的 `2>&1 | grep "include"`是为了获取到这一输出并从中寻找相关字段，最终确定编译链的include路径

在include路径中，复制第三方库即可

### 修改Ardupilot library

将第三方库文件调用到的相关核心函数文件，复制进入自定义Ardupilot中需要调用到的cpp同一文件夹下

并在文件中指定 `#include "thrid_party.h"`即可

## Reference

https://blog.csdn.net/lida2003/article/details/135167962
