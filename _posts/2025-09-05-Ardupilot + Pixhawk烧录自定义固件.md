---
layout: post
title: Ardupilot + Pixhawk烧录自定义固件
category: "ArduPilot"
date: 2025-09-05
---


环境 + 版本

* Pixhawk 2.4.8
* Mission Planner v1.3.82
* Ardupilot v4.5.7
* QGroundControl v4.4.2

`Pixhawk 2.4.8` 选用的编译固件型号为 `fmuv3`

Pixhawk 2.4.8所使用的处理板信息：`STM32F427 VIT6 (168 Mhz/256 KB RAM/2 MB 闪存 100Pin)`

> RAM是指内存；闪存相当于外存；2 MB 闪存是用于存储日志文件

## 编译

修改ardupilot项目中的相关代码后，开始编译

**配置编译信息**

````bash
./waf configure --board xxx
````

查询Ardupilot所支持的固件种类

````
./waf list_boards
````

所支持的型号有

````
3DRControlZeroG, ACNS-CM4Pilot, ACNS-F405AIO, aero, AeroFox-Airspeed, AeroFox-Airspeed-DLVR, AeroFox-GNSS_F9P, AeroFox-PMU, airbotf4, AIRLink, Airvolute-DCS2, AnyleafH7, Aocoda-RC-H743Dual, AR-F407SmartBat, ARK_CANNODE, ARK_GPS, ARK_RTK_GPS, ARKV6X, AtomRCF405NAVI, bbbmini, BeastF7, BeastF7v2, BeastH7, BeastH7v2, bebop, BETAFPV-F405, bhat, BirdCANdy, BlitzF745, BlitzF745AIO, BlitzH743Pro, BlitzMiniF745, BlitzWingH743, blue, BotBloxDroneNet, C-RTK2-HP, canzero, CarbonixF405, CarbonixL496, CBU-H7-Stamp, crazyflie2, CSKY405, CUAV-7-Nano, CUAV-Nora, CUAV-Nora-bdshot, CUAV-Pixhack-v3, CUAV-X7, CUAV-X7-bdshot, CUAV_GPS, CUAVv5, CUAVv5-bdshot, CUAVv5Nano, CUAVv5Nano-bdshot, CubeBlack, CubeBlack+, CubeBlack-periph, CubeGreen-solo, CubeOrange, CubeOrange-bdshot, CubeOrange-joey, CubeOrange-ODID, CubeOrange-periph, CubeOrange-periph-heavy, CubeOrange-SimOnHardWare, CubeOrangePlus, CubeOrangePlus-bdshot, CubeOrangePlus-SimOnHardWare, CubePilot-CANMod, CubePilot-PPPGW, CubePurple, CubeRedPrimary, CubeRedPrimary-PPPGW, CubeRedSecondary, CubeSolo, CubeYellow, CubeYellow-bdshot, dark, DevEBoxH7v2, disco, DrotekP3Pro, Durandal, Durandal-bdshot, edge, erleboard, erlebrain2, esp32buzz, esp32diy, esp32empty, esp32icarus, esp32nick, esp32s3devkit, esp32s3empty, esp32tomte76, f103-ADSB, f103-Airspeed, f103-GPS, f103-HWESC, f103-QiotekPeriph, f103-RangeFinder, f103-Trigger, f303-GPS, f303-HWESC, f303-M10025, f303-M10070, f303-MatekGPS, f303-PWM, f303-TempSensor, f303-Universal, F35Lightning, f405-MatekAirspeed, f405-MatekGPS, F4BY, FlyingMoonF407, FlyingMoonF427, FlyingMoonH743, FlywooF405HD-AIOv2, FlywooF405Pro, FlywooF405S-AIO, FlywooF745, FlywooF745Nano, FlywooH743Pro, fmuv2, fmuv3, fmuv3-bdshot, fmuv5, FoxeerF405v2, FoxeerH743v1, FreeflyRTK, G4-ESC, GEPRCF745BTHD, H757I_EVAL, H757I_EVAL_intf, HEEWING-F405, HEEWING-F405v2, Here4AP, Here4FC, Hitec-Airspeed, HitecMosaic, HolybroF4_PMU, HolybroG4_Airspeed, HolybroG4_Compass, HolybroG4_GPS, HolybroGPS, IFLIGHT_2RAW_H7, iomcu, iomcu-dshot, iomcu-f103, iomcu-f103-8MHz-dshot, iomcu-f103-dshot, iomcu_f103_8MHz, JFB100, JFB110, JHEM_JHEF405, JHEMCU-GSF405A, JHEMCU-GSF405A-RX2, JHEMCU-H743HD, KakuteF4, KakuteF4-Wing, KakuteF4Mini, KakuteF7, KakuteF7-bdshot, KakuteF7Mini, KakuteH7, KakuteH7-bdshot, KakuteH7-Wing, KakuteH7Mini, KakuteH7Mini-Nand, KakuteH7v2, kha_eth, linux, LongBowF405WING, luminousbee4, luminousbee5, MambaF405-2022, MambaF405US-I2C, MambaF405v2, MambaH743v4, MatekF405, MatekF405-bdshot, MatekF405-CAN, MatekF405-STD, MatekF405-TE, MatekF405-TE-bdshot, MatekF405-Wing, MatekF405-Wing-bdshot, MatekF765-SE, MatekF765-Wing, MatekF765-Wing-bdshot, MatekG474-DShot, MatekG474-Periph, MatekH743, MatekH743-bdshot, MatekH743-periph, MatekH7A3, MatekL431-ADSB, MatekL431-Airspeed, MatekL431-APDTelem, MatekL431-BattMon, MatekL431-bdshot, MatekL431-DShot, MatekL431-EFI, MatekL431-GPS, MatekL431-HWTelem, MatekL431-MagHiRes, MatekL431-Periph, MatekL431-Proximity, MatekL431-Rangefinder, MatekL431-RC, MatekL431-Serial, MazzyStarDrone, MFT-SEMA100, MicoAir405Mini, MicoAir405v2, MicoAir743, mindpx-v2, mini-pix, modalai_fc-v1, mRo-M10095, mRoCANPWM-M10126, mRoControlZeroClassic, mRoControlZeroF7, mRoControlZeroH7, mRoControlZeroH7-bdshot, mRoControlZeroOEMH7, mRoCZeroOEMH7-bdshot, mRoKitCANrevC, mRoNexus, mRoPixracerPro, mRoPixracerPro-bdshot, mRoX21, mRoX21-777, navigator, navigator64, navio, navio2, Nucleo-G491, Nucleo-L476, Nucleo-L496, NucleoH743, NucleoH755, NxtPX4v2, obal, ocpoc_zynq, omnibusf4, omnibusf4pro, omnibusf4pro-bdshot, omnibusf4pro-one, omnibusf4v6, OMNIBUSF7V2, OmnibusNanoV6, OmnibusNanoV6-bdshot, OrqaF405Pro, PH4-mini, PH4-mini-bdshot, Pix32v5, PixC4-Jetson, PixFlamingo, PixFlamingo-F767, Pixhawk1, Pixhawk1-1M, Pixhawk1-1M-bdshot, Pixhawk1-bdshot, Pixhawk4, Pixhawk4-bdshot, Pixhawk5X, Pixhawk6C, Pixhawk6C-bdshot, Pixhawk6X, Pixhawk6X-bdshot, Pixhawk6X-ODID, Pixhawk6X-PPPGW, PixPilot-C3, PixPilot-V3, PixPilot-V6, PixPilot-V6PRO, Pixracer, Pixracer-bdshot, Pixracer-periph, PixSurveyA1, PixSurveyA1-IND, PixSurveyA2, pocket, pxf, pxfmini, QioTekAdeptF407, QioTekZealotF427, QioTekZealotH743, QioTekZealotH743-bdshot, QURT, R9Pilot, RadiolinkPIX6, RADIX2HD, ReaperF745, revo-mini, revo-mini-bdshot, revo-mini-i2c, revo-mini-i2c-bdshot, revo-mini-sd, rFCU, rGNSS, rst_zynq, SDMODELH7V1, SDMODELH7V2, Sierra-F405, Sierra-F412, Sierra-F9P, Sierra-L431, Sierra-PrecisionPoint, Sierra-TrueNavIC, Sierra-TrueNavPro, Sierra-TrueNavPro-G4, Sierra-TrueNorth, Sierra-TrueSpeed, sitl, SITL_arm_linux_gnueabihf, sitl_periph, sitl_periph_battmon, sitl_periph_gps, sitl_periph_universal, SITL_static, SITL_x86_64_linux_gnu, SIYI_N7, SkystarsH7HD, SkystarsH7HD-bdshot, skyviper-f412-rev1, skyviper-journey, skyviper-v2450, sparky2, speedybeef4, SpeedyBeeF405Mini, SpeedyBeeF405WING, speedybeef4v3, speedybeef4v4, SPRacingH7, SPRacingH7RF, SuccexF4, sw-boom-f407, sw-nav-f405, sw-spar-f407, Swan-K1, TBS-Colibri-F7, thepeach-k1, thepeach-r1, TMotorH743, vnav, VRBrain-v51, VRBrain-v52, VRBrain-v54, VRCore-v10, VRUBrain-v51, VUAV-V7pro, X-MAV-AP-H743v2, YJUAV_A6, YJUAV_A6SE, YJUAV_A6SE_H743, YJUAV_A6Ultra, ZeroOneX6, ZubaxGNSS, zynq
````

> 注意飞控开发板的名字不一定与这里的一一对应，如 `Pixhawk2.4.8` 所需要的编译型号就是`fmuv3`

编译完成后，编译出的固件位于 `ardupilot/build/your_board/bin`

## 烧录

使用地面站`Mission Planner`进行烧录

> 还有其他的烧录方式，如QGC以及Ardupilot官方脚本进行烧录
>
> Mission Planner图形化界面最为方便，故这里使用Mission Planner

使用usb连接Pixhawk后，打开`Mission Planner`，**此时不要在Mission Planner中点击Connect**

> 烧录固件的过程中不能将Mission Planner连接到Pixhawk中原有的飞控固件，否则无法删除原有飞控并烧录新的飞控
>
> 但可以通过选择栏目判断Mission Planner是否成功识别到串口连接，如下图`COM4`为正确连接
>
> ![image-20250905174420749](/pic/image-20250905174420749.png)

`SETUP` -> `Install Firmware /  Install Firmware Legacy` -> `Load custom firmware`

![image-20250420105901348](/pic/image-20250420105901348.png)

> `Install Firmware /  Install Firmware Legacy`的区别是下载官方固件的版本不同，但我们这里准备烧录的是自定义固件，不采用官方准备的固件，因此两个选项都可以选
>
> `Install Firmware` 是下载地面站获取到的最新版本固件
>
> `Install Firmware Legacy` 是可以下载地面站获取到的旧版本固件，下图是二者界面上的差别
>
> ![image-20250905175044147](/pic/image-20250905175044147.png)

点击`Load custom firmware`后，选择文件路径，导至编译得到的固件文件`xxx.apj`，如果型号对应，地面站软件会自动开始烧录。

若准备烧入的固件型号与开发板不对应，地面站软件会产生报错，并不再进行烧录

另外，插入飞控板后也有可能提示

![Snipaste_2025-05-20_19-33-42](/pic/Snipaste_2025-05-20_19-33-42.png)

按照提示内容将现已连接的Pixhawk拔开USB，再重新连接USB串口，最后点击`Mission Planner`弹窗中的 `OK`

Mission Planner将自动烧录

## MAVLink检测

地面站软件QGC -> Analyze Tools -> MAVLink检测

> Ardupilot编译的固件可能无法连接Mavlink 控制台的bug（暂未解决），否则可以直接使用终端命令查看相关信息

**内存占用信息**

`MEMINFO`中的字段`freemem`，其值若为`35696`，则代表目前硬件板空闲的内存为`35696B`，相当于`34.859375KB`

由于使用的Pixhawk 2.4.8搭载的内存大小为`256KB`，因此目前飞控软件使用的内存大小为`256 - 34.859375KB`

![image-20250905175910619](/pic/image-20250905175910619.png)

**cpu负载**

`SYS_STATUS`字段中的`load`字段，其值若为`539`，代表CPU占用`53.9%`

![image-20250905180126426](/pic/image-20250905180126426.png)

## $Reference$

https://zhuanlan.zhihu.com/p/553439264

https://discuss.ardupilot.org/t/difference-between-install-fiirmware-and-lnstall-firmware-legacy/73418/3

https://blog.csdn.net/qq_37692302/article/details/107631473

https://blog.csdn.net/Maaa_25/article/details/119139797
