---
layout: post
title: ArduPilot loads ML model in Json
category: "ArduPilot"
date: 2025-09-11
---


本文主要讲解如何在对ArduPilot**进行交叉编译过程**中加载json格式的机器学习模型

> 当编译的目标是SITL固件时，所使用的编译链是本地系统的编译链，标准库完整并能识别本地的环境变量，包含第三方库不需要单独再指定路径等等，因此基本不会有问题，这里不再赘述

## ArduinoJson

**项目地址**

https://github.com/bblanchon/ArduinoJson

**使用方法**

实际只需要使用到 `ArduinoJson.h`，将其导入 ArduPilot library 中或者在`./waf configure`配置命令中加入包含第三方头文件的路径， 具体方法见 https://m3ngl.github.io/ardupilot/2025/09/06/ArduPilot-Waf%E4%BA%A4%E5%8F%89%E7%BC%96%E8%AF%91%E7%AC%AC%E4%B8%89%E6%96%B9%E5%BA%93/

然后在使用文件中加入 `#include "ArduinoJson.h"` 即可

**编译问题解决**

由于该库依赖于交叉编译工具链不支持的某些C++标准库函数，比如交叉编译对象是`fmuv3`是，所使用的交叉编译工具链 `arm-none-eabi-g++`对`std::to_string`，`std::vsnprintf`等标准库函数不支持

在包含之前禁用这些依赖即可解决问题，因为这些并不是核心函数内部的有效逻辑 https://arduinojson.org/v5/api/config/enable_std_string/

````bash
#define ARDUINOJSON_USE_DOUBLE 0
#define ARDUINOJSON_ENABLE_STD_STRING 0
#define ARDUINOJSON_ENABLE_STD_STREAM 0
#include "ArduinoJson.h"
````

初始化相关json类，ArduinoJson新版本目前使用 `JsonDocument` 而不是 `DynamicJsonDocument`

除此以外，为了避免使用文件I/O，我们先将json格式文件保存的模型以**硬编码+字符串**的方式写入cpp代码中，如

````cpp
const char* json_str = R"(
[
    {
        "is_leaf": 0,
        "feature": 101,
        "threshold": 14.156660556793213,
        "left": 1,
        "right": 72
    },
    ...
]
)";
````

这样方便模型在ardupilot中的初始化

````cpp
DeserializationError error = deserializeJson(_doc, json_str_three);
````

## nlohmann/json

**项目地址**

https://github.com/nlohmann/json

**使用方法**

下载项目地址中的`releases`版本，将`json.hpp`导入本地系统/同一文件夹即可

**解决编译问题**

对`nlohmann/json`进行交叉编译，由于该库使用到了标准库默认的数学函数，因此首先需要恢复标准库定义的数学函数，而不是ArduPilot自己定义的数学函数

1. **取消冲突的数学函数宏定义**

````cpp
// 临时取消冲突的数学宏定义
#pragma push_macro("abs")
#pragma push_macro("acos")
#pragma push_macro("asin")
#pragma push_macro("atan")
#pragma push_macro("atan2")
#pragma push_macro("cos")
#pragma push_macro("cosh")
#pragma push_macro("exp")
#pragma push_macro("log")
#pragma push_macro("log10")
#pragma push_macro("pow")
#pragma push_macro("sin")
#pragma push_macro("sinh")
#pragma push_macro("sqrt")
#pragma push_macro("tan")
#pragma push_macro("tanh")
#undef abs
#undef acos
#undef asin
#undef atan
#undef atan2
#undef cos
#undef cosh
#undef exp
#undef log
#undef log10
#undef pow
#undef sin
#undef sinh
#undef sqrt
#undef tan
#undef tanh

#include "json.hpp"
using json = nlohmann::json;

// 恢复ArduPilot的相关宏定义
#pragma pop_macro("abs")
#pragma pop_macro("acos")
#pragma pop_macro("asin")
#pragma pop_macro("atan")
#pragma pop_macro("atan2")
#pragma pop_macro("cos")
#pragma pop_macro("cosh")
#pragma pop_macro("exp")
#pragma pop_macro("log")
#pragma pop_macro("log10")
#pragma pop_macro("pow")
#pragma pop_macro("sin")
#pragma pop_macro("sinh")
#pragma pop_macro("sqrt")
#pragma pop_macro("tan")
#pragma pop_macro("tanh")
````

2. **交叉编译链所支持的标准库不完整**

这一点导致某些C++标准库函数没有被定义，而`nlohmann/json`库中又存在对这些函数的调用，编译时报错

````bash
../../libraries/Attack_Detect/json.hpp:6528:10: error: 'FILE' in namespace 'std' does not name a type
 6528 |     std::FILE* m_file;
 ...
 /opt/gcc-arm-none-eabi-10-2020-q4-major/arm-none-eabi/include/wchar.h:75:16: note: 'FILE' declared here
   75 | typedef __FILE FILE;
      |    
...
../../libraries/Attack_Detect/json.hpp: In member function 'std::string nlohmann::json_abi_v3_12_0::detail::lexer<BasicJsonType, InputAdapterType>::get_token_string() const':
../../libraries/Attack_Detect/json.hpp:8489:41: error: 'snprintf' is not a member of 'std'
 8489 |                 static_cast<void>((std::snprintf)(cs.data(), cs.size(), "<U+%.4X>", static_cast<unsigned char>(c))); // NOLINT(cppcoreguidelines-pro-type-vararg,hicpp-vararg)
      |   
````

而该库不同于`ArduinoJson`，没有官方定义的宏定义来禁用对这些函数的调用，暂未解决这一报错问题

## 编译失败的常见原因

1. **C++标准不符合**

某些CPP第三方库可能是基于较旧或较新版本的C++进行开发的，而ArduPilot仅主要支持C++11标准，不支持 C++17 或更高版本，支持部分C++14特性；第三方库与ArduPilot标准不同导致的问题基本无法解决，但可以判断是否为该问题

1. 确定对应固件编译的工具链

````bash
./waf configure

# ...
# Checking for 'g++' (C++ compiler)        : /opt/gcc-arm-none-eabi-10-2020-q4-major/bin/arm-none-eabi-g++ 
# Checking for 'gcc' (C compiler)          : /opt/gcc-arm-none-eabi-10-2020-q4-major/bin/arm-none-eabi-gcc 
# ...
````

2. 确定该工具链的版本以及所支持的C++标准

````bash
arm-none-eabi-g++ -dM -E -x c++ /dev/null | grep -F __cplusplus
````

* 如果输出为 `#define __cplusplus199711L`，表示默认使用 C++98。
* 如果输出为 `#define __cplusplus201103L`，表示默认使用 C++11。
* 如果输出为 `#define __cplusplus201402L`，表示 C++14。
* 如果输出为 `#define __cplusplus 201703L`，表示 C++17。
* 更高版本如 C++20 会显示 `202002L`。
