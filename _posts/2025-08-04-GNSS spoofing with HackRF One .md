---
layout: post
title: GNSS spoofing with HackRF One
category: "Other"
date: 2025-08-04
---


环境/硬件工具：WSL2 ubuntu20.04.6 LTS + hackRF one

软件工具：Google Earth Pro + SatGen + gps-sdr-sim + hackrf

> 本文内容仅用于科研过程记录，未经许可不得用于商业用途或非法用途

GNSS spoofing可以分为静态欺骗和动态欺骗，静态欺骗可以直接使用`gps-sdr-sim`工具直接生成最后一步的卫星数据文件，意味着不再需要`Google Earth Pro + SatGen`，在安装`gps-sdr-sim`且下载星历RINEX文件后，可以直接跳转到 [1.3.1 静态欺骗](#jump0) 查看静态欺骗内容；若进行动态欺骗，则需要前两个软件工具生成路径数据。

## $Method$​

动态欺骗的过程，简单来说

1. 使用Google Path Pro生成轨迹KML文件
2. 使用SatGen导入轨迹KML文件，设置合理的轨迹运动参数后，导出为NMEA文件
3. 从在线网站上下载最新的星历RINEX文件
4. 使用`gps-sdr-sim`导入RINEX文件和NMEA文件后，生成模拟的卫星信号文件
5. 使用`hackrf_transfer`软件，连接上硬件设备HackRF one后，在终端输入命令根据模拟的卫星信号文件，开始欺骗

静态欺骗的过程，可以简化至

1. 从在线网站上下载最新的星历RINEX文件
2. 使用`gps-sdr-sim`根据**终端**指定的经纬度海拔坐标和导入的RINEX文件，生成模拟的卫星信号文件
3. 使用`hackrf_transfer`软件，连接上硬件设备HackRF one后，在终端输入命令根据模拟的卫星信号文件，开始欺骗

### 安装工具

#### Google Path Pro

下载链接：https://www.google.cn/intl/zh-CN/earth/versions/#download-pro

软件界面如下

![image-20250803211421637](/pic/image-20250803211421637.png)

> chrome版本的Google Path，也就是网页版，也能生成kml路径文件，但是由于没有将指定路径导出为kml文件的选项，只有将整个项目导出为kml文件。因此同一项目中的信息可能会有之前加载的多条路径信息，不便于以此为基础进行动态欺骗。
>
> ![image-20250803200515016](/pic/image-20250803200515016.png)

#### SatGen  Trajectory generation

这里使用的是SatGen免费的简易工具，相比与SatGen发行版本虽然界面更简单，但是在轨迹细节设置上有更多的功能

https://gitcode.com/Universal-Tool/5b049/?utm_source=article_gitcode_universal&index=top&type=card&

软件界面如下

![image-20250803201502708](/pic/image-20250803201502708.png)

#### gps-sdf-sim

下载项目源码

````bash
git clone https://github.com/osqzss/gps-sdr-sim.git
````

需要手动本地编译成可执行文件`gps-sdr-sim`，后续直接调用该可执行文件即可

````bash
gcc gpssim.c -lm -O3 -o gps-sdr-sim -DUSER_MOTION_SIZE=4000
````

其中`-DUSER_MOTION_SIZE=4000`参数是指定了该工具能生成的运动最大时间，这使得当轨迹文件的运动样本点过多时，也能完整将轨迹数据转换为卫星数据

> note：当设置较大的`DUSER_MOTION_SIZE`参数值后，通过该工具生成的NMEA文件（如果轨迹点足够多的话）体积也会增大

#### hackrf software

````bash
sudo apt-get install hackrf
````

该命令将自动下载hackrf相关的工具，如下

````bash
hackrf_clock      hackrf_debug      hackrf_operacake  hackrf_sweep
hackrf_cpldjtag   hackrf_info       hackrf_spiflash   hackrf_transfer
````

连接上hackRF ONE工具后，使用`hackrf_info`命令检验是否成功连接到硬件设备，显示如下信息则成功连接到该工具

> WSL2 连接usb设备方法可以见 https://m3ngl.github.io/wsl2/2025/08/01/WSL2%E8%BF%9E%E6%8E%A5USB%E8%AE%BE%E5%A4%87/

![image-20250803203616779](/pic/image-20250803203616779.png)

### 准备数据文件

#### KML file

KML文件是一种基于XML的地理数据标记语言文件

打开Google Earth Pro，点击添加 -.> 路径

![image-20250803205701490](/pic/image-20250803205701490.png)

在新建路径窗口弹出后，使用鼠标左键在软件地图中绘制轨迹运动点（右键是消除上一个轨迹运动点）

![image-20250803205829599](/pic/image-20250803205829599.png)

绘制完成后，在新建路径中点击确定，将在左下角 **位置** -> **我的地点**中显示新创建的路径，将其另存为KML文件即可

![image-20250803210413514](/pic/image-20250803210413514.png)

可以看到另存为的KML文件中，记录了通过Google Earth绘制的轨迹路径坐标集

![image-20250803205242481](/pic/image-20250803205242481.png)

#### RINEX file

RINEX文件是广播星历文件，其记录了各个卫星的轨道信息、移动速度、位置等等

> 星历文件中还有一种是精密星历文件，为什么仅使用广播星历文件，可以见 [2.2 星历文件分类](#jump2)

下载地址 https://cddis.nasa.gov/archive/gnss/data/daily/2025/brdc/

> 以往该网站可以直接通过ftp协议在Windows文件资源管理器中显示并下载，但是目前网站官方已禁止该访问途径，只有通过https在浏览器中访问，并注册用户才能打开下载（翻墙情况可能反而无法打开链接，关闭VPN后加载片刻即可进入）
>
> 当然也有国内网站提供相关的星历文件，这里不再赘述

每次进行欺骗都最好下载**当天的**星历文件，以往的星宿文件欺骗成功效率较低

![image-20250803202818819](/pic/image-20250803202818819.png)

下载网页最下端（即当年最新的）的`SSSSDDDf.YYn.gz`文件，如`brdc1060.25n.gz`

> RINEX文件命名含义解释，同样见 [2.2 星历文件分类](#jump2)

在Linux中使用`gunzip`工具解压`.gz`文件得到 `brdc1060.25n`

````bash
gunzip brdc1060.25n.gz
````

#### NMEA file

通过向SatGen软件导入KML文件，生成NMEA文件

该文件保存的是，以卫星协议为载体的导航坐标信息

打开软件，**Google Earth import** -> **Load KML file**

![image-20250804105559095](/pic/image-20250804105559095.png)

导入加载kml文件后，可以看到之前绘制的轨迹图像将自动展现出来，且下方 **Speed profile** 将自动根据 **Dynamic settings** 计算出在该轨迹上运动时各个时刻的速度，以及总耗时

![image-20250804105729212](/pic/image-20250804105729212.png)

Dynamic settings中的参数含义是

* Max longacc 最大纵向加速度
* Max jerk 最大加加速度
* Max latacc 最大横向加速度
* Max speed 最大速度
* Stationary period 起步停留时间
* Stationary period end 结束停留时间

更改相关加速度以及最大速度，使得轨迹运动速度（speed = Scenario distance / total time）在实验的合理范围内，且修改软件输出NMEA文件内容的频率 **Output** 为10hz，其默认是20hz，这是因为随后使用到的gps-sdr-sim工具要求运动的采样率**必须为10hz**。

> Note：实际欺骗过程中，需要一段时间后才能将GNSS接收器成功欺骗到指定坐标，因此建议将这里的`Stationary period`设置为60s以上，便于保证动态欺骗过程从起点出发，而不是从轨迹中途触发

重新更改 **Dynamic settings** 后点击 **Preview**，使得软件重新根据设置计算 **Speed profile** 信息，没有问题后点击 **Generate NMEA file** 即可

> Note：该软件导出NMEA文件的默认后缀是`.txt`，但这并不影响该文件的使用，也可以直接使用notepad打开查看其中的内容

NMEA文件内容是以下形式，其实际上是使用GPGGA协议记录的每个轨迹点的总集

````
$GPGGA,090000.00,3930.74772641,N,11624.62844234,E,1,05,2.87,160.00,M,-21.3213,M,,*75
$GPGGA,090000.10,3930.74772641,N,11624.62844234,E,1,05,2.87,160.00,M,-21.3213,M,,*74
$GPGGA,090000.20,3930.74772641,N,11624.62844234,E,1,05,2.87,160.00,M,-21.3213,M,,*77
$GPGGA,090000.30,3930.74772641,N,11624.62844234,E,1,05,2.87,160.00,M,-21.3213,M,,*76
$GPGGA,090000.40,3930.74772641,N,11624.62844234,E,1,05,2.87,160.00,M,-21.3213,M,,*71
````

#### GPS Signal file

使用`gps-sdf-sim`，根据最新的星历RINEX文件，将NMEA文件转换成GPS信号文件`xxx.bin`

````bash
./gps-sdr-sim -e ./brdc2150.25n -g ./BJ_airport.nmea -b 8 -o dynamic_spoofing.bin
````

![image-20250804121640180](/pic/image-20250804121640180.png)

`gps-sdr-sim`的参数解释

* `-e` 指定星历RINEX文件
* `-g` 专用于生成动态轨迹，指定导入的NMEA文件
* `-b` 指定软件无线电（SDR）处理射频信号时的格式，该工具默认指定`-b 16`，但HackRF one工具在`-b 8`格式下欺骗成功率更高
* `-o` 指定输出的GPS信号文件名称，默认是`gpssim.bin`

### 开始欺骗

对室内设备进行欺骗，其效果会更好，因为欺骗原理本身就是发送伪造的GNSS信号，而在室外会有真实的GNSS信号存在以及噪声等，这些因素将导致欺骗效果不如室内明显。

#### <a id="jump0">静态欺骗</a>

选定经纬度坐标 + 海拔 `39.507517,116.413965,100`，使用`gps-sdr-sim`生成NMEA文件

````bash
./gps-sdr-sim -e ./brdc1200.25n -l 39.507517,116.413965,100 -b 8 -o static_spoofing.bin
````

使用`hackrf_transfer`控制HackRF one硬件工具发送欺骗信号

````bash
hackrf_transfer -t static_spoofing.bin -f 1575420000 -s 2600000 -a 1 -x 1 -R
````

> `hackrf_transfer`的参数解释详情见 [hackrf_transfer参数解释](#jump1)

![image-20250804122927934](/pic/image-20250804122927934.png)

等待一段时间后（通常3min以内），即可在接收器中展现欺骗效果

#### 动态欺骗

````bash
hackrf_transfer -t dynamic_spoofing.bin -f 1575420000 -s 2600000 -a 1 -x 1 -R
````

![image-20250804123049112](/pic/image-20250804123049112.png)

可以将手机开启飞行模式，打开定位服务，并打开地图软件，等待一段时间后，即可展现效果

![2025-08-04-13-44-56](/pic/2025-08-04-13-44-56.gif)

## $Background$

### 卫星频段

GPS频段信息，

- L1频段:1575.42±1.023MHz
- L2频段:1227.60±1.023MHz 
- L3频段:用途和频率暂未公开。
- L5频段:1176.45±1.023MHz（2009年测试，2010年正式播发）

北斗卫星频段信息，

- B1频段:中心频率为1575.42MHz，提供B1I和B1C两种信号。
- B2频段:中心频率为1176.45MHz，提供B2a和B2b两种信号。
- B3频段:中心频率为1268.52MHz，提供B3I信号。

### <a id="jump2">星历文件分类</a>

有两种星历文件，广播星历`RINEX`文件以及精密星历`sp3`文件。

我们进行GNSS欺骗**只需要广播星历**，虽然精密星历的精度远高于广播星历，但在实际卫星导航过程中卫星并不会将精密星历发送给接收器，而是一段时间后保存为文件形式回传给地面以供其他用途，而GNSS欺骗是模拟真实情况的卫星导航，真实的卫星导航仅传递广播星历，因此进行GNSS欺骗只需要广播星历。

广播星历`RINEX`文件有几种版本，但应用最为普遍的是**RINEX V2**格式

#### RINEX V2格式

该版本的命名格式 `XXXXdddf.yyt`，例如 `brdc0960.25n`

| CODE | Meaning                                   |
| ---- | ----------------------------------------- |
| XXXX | 4字符基站名                               |
| ddd  | 一年开始的第ddd天（注意**不是**几月几号） |
| f    | 一天内的第f个文件                         |
| yy   | 年份                                      |
| t    | 文件类型，如：                            |
|      | n = 导航文件                              |
|      | g = 格罗纳斯导航文件                      |

#### RINEX V3格式

该版本的命名格式 `XXXXMRCCC_K_YYYYDDDHHMM_01D_tt.FFF`，如 `BRDM00DLR_S_20251910000_01D_MN.rnx`

第一部分 `XXXXMRCCC_K`

| CODE | Meaning                             |
| ---- | ----------------------------------- |
| XXXX | 4位，IGS测站的名字                  |
| M    | 标记编号(0-9)                       |
| R    | 接收机编号(0 - 9)                   |
| CCC  | ISO国家代码                         |
| K    | 数据来源，其中：                    |
|      | R =从使用供应商或其他软件的接收数据 |
|      | S =从数据流(RTCM或其他)             |
|      | U =未知                             |

第二部分，`YYYYDDDHHMM`

| CODE | Meaning     |
| ---- | ----------- |
| YYYY | 4位，代表年 |
| DDD  | 3位，年积日 |
| HH   | 2位，小时   |
| MM   | 2位，分钟   |

第三部分，`01D_tt.FFF`

| CODE | Meaning                                    |
| ---- | ------------------------------------------ |
| 01D  | 一般来说，这个字段算上`01D`总共有三类：    |
|      | 01D：每天采样一段时间的数据（Daily ）      |
|      | 01H：每小时采样一段时间的数据（Hourly ）   |
|      | 15M：每15分采样一段时间的数据（Minutely ） |
| tt   | 数据类型，其中：                           |
|      | GO = GPS观测数据                           |
|      | RO = GLONASS观测数据                       |
|      | EO = Galileo观测数据                       |
|      | JO = QZSS观测数据                          |
|      | CO = BDS观测数据                           |
|      | IO = IRNSS观测数据                         |
|      | SO = SBAS观测数据                          |
|      | MO = 混合观测数据                          |
|      | GN = GPS导航数据                           |
|      | RN = GLONASS导航数据                       |
|      | EN = Galileo导航数据                       |
|      | JN = QZSS导航数据                          |
|      | CN = BDS导航数据                           |
|      | IN = IRNSS导航数据                         |
|      | SN = SBAS导航数据                          |
|      | MN = 导航数据(所有GNSS星座)                |
|      | MM = 气象观测数据                          |
| FFF  | rnx = RINEX                                |
|      | crx = 高压缩的 RINEX                       |

###  <a id="jump1">hackrf_transfer参数解释</a>

````bash
hackrf_transfer -t spoofing.bin -f 1575420000 -s 2600000 -a 1 -x 10 -R
````

* `-t`：信号采样文件（gps-sdr-sim 生成的GPS信号文件`.bin`）
* `-f`：频率赫兹；美国官方的GPS L1信号频段1575420000Hz
* `-s`：HackRF 采样速率 2.6Msps（其他 sdr 查看 readme ）
* `-a`：是否激活HackRF设备的接收/发射射频放大器：1=使能；0=禁用
* `-x`：增益分贝，TX VGA(中频)增益，0-47db；1dB步长
* `-R`：重复发射模式

增益分贝可以适当调小，甚至设置为0，以免信号强度过大，影响到室内外正常工作的设备

## $Reference$

https://blog.csdn.net/m0_48012049/article/details/108726876

https://blog.csdn.net/Cail466210445/article/details/80777563

https://buaq.net/go-8184.html

https://blog.csdn.net/m0_51561428/article/details/137694563

https://hackrf.readthedocs.io/en/latest/installing_hackrf_software.html

https://blog.csdn.net/wokaowokaowokao12345/article/details/127382933

https://sirlis.cn/posts/astronomy-CDDIS/

https://github.com/osqzss/gps-sdr-sim

https://github.com/oldprogram/gnuradio_demo/tree/main/%E7%BB%BC%E5%90%88%E6%95%99%E7%A8%8B/07-SDR%20GPS/01-hackrf%20GPS%20%E6%AC%BA%E8%AF%88

https://www.mrskye.cn/archives/5d9be0ae/#GPS%E5%AF%BC%E8%88%AA%E7%94%B5%E6%96%87%E5%AE%9A%E4%B9%89

https://hackrf.readthedocs.io/en/latest/hackrf_tools.html

https://developer.aliyun.com/article/310404?utm_source=chatgpt.com

https://blog.csdn.net/qq_35099602/article/details/108183607
