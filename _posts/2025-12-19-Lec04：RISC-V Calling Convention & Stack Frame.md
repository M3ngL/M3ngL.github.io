---
layout: post
title: Lec04：RISC-V Calling Convention & Stack Frame
category: "MIT6.S081 Note"
date: 2025-12-19
---


> xv6课程翻译： https://mit-public-courses-cn-translatio.gitbook.io/mit6-s081/lec05-calling-conventions-and-stack-frames-risc-v
>
> xv6教学文档：https://th0ar.gitbooks.io/xv6-chinese/content/index.html

## 架构指令集

* RISC-V中的RISC是精简指令集（Reduced Instruction Set Computer）
* x86通常被称为CISC，复杂指令集（Complex Instruction Set Computer）
* ARM也是一个精简指令集

RISC-V与x86二者之间的区别

- 指令的数量。`CISC >> RISC`，这是因为ntel对于向后兼容非常看重，并没有下线任何指令
- RISC-V指令也更加简单。
  - x86-64中，很多指令都做了不止一件事情。这些指令中的每一条都执行了一系列复杂的操作并返回结果
  - RISC-V的指令趋向于完成更简单的工作，相应的也消耗更少的CPU执行时间
- RISC是开源的

---

RISC-V的特殊之处在于：它区分了Base Integer Instruction Set 基础整数指令集和Standard Extension Instruction Set 标准扩展指令集

* Base Integer Instruction Set包含了所有的常用指令，比如 `add，mult`
* 处理器可以选择性的支持Standard Extension Instruction Set

## RISC-V Calling Convention Register

汇编代码并不是在内存上执行，而是在寄存器上执行。当在做基本操作如 `add` 时，是对寄存器进行操作

使用寄存器在汇编代码中的体现通常是，

1. `load` 操作将数据存放在寄存器中，数据来源可以是内存，也可以是另一个寄存器
2. 在寄存器上执行一些操作
3. 操作结束后，可以将操作的结果 `store` 在某个地方：内存中的某个地址或者另一个寄存器

RISC-V 调用约定寄存器的使用方法：

![image-20251219122021981](/pic/image-20251219122021981.png)

* **Register**：该列名称一般用于 RISC-V 的 Compressed Instruction 中
* **ABI Name**：该列名称在大部分时候使用，包括汇编代码
* **Saver**：
  * **Caller** Saved 寄存器的值在函数调用发生后可以随意更改，调用之前的寄存器值已经被 Caller 保存到其他地方
  * **Callee** Saved 寄存器的值在函数调用发生后必须保存原值，调用完成后必须恢复原值

比如，`ra` 寄存器是 Caller Saved，当函数 a 调用函数 b 的时侯，b 函数内部可以重写 Return address

因此，任何一个Caller Saved寄存器，作为调用方的函数要小心可能的数据可能的变化；任何一个Callee Saved寄存器，作为被调用方的函数要小心寄存器的值不会相应的变化

> 比如`s0 - s11`都是Callee寄存器，在一些特定的场景下，会想要确保一些数据在函数调用之后仍然能够保存，这个时候编译器可以选择使用s寄存器。

---

xv6 中所有的寄存器都是 64bit，各种各样的数据类型都可以被改造的可以放进这 64bit 中

比如一个 32bit 的整数存储在寄存器中时，会通过在前面补 32 个 `0` 或者 `1`（取决于整数是不是有符号的）来使得这个整数变成 64bit 并存在这些寄存器中

> 只将返回值放在a1寄存器，我认为会出错
>
>  `a0` 到 `a7` 寄存器是用来作为函数的参数。如果一个函数有超过8个参数，就需要用内存了

## Stack Frame

每一次调用一个函数，函数都会为自己创建一个Stack Frame，并且只给自己用

函数通过移动 `Stack Pointer(SP)` 来完成 Stack Frame 的空间分配

Stack 是从高地址开始向低地址使用，所以栈总是**向下增长**

````bash
高地址
+-----------------------+
|main 的栈帧	   	   	  |
|	Return Address		|
|	保存的旧 FP -> (指向更早的帧或 NULL)
|	Saved Registers		|
|	Local Variables		|
|	......         		|
+-----------------------+
|funcA 的栈帧	   	   	  |
|	Return Address		|
|   保存的旧 FP → 指向 main 的栈帧开头
|	Saved Registers		|
|	Local Variables		|
|	......         		|
+-----------------------+
|funcB 的栈帧	   	   	  | ← 当前 Frame Pointer (fp/s0) 指向这里
|	Return Address		|
|   保存的旧 FP → 指向 funcA 的栈帧开头
|	Saved Registers		|
|	Local Variables		|
|	......         		|  			
+-----------------------+
低地址（栈顶 sp）
````

如图所示，Stack Frame包含了

* 保存的寄存器
* 本地变量，
* 可能的函数参数（如果函数的参数多于8个，额外的参数会出现在Stack中）

有关Stack Frame中有两个重要的寄存器，

* SP（Stack Pointer），它指向Stack的底部并代表了当前Stack Frame的位置
* FP（Frame Pointer），它指向当前Stack Frame的顶部

除此以外，不同的函数有不同数量的本地变量，不同的寄存器，所以Stack Frame的**大小是不一样**的

但是有关Stack Frame有两件事情是确定的：

- **`Return address`** 总是会出现在 Stack Frame 的第一位
- **指向前一个 Stack Frame 的指针**也会出现在栈中的固定位置，该指针即是上一个栈帧的FP

因为Return address和指向前一个Stack Frame的的指针都在当前Stack Frame的固定位置，所以可以通过当前的FP寄存器寻址到这两个数据

我们保存前一个Stack Frame的指针的原因是为了让我们能跳转回去

---

Stack Frame必须要被汇编代码创建，所以是编译器生成了汇编代码，进而创建了Stack Frame

通常在汇编代码中，函数的理论结构是

* Function prologue
* 函数的本体 body
* Epilogue

以 `sum_then_double` 函数为例

````nasm
.global sum_then_double
sum_then_double:
	addi	sp, sp, -16
	sd		ra, 0(sp)
	call	sum_to
	li		t0, 2
	mul		a0, a0, t0
	ld		ra, 0(sp)
	addi	sp, sp, 16
	ret
	
sum_to:
	mv		t0, a0
	li		a0, 0
  loop:
  	add		a0, a0, t0
  	addi	t0, t0, -1
  	bnez	t0, loop
  	ret
````

其中 Function **prologue**：对Stack Pointer减 `16`，这样就为新的 Stack Frame 创建了16字节的空间，之后再将 `Return address` 保存在 Stack Pointer 位置

````nasm
addi	sp, sp, -16
sd		ra, 0(sp)
````

函数主体 **body**，调用的 `sum_to` 函数是一个 leaf 函数，该函数只有函数主体，并没有Stack Frame的内容

> leaf 函数是指不调用别的函数的函数，它不用担心保存自己的 `Return address` 或者小心使用任何其他的 Caller Saved 寄存器，因为它不会调用别的函数

````nasm
call	sum_to
li		t0, 2
mul		a0, a0, t0
````

**Epilogue**：将 `Return address` 加载回 `ra` 寄存器，通过对Stack Pointer加 `16` 来删除刚刚创建的Stack Frame，最后 `ret` 从函数中退出

````nasm
ld		ra, 0(sp)
addi	sp, sp, 16
ret
````

> 如果直接删掉 prologue 和 Epilogue 部分，将导致 `ra` 寄存器始终是指向 `sum_to` 或者  `sum_then_double`，这样让 `sum_then_double` 函数始终返回不到原来的 `Return address`，进入无限循环

---

**在 GDB 中查看 Stack Frame info**

断点到某一个函数，输入 `bt` 查看函数的调用栈

可以根据调用栈的栈帧序号，选定要查看的栈帧信息，即 `frame x`

查看当前指定的栈帧信息 `info frame`

![image-20251219120839662](/pic/image-20251219120839662.png)

`info frame` 的回显解释

- `Stack level 6`，表明这是调用栈的第6层，正在执行的函数在调用栈的第0层
- `pc`，当前的程序计数器
- `saved pc = ` ，如果有值的话，是表明当前函数要返回的位置
- `source language c`，表明这是C代码
- `Arglist at`，表明参数的起始地址，且 `args:` 为空表示当前的函数没有参数

---

**Strct 在 Stack Frame 中的存储方式**

Struct 在内存中是一段连续的地址

当创建 Struct 时，结构体中对应相邻的字段在内存中会彼此相邻

>  可以将 Struct 看作是一个数组，但是里面的不同元素的类型可以不一样
