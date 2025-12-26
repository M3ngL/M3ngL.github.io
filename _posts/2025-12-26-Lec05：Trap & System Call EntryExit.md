---
layout: post
title: Lec05：Trap & System Call Entry/Exit
category: "MIT6.S081 Note"
date: 2025-12-26
---


> xv6课程翻译： https://mit-public-courses-cn-translatio.gitbook.io/mit6-s081/lec06-isolation-and-system-call-entry-exit-robert
>
> xv6教学文档：https://th0ar.gitbooks.io/xv6-chinese/content/index.html

## Trap 机制

用户空间和内核空间的切换通常被称为 `trap`，切换时机一般发生在：

- 程序执行了系统调用，一般由软件中断触发
- 程序出现了类似page fault、运算时除以0的错误
- 设备中断使得当前程序运行需要响应内核设备驱动

本节是需要清楚如何让程序的运行，从只拥有user权限并且位于用户空间的Shell，切换到拥有supervisor权限的内核

在这个过程中，硬件的状态将会非常重要，将硬件从适合运行用户应用程序的状态，改变到适合运行内核代码的状态

**切换过程中的重点寄存器**

- `PC (Program Counter Register)`程序计数器，指向程序即将要执行的指令
- `SATP（Supervisor Address Translation and Protection）`寄存器，它包含了指向当前 page table 的物理内存地址。
- `STVEC（Supervisor Trap Vector Base Address Register）`寄存器，它指向了内核中处理trap的指令的起始地址
- `SEPC（Supervisor Exception Program Counter）`寄存器，在 trap 的过程中保存程序计数器的值
- `SSRATCH（Supervisor Scratch Register）` 寄存器，存放当前进程的 trapframe 指针

---

在 trap 的最开始，CPU的所有状态依旧是运行在用户代码中而不是内核代码

因此在 trap 处理的过程中，需要更改一些状态或者对状态做一些操作，这样我们才可以运行系统内核中普通的C程序

需要做的操作如下：

- 需要保存 32 个用户寄存器

> 显然在切换到内核空间后，还需要切换回用户空间，因此需要恢复用户应用程序的执行，而程序的执行离不开寄存器
>
> 所以这意味着32个用户寄存器不能被内核弄乱，但是这些寄存器又要被内核代码所使用，所以在 trap 处理逻辑开始之前，必须先在某处保存这32个用户寄存器
>
> 尤其是当用户程序随机的被设备中断所打断时，内核是需要响应中断的，并需要在响应结束后在用户程序完全无感知的情况下再恢复用户代码的执行
>
> 从安全角度来看，trap 中涉及到的硬件和内核机制不能依赖任何来自用户空间东西，比如这里不能依赖32个用户寄存器，它们可能保存的是恶意的数据，所以，XV6的trap机制不会查看这些寄存器，而只是将它们保存起来

- 保存并修改程序计数器 `PC`，修改后的 `PC` 的值为内核中的 C 代码

> 保存的作用是需要中断结束后能够在用户程序运行中断的位置继续执行用户程序

- 修改 mode 状态为 `supervisor mode`

> 这样做会带来一些变化，但很有限：
>
> * 程序能够读写控制寄存器，`SATP，STVEC，SEPC，SSCRATCH`等等
> * 程序能够使用 `PTE_U` 标志位为 0 的PTE
>   * `PTE_U` 标志位为 `1` ，表明只有 `user mode` 下可以使用这个页表
>   * `PTE_U` 标志位为 `0` ，表明只有 `supervisor mode` 下可以使用这个页表

- 将 `SATP` 寄存器指向 kernel page table，目前是指向 user page table

> user page table 只包含了用户程序所需要的内存映射和一两个其他的映射，它并没有包含整个内核数据的内存映射，因此需要切换为 kernel page table
>
> upervisor mode中的代码并不能读写任意物理地址，也需要通过page table来访问内存，且如果一个虚拟地址并不在当前由SATP指向的page table中，又或者SATP指向的page table中 `PTE_U=1`，那么supervisor mode不能使用那个地址

- 将堆栈寄存器指向位于内核的一个地址，因为我们需要一个堆栈来调用内核的C函数

> 这样才能给C代码提供栈

## Trap 执行流程

接下来以 Shell 执行 write 系统调用为例，

> 从 Shell 的角度来说，这就是个 Shell 代码中的C函数调用

总体流程如下：

1. 用户空间的 `write` 函数将执行 `ECALL` 指令，该指令会将程序执行切换到具有 supervisor mode 的内核中，内核中执行的第一个指令是一个汇编函数 `uservec`，位于内核代码 `trampoline.s`

>  `ECALL` 之后将中断了用户代码的执行，转由内核代码执行，执行过程将覆盖寄存器的值，为了在内核代码结束后，顺利恢复执行用户空间的代码，需要在之后的部分中做一系列的事情，如存储/恢复，尤其是汇编函数中

2. 在 `uservec` 汇编函数中，代码执行将跳转到由C语言实现的函数 `usertrap` 中，位于 `trap.c` 
3. 在 `usertrap` C函数中，执行 `syscall` C函数
4. `syscall` 会在一个指针数组中，根据传入的代表系统调用的数字进行查找，并在内核中执行具体实现了系统调用功能的函数  `sys_write`
5. `sys_write` 将要显示的数据输出到 console 上，完成了之后，将写定的返回值返回给 `syscall` 函数
6. `syscall` 函数结束时会调用 `usertrapret` C函数，也位于 `trap.c`，将完成方便在C代码中实现的返回到用户空间的工作
7. `usertrapret` C函数结束时，将执行汇编函数 `userret`，位于内核代码 `trampoline.s`，以完成最后的存储/恢复工作

> 之所以考虑在汇编代码中完成大部分的存储/恢复工作，是因为用户寄存器必须在汇编代码中保存，因为任何需要经过编译器的语言，例如C语言，都不能修改任何用户寄存器

8. 在 `userret` 汇编函数中会调用机器指令 `sret` 返回到用户空间，并且恢复 `ECALL` 之后的用户程序的执行

### ECALL

Shell 调用用户空间的 `write` 函数时，实际上调用的是关联到 Shell 的一个库函数，该函数位于`usys.s`

````nasm
write:
	li	a7, SYS_write
	ecall
	ret
````

将 `SYS_write` 赋值给 `a7` 寄存器后，执行 `ecall` 指令

执行完 `ecall` 指令，将完成这些事情：

* 将代码从 user mode 改到 supervisor mode
* 将程序计数器的值保存在了 `SEPC` 寄存器
* 程序执行跳转到 `STVEC` 寄存器指向的指令地址 `0x3ffffff000`（是固定位置，对应着当前进程的 trampoline page）

> 验证 `ecall` 指令效果，根据 `sh.asm` 中的指令地址，对`ecall`指令位置下断点，可以看到：
>
> 执行 `ecall` 指令前
>
> ![image-20251222210939022](/pic/image-20251222210939022.png)
>
> 执行 `ecall` 指令后
>
> ![image-20251222211348936](/pic/image-20251222211348936.png)
>
> * `pc` 的指向在用户空间时在距离 `0` 比较近的地址，因为用户空间中所有的地址都比较小
> * `pc` 的指向在内核空间时在地址值较大，这是因为内核使用从数值角度大得多的内存地址
>
> 在上一次从内核空间进入到用户空间之前，内核会设置好 `STVEC` 寄存器指向内核希望 trap 代码运行的位置

而为了最终能够实现执行内核中的代码，还需要

- 需要保存32个用户寄存器的内容
- 需要切换到 kernel page table，现在还在user page table

> 为什么切换到 supervisor mode 后还要使用 page table 机制？
>
> 在RISC-V中，supervisor mode 下的代码不允许直接访问物理内存，所以只能继续使用 page table 来映射
>
> 一种思路：直接将 `SATP` 寄存器指向 kernel page table，之后就可以直接使用所有的 kernel mapping 来存储用户寄存器

- 需要创建或者找到一个 kernel stack，并将 Stack Pointer 寄存器的内容指向那个 kernel stack
- 需要跳转到内核中C代码的某些合理的位置

> 为什么不让 `ecall` 指令执行完整的效果？
>
> * 某些操作系统可以在不切换 page table 的前提下，执行部分系统调用。切换page table的代价比较高，如果ecall打包完成了这部分工作，那就不能对一些系统调用进行改进，使其不用在不必要的场景切换page table。
> * 某些操作系统同时将user和kernel的虚拟地址映射到一个page table中，这样在user和kernel之间切换时根本就不用切换page table。
> * 一些系统调用过程中，实际上一些寄存器不用保存，而哪些寄存器需要保存，哪些不需要
> * 对于某些简单的系统调用或许根本就不需要任何stack

执行 `ecall` 指令之后，可以查看当前寄存器内容

![image-20251222211742976](/pic/image-20251222211742976.png)

显然，`a0, a1, a2` 都还是 `wirte` 函数的传参内容

### uservec

前文提到，程序执行跳转到 `STVEC` 寄存器指向的指令地址 `0x3ffffff000`，该地址对应当前进程的 trampoline page

> 之所以叫 trampoline page，是因为系统执行某种程度在它上面“弹跳”了一下，然后从用户空间走到了内核空间

````nasm
.section trampsec
.globl trampoline
trampoline:
.align 4
.globl uservec
uservec:
	...
````

程序执行到 trampoline page 的最开始，即 `uservec` 汇编函数

---

为了使 Trap 推进下去，首先要做的是**保存用户寄存器的内容**，这是因为在未保存前，内核还不能使用寄存器

![image-20251222213430411](/pic/image-20251222213430411.png)

此时将执行 `csrw  sscratch, a0` 指令，这将交换寄存器 `a0` 和 `SSCRATCH` 的内容

为什么是与 `SSCRATCH` 寄存器交换内容，是因为：

为了保存所有的用户寄存器，XV6 统一将其保存在 trapframe page，具体包括了两个部分：

* XV6 在**每个 user page table** 映射了 trapframe page，这样**每个进程**都有自己的 trapframe page
* 在内核前一次切换回用户空间时，**内核会将 `SSCRATCH` 寄存器的内容设置为 trapframe page 的虚拟地址（是固定的 `0x3fffffe000`）**，因此通过 `ecall` 指令切换到内核空间后，交换 `a0` 和 `SSCRATCH` 寄存器的内容，即可使得 `a0` 指向 trapframe page

trapframe page 包括了保存用户寄存器的 32 个空槽位，是专门用于存储寄存器内容的

> trapframe page 和  trampoline page 不同，后者是存储 Trap 机制的指令
>
> * 为什么需要在每个 user page table 都映射 trapframe page？
>
> 之前提到 `ecall` 指令并不会切换到 kernel page table，所以这意味着，trap 处理代码必须存在于每一个 user page table 中，这是由内核映射到每一个 user page table 中

现在可以通过 `a0` 寄存器的值，访问到 trapframe page，将其他用户寄存器的值保存到该页中，方式就是

````bash
offset(a0) # 偏移量 + a0的位置
````

![image-20251222215740544](/pic/image-20251222215740544.png)

> `scrw` 指令后对 `a0` 寄存器的操作是为了在 `a0` 中构造一个用于内核态的边界地址
>
> `sd` 指令将左侧的寄存器内容传入到右侧指向的内存中

从 `40` 个字节开始存储寄存器的值，原因是 trapframe 的结构定义：

````c
struct trapframe {
  /*   0 */ uint64 kernel_satp;   // kernel page table
  /*   8 */ uint64 kernel_sp;     // top of process's kernel stack
  /*  16 */ uint64 kernel_trap;   // usertrap()
  /*  24 */ uint64 epc;           // saved user program counter
  /*  32 */ uint64 kernel_hartid; // saved kernel tp
  /*  40 */ uint64 ra;
	...
}
````

保存完所有的用户寄存器之后，开始将 trapframe 中原本带有的数据存入寄存器（ 位于 trapframe 结构体 `40` 字节之前的）

![image-20251226154514092](/pic/image-20251226154514092.png)

* 加载 `a0` 指向的内存地址往后数的第8个字节 `kernel_sp` 到 Stack Pointer 寄存器
* 向 `tp` 寄存器写入数据 `kernel_hartid`

> 在RISC-V中，没有一个直接的方法来确认当前运行在多核处理器的哪个核上，XV6会将CPU核的编号 `hartid` 保存在 `tp`  寄存器

* 向 `t0` 寄存器写入数据 `kernel_trap`，指向函数 `usertrap` 的指针，即内核空间第一个执行的函数
* 向 `t1` 寄存器写入数据 `kernel_satp`，指向 kernel page table

> 严格来说，`t1` 寄存器写入的内容并不是 kernel page table 的地址，这是需要向 `SATP` 寄存器写入的数据，不等同于kernel page table 的地址。它既包含了kernel page table的高位地址，也包含了各种标志位

* `csrw  stap, t1` 指令是交换 `SATP` 和 `t1` 寄存器，执行完成之后，当前程序会从 user page table 切换到 kernel page table

> 刚刚完成切换时，为什么同一个虚拟地址不会通过新的 page table 寻址走到一些无关的page中从而崩溃?
>
> 因为在 trampoline page 中，同时在 user page table 和 kernel page table 都有相同的映射关系，因此不会崩溃

* `jr t0` 指令，从 trampoline 跳到内核的C代码 `usertrap` 函数中

![image-20251226155952021](/pic/image-20251226155952021.png)

**至此page table完成切换；Stack Pointer指向了kernel stack；页表是 kernel page table，可以读取kernel data；通过 `jr` 指令跳转到了内核中的C代码**

此时是以kernel stack，kernel page table 跳转到 `usertrap` 函数

### usertrap

`usertrap` 函数在某种程度上会存储并恢复硬件状态，但是它也需要检查触发 trap 的原因，以确定相应的处理方式

````c
//
// handle an interrupt, exception, or system call from user space.
// called from trampoline.S
//
void usertrap(void){
  int which_dev = 0;

  if((r_sstatus() & SSTATUS_SPP) != 0)
    panic("usertrap: not from user mode");

  // send interrupts and exceptions to kerneltrap(),
  // since we're now in the kernel.
  w_stvec((uint64)kernelvec);
	...
}
````

1. **更改 `STVEC` 寄存器**，将STVEC指向了 `kernelvec` 变量，这是内核空间 trap 处理代码的位置，不是用户空间 trap 处理代码的位置
2. **确定当前运行的是什么进程**

````c
struct proc *p = myproc();
````

> 其中 `myproc` 函数内部会查找一个根据当前CPU核的编号索引的数组，CPU核的编号是 `hartid` 
>
> `hartid` 变量之前在 `uservec` 函数中将它存在了 `tp` 寄存器，这是myproc函数找出当前运行进程的方法

3. **保存用户程序计数器**，此时该值依然保存在 `SEPC` 寄存器中

````c
// save user program counter.
p->trapframe->epc = r_sepc();
````

> 为什么需要从 `SEPC` 寄存器挪到 trapframe 中而不是就让ta在该寄存器中？
>
> 因为当程序在内核中执行时，系统可能切换到另一个进程，并进入到那个程序的用户空间，然后那个进程可能再调用一个系统调用进而导致 `SEPC` 寄存器的内容被覆盖
>
> 因此需要保存当前进程的 `SEPC` 寄存器到一个与该进程关联的内存中，这样这个数据才不会被覆盖

4. **确定触发 trap 的原因**

````c
if(r_scause() == 8){
    // system call
    ...
} else if((which_dev = devintr()) != 0){
    // ok
} else {
    printf("usertrap(): unexpected scause %p pid=%d\n", r_scause(), p->pid);
    printf("            sepc=%p stval=%p\n", r_sepc(), r_stval());
    setkilled(p);
}
````

数字 `8` 表明，我们现在在 trap 代码中是因为系统调用

5. **进入 `if` 语句内部**，首先确定当前进程是否被 kill，然后对保存在 trapframe 的用户程序计数器 `+4`

````c
if(killed(p))
  exit(-1);

// sepc points to the ecall instruction,
// but we want to return to the next instruction.
p->trapframe->epc += 4;
````

> `+4` 的原因是第三步中使用的存储在 `SEPC` 寄存器中的程序计数器值，是用户程序中触发 trap 的指令的地址，即 `ecall` 指令的地址
>
> 但当内核代码执行结束，回到用户程序时，肯定是继续执行 `ecall` 之后的一条指令，因此这里 `+4`

6. **在 `if` 语句内部，打开中断**

在 trap 过程中，RISC-V 的 trap 硬件总是会关闭中断

而 XV6 中有些系统调用内部需要许多时间处理，为了使中断可以更快的服务其他情况，会在处理系统调用的时候使能中断

````c
// an interrupt will change sepc, scause, and sstatus,
// so enable only now that we're done with those registers.
intr_on();
````

7.  **在 `if` 语句内部，调用 `syscall` 函数**，定义在 `syscall.c` 

````c
syscall();
````

`syscall` 函数的工作就是获取由 trampoline 代码中保存在 trapframe 中 `a7` 寄存器的值，然后用这个数字对包含了每个系统调用指针的数组进行索引，之后就将执行系统调用对应的函数内容

这里重点关注 `syscall` 函数结束时，将系统调用函数的返回值赋值给了 trapframe 中对应的 `a0` 寄存器

````c
p->trapframe->a0 = syscalls[num]();
````

这样做的原因是：所有的系统调用都有一个返回值，比如 `write` 会返回实际写入的字节数，而RISC-V上的C代码的习惯是函数的返回值存储于寄存器 `a0` ，所以为了模拟函数的返回，我们将返回值存储在 trapframe 的 `a0` 中。之后，当我们返回到用户空间，trapframe中的 `a0` 槽位的数值会写到实际的 `a0` 寄存器，Shell会认为 `a0` 寄存器中的数值是 `write` 系统调用的返回值。

8. `syscall` 函数返回后，回到 `usertrap` 函数，在这里**调用函数 `usertrapret`**

````c
if(killed(p))
    exit(-1);

// give up the CPU if this is a timer interrupt.
if(which_dev == 2)
    yield();

usertrapret();
````

### usertrapret

1. **关闭中断**

````c
//
// return to user space
//
void
usertrapret(void)
{
  struct proc *p = myproc();

  // we're about to switch the destination of traps from
  // kerneltrap() to usertrap(), so turn off interrupts until
  // we're back in user space, where usertrap() is correct.
  intr_off();
````

关闭中断是因为将要更新 `STVEC` 寄存器来指向用户空间的 trap 处理代码，之前在内核中的时候，`STVEC` 寄存器指向的是内核空间的 trap 处理代码

如果这时发生了一个中断，即便现在程序执行仍然在内核中，也将走向用户空间的 trap 处理代码，进而导致内核出错

2. **将 `STVEC` 寄存器指向 trampoline 代码**

````c
// send syscalls, interrupts, and exceptions to uservec in trampoline.S
uint64 trampoline_uservec = TRAMPOLINE + (uservec - trampoline);
w_stvec(trampoline_uservec);
````

`trampoline_uservec` 变量指向的地址会执行 `sret` 指令，从而返回到用户空间

> `sret` 指令会重新打开中断

3. **将内核当前寄存器值填入 trapframe**

````c
// set up trapframe values that uservec will need when
// the process next traps into the kernel.
p->trapframe->kernel_satp = r_satp();         // kernel page table
p->trapframe->kernel_sp = p->kstack + PGSIZE; // process's kernel stack
p->trapframe->kernel_trap = (uint64)usertrap;
p->trapframe->kernel_hartid = r_tp();         // hartid for cpuid()
````

- 存储了kernel page table的指针
- 存储了当前用户进程的 kernel stack
- 存储了 `usertrap` 函数的指针
- 从 `tp` 寄存器中读取当前的CPU核编号，并存储在 trapframe 中

> 从 `tp` 寄存器中读取当前的CPU核编号是为了防止，在进入内核态前用户代码修改过 `tp` 寄存器

4. **设置 `SSTATUS` 寄存器**

````c
// set up the registers that trampoline.S's sret will use
// to get to user space.

// set S Previous Privilege mode to User.
unsigned long x = r_sstatus();
x &= ~SSTATUS_SPP; // clear SPP to 0 for user mode
x |= SSTATUS_SPIE; // enable interrupts in user mode
w_sstatus(x);
````

* `SSTATUS` 寄存器的 `SPP` 位控制了 `sret` 指令的行为，为 `0` 时表示下次执行 `sret` 的时候，是返回 user mode 而不是 supervisor mode
* `SSTATUS` 寄存器的 `SPIE` 位控制了，在执行完 `sret` 之后，是否打开中断

5. **设置 `SEPC` 寄存器**

````c
// set S Exception Program Counter to the saved user pc.
w_sepc(p->trapframe->epc);
````

将 `SEPC` 寄存器的值设置成之前保存的用户程序计数器的值

6. **根据 user page table 地址生成相应的 `SATP` 寄存器中应该存储的值，传入 `trampoline_userret`**

> 前文说过， `SATP` 寄存器存储的值，和 page table 地址不是等价关系

````c
// tell trampoline.S the user page table to switch to.
uint64 satp = MAKE_SATP(p->pagetable);

// jump to userret in trampoline.S at the top of memory, which 
// switches to the user page table, restores user registers,
// and switches to user mode with sret.
uint64 trampoline_userret = TRAMPOLINE + (userret - trampoline);
((void (*)(uint64))trampoline_userret)(satp);
````

`trampoline_userret` 指向 `userret` 汇编函数，该函数位于 trampoline，将在其中完成 page table 的切换

`satp` 变量将由硬件赋值给 `a0` 寄存器

>  page table 的切换只能在 trampoline 中完成切换，因为只有 trampoline 中代码是同时在用户和内核空间中映射
>
> 目前仅是将指向 user page table 的指针准备好，因为目前位于C函数中，而不是 trampoline

### userret

程序执行到了位于 trampoline 中的 `userret` 汇编函数

1. **切换 page table**

````nasm
userret:
        # userret(pagetable)
        # called by usertrapret() in trap.c to
        # switch from kernel to user.
        # a0: user page table, for satp.

        # switch to the user page table.
        sfence.vma zero, zero
        csrw satp, a0
        sfence.vma zero, zero
````

执行 `csrw satp, a0`，将 user page table 地址存储在SATP寄存器中

> user page table也映射了 trampoline page，所以程序还能继续执行而不是崩溃

2. **将 trapframe 的地址赋值给 `a0` 寄存器**

````nasm
li a0, TRAPFRAME
````

`a0` 寄存器之前曾经保存过 trapframe 的地址，但函数调用后，函数传参将赋值给 `a0` 寄存器，因此早已被修改了，这里需要重新赋值 `TRAPFRAME`

截至目前，所有的寄存器内容还是属于内核

3. **恢复用户寄存器**，将 trapframe 中之前保存的寄存器的值加载到对应的各个寄存器中

包括恢复用户空间下的 `a0` 寄存器（有些系统调用会产生返回值，在之前的步骤中已经赋值到了 `trapframe->a0`）

````nasm
# restore all but a0 from TRAPFRAME
ld ra, 40(a0)
ld sp, 48(a0)
ld gp, 56(a0)
ld tp, 64(a0)
ld t0, 72(a0)
ld t1, 80(a0)
ld t2, 88(a0)
ld s0, 96(a0)
...
# restore user a0
ld a0, 112(a0)
````

4. **执行 `sret` 指令**

````nasm
# return to user mode and user pc.
# usertrapret() set up sstatus and sepc.
sret
````

`sret` 是在 kernel 中的最后一条指令，当执行完这条指令：

- 程序会切换回 user mode
- `SEPC` 寄存器的数值会被拷贝到 `PC` 寄存器
- 重新打开中断

5. **执行 `ecall` 指令的下一句指令 `ret` 指令**

回到用户空间后，将继续执行 `ecall` 指令之后的指令 

````nasm
write:
     li a7, SYS_write
         e14:	48c1                	li	a7,16
     ecall
         e16:	00000073          	ecall
     ret
         e1a:	8082                	ret
````

执行完 `ret` 指令之后，将从 `write` 系统调用返回到 Shell 中

## 其他

* 为什么要将寄存器保存在 trapframe page 而不是用户代码的栈中？

首先，不确定用户程序是否有栈，必然有一些编程语言没有栈，对于这些编程语言的程序，Stack Pointer寄存器将不指向任何地址。也有一些编程语言有栈，但是或许它的格式很奇怪，内核并不能理解。

如果我们想要运行任意编程语言实现的用户程序，内核就不能假设用户内存的哪部分可以访问，哪部分有效，哪部分存在。所以内核需要自己管理这些寄存器的保存

* `sret` 指令的作用

`sret` 指令是由 RISC-V 定义的用来从 supervisor mode 转换到 user mode

当机器启动的时候，默认是在内核中。不管是进程第一次启动还是从一个系统调用返回，进入到用户空间的唯一方法是就是执行 `sret` 指令

* trap 的处理方式要区分是来自于用户空间还是内核空间

如果 trap 从内核空间发起，程序已经在使用kernel page table，因此很多从用户空间发起 trap 时的处理都不必存在

* qemu 快捷键 + 查看当前程序执行下完整的 page table

xv6 运行界面输入 `ctrl a + c` 可以进入到 QEMU 的 console

在该 console 中再输入 `info mem`，QEMU会打印完整的 page table

![Snipaste_2025-12-22_21-12-45](/pic/Snipaste_2025-12-22_21-12-45.png)

* PTE标志位解释

  * r，是否可读

  * w，是否可写

  * x，是否可执行

  * u，user mode下是否可以使用

  * g，global

  * a，access，是否被访问过

  * d， dirty，是否被修改过

* 内存映射文件机制

通过 page table，可以将用户空间的虚拟地址空间，对应到文件内容，这样就可以通过内存地址直接读写文件，而无需通过一个文件描述符来读写文件。这将比直接调用read/write系统调用要快的多
