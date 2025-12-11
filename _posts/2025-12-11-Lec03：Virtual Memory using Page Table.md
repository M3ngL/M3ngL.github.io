---
layout: post
title: Lec03：Virtual Memory using Page Table
category: "MIT6.S081 Note"
date: 2025-12-11
---


> xv6课程翻译： https://mit-public-courses-cn-translatio.gitbook.io/mit6-s081/lec04-page-tables-frans
>
> xv6教学文档：https://th0ar.gitbooks.io/xv6-chinese/content/index.html

## 内存的隔离性

程序与数据保存在物理内存中，但物理内存本身是不具备隔离性的

我们需要将不同程序（数据）之间的内存隔离开来，可以使用地址空间技术

**虚拟内存的特征即是地址空间**，地址空间指的是一个进程所能看到的所有虚拟地址的集合，每个进程拥有独立的虚拟地址的集合

实现效果：能够将不同程序之间使用的物理内存隔离开来

具体来说，如果程序 A 想要向地址 `1000` 写入数据，那么程序 A 只会向它自己的地址 `1000`，而不是程序 B 的地址 `1000` 写入数据

所以，每个程序都运行在自己的地址空间，并且这些地址空间彼此之间相互独立。在这种不同地址空间的概念中，程序 A 甚至都不具备引用属于程序 B 内存地址的能力。

> 虚拟内存可以比物理内存更大，物理内存也可以比虚拟内存更大

从硬件层面，我们需要考虑如何在相连的物理内存上，为不同的程序创建不同的地址空间

最终是通过 **page table 来实现虚拟内存**，进一步创建不同的地址空间，实现内存的隔离性

> 还有其他方式实现虚拟内存（这里是分页），如分段、段页式
>
> 虚拟内存的实现方式，即虚拟地址到物理地址的映射机制

## 地址映射

虚拟地址到物理地址的过程由内存管理单元 MMU 统一管理

> 物理地址会被用来索引物理内存，并从物理内存加载，或者向物理内存存储数据

从CPU的角度来说，一旦 MMU 打开了，它执行的每条指令中的地址都是虚拟内存地址

比如当 CPU 执行指令 `sd $7, (a0)`， 假设寄存器 `a0` 中的值是地址 `0x1000`，那么这是一个虚拟内存地址，该虚拟内存地址会被转到内存管理单元，最终可能会被翻译到物理内存地址 `0xFFF0`

具体的地址翻译/映射过程，是根据 MMU 中的表单来进行的，表单将包含物理内存地址，而虚拟地址中的信息是表单的索引

---

**表单本身的位置**

通常来说，地址对应关系的表单也**保存在内存**中。所以CPU中需要有一些寄存器用来存放表单在物理内存中的地址

在 RISC-V 上 `SATP` 寄存器会保存表单在内存中的存储地址，如地址关系表单位于物理内存地址 `0x10`，那么 `SATP` 寄存器的值就是  `0x10`

---

**切换表单**

每个应用程序都有自己独立的表单，并且这个表单定义了该应用程序的地址空间

因此当操作系统将 CPU 使用权从一个应用程序切换到另一个应用程序时，同时也需要切换 SATP 寄存器中的内容，从而指向新的进程保存在物理内存中的地址对应表单

这样的话，进程 A 和进程 B 中相同的虚拟内存地址，就可以翻译到不同的物理内存地址

而每个进程对应的 SATP 值是由内核保存的，内核会修改 SATP 寄存器的值

> 写 SATP 寄存器是一条特殊权限指令，因此只有运行在 kernel mode 的代码可以更新这个寄存器
>
> 用户应用程序不能通过更新这个寄存器来更换一个地址对应表单，否则的话就会破坏隔离性

---

**表单本身的大小**

假设对于每个虚拟地址，在表单中都有一个条目

理论上来看，当寄存器是 `64bit` 的，表单条目将会有 `2^64` 个，所以如果我们以单个地址为粒度来管理，表单会变得非常巨大

所以，实际情况不可能是一个虚拟内存地址对应表单中的一个条目

为了实现实际有用的表单构造，需要**分页**：

* 为每个page创建一条表单条目，即每一次地址翻译都是针对一个 page

> 在 RISC-V 中，一个 page 是 `4KB`，也就是 `4096Bytes`
>
> 几乎所有的处理器都使用 4KB 大小的 page 或者支持 4KB 大小的 page

* 虚拟内存地址划分为两个部分：`index` 和 `offset`
  * `index` 用来查找是第几个 page
  * `offset` 用来查找某个 page 中的偏移量，单位具体到字节

> 比如当 `offset` 是 `12` 时，指的是当前 page 中的第 `12` 个字节

现在让地址转换表是以 page 为粒度，可以叫做 page table 了

---

**粗略的地址翻译过程**

1. 读取虚拟内存地址中的 `index` 可以知道存储在物理内存中的 page 号，这个page号对应了物理内存中的4096个字节
2. 读取虚拟内存地址中的 `offset`，这指向了 page 中的 4096 个字节中的某一个
3. 将 `offset` 加上该 page 的**起始地址**，就可以得到物理内存地址

---

**虚拟/物理地址的二进制位组成**

RISC-V 中，因为 RISC-V 的寄存器是 64bit 的，因此虚拟内存地址都是 64bit

但是实际上并不是所有的 64bit 都被使用了，高 25bit 并没有被使用

> 这样的结果是虚拟内存地址的数量现在只有 `2^39` 个，若是采用一对一的映射方式，那么对应的内存量有 512GB

在剩下的 39bit 中，有 27bit 被用来当做 index，12bit 被用来当做 offset

> **offset 必须是 12bit，因为对应了一个 page 的 4096字节**

地址转换时，MMC 将虚拟内存中的 27bit 翻译成物理内存中的 **44bit** 的 page 号，简称 PPN（Physical Page Number）；虚拟内存中的剩下 12bit 直接给物理地址低位，最终组成最终的物理地址

> 物理地址总共有 56bit，其中 44bit 是 PPN，12bit 和虚拟内存的 `offset` 一致

内存页在物理内存中放置方式是连续的，因此能够直接通过 PPN 找到对应的 page

---

## Page table

假设每个进程都有自己的 page table，那么每个page table表会有多大呢？

由于 page table 最多会有 `2^27` 个条目（对应虚拟内存地址中的 `index` 长度为27），所对应的内存也就有 `2^27` 字节，即128MB

但一个进程使用不了这么多内存，且若每个进程都使用这么大的 page table，进程需要为 page table 消耗大量的内存，并且很快物理内存就会耗尽

因此要考虑将一个 page table 用到多个进程上，即一个 page table 中的条目内容是多个进程的虚拟地址与物理地址的映射关系集合

**page table的设计**

page table是一个多级的结构，分为三个 page directory，迭代查询 page directory 中的条目，最终找到物理地址的高位值

而虚拟内存地址中 27bit 长的 `index`，实际上是由3个 9bit 的数字组成：`L2, L1, L0`，分别对应三个 page directory 的索引

![image-20251211104336811](/pic/image-20251211104336811.png)

> 虚拟内存地址的 `index` 为什么是切割成 9bit+9bit+9bit？
>
> 因为从 directory 的大小来看，一个 directory 大小是 4096Bytes（一个 directory 本质上也是由一个 page 存储，只是从功能上用作了 page directory）
>
> Directory 中的一个条目被称为PTE（Page Table Entry）是 64bits，也就是8Bytes，所以一个Directory page有 `4096/8 = 512` 个条目
>
> 因此作为 directory 的索引 `L2, L1, L0` 各自的大小就是 9bit，这将定位到 `2^9=512` 个条目中的某一个

---

**具体的地址翻译过程**

1. `SATP` 寄存器会指向最高一级的 page directory 的物理内存地址
2. 用虚拟内存中 `index` 的高 9bit `L0` 用来索引最高一级的 page directory，并读取 PTE 中的内容作为PPN，即物理 page 号
3. `PPN * 4096` 即是中间级 page directory 的起始地址
4. 用虚拟内存中 `index` 的中间位 9bit `L1` 用来索引中间级的 page directory，并读取 PTE 中的内容作为PPN
5. `PPN * 4096` 即是最低级 page directory 的起始地址
6. 用虚拟内存中 `index` 的低位 9bit `L2` 用来索引最低级的 page directory，并读取 PTE 中的内容作为PPN
7. `PPN * 4096` 即是最终查询的物理地址的高位

> 为什么是 `PPN * 4096`？
>
> PPN 的大小为 44bit，实际意义是内存页将物理内存分割为多个页面，且连续放置，因此可以直接通过物理 page 号找到对应的 物理 page，而物理 page 的起始地址需要乘以 page 本身的大小，即 4096Bytes
>
> 换句话说，这是要求每个 page directory 都与物理 page 对齐，即低 12bit 均为 `0`
>
> 因此也可以使用 `PPN << 12` 来定位起始地址

这种方式的主要优点是，如果地址空间中大部分地址都没有使用，你不必为每一个 `index` 准备一个条目

---

**方法对比**

举个例子，如果你的地址空间只使用了一个 page，总共 4096Bytes

* 当page table是多级时，最高级 page directory中，索引为 `0` 对应的条目 PTE，将指向中间级page directory；中间级 page directory中，索引为 `0` 对应的条目PTE，指向最低级page directory。因此这里总共需要3个page directory，也就是3 * 512个条目，最终将定位物理地址
* 当page table是单级时，虽然只使用了一个 page table 用于索引，但 page table 内需要 `2^27` 个PTE（对应虚拟地址 `index` 的长度）

> page 特指内存的单位，地址空间的粒度
>
> page table 在其他分配方式中，其大小不一定等于一个 page

**PTE 标志位**

每个PTE的低 10bit 是一些标志位：

- `Valid`，如果 `Valid bit` 位为`1`，那么表明这是一条正确的PTE，可以用它来做地址翻译；而当`Valid bit` 位为 `0` 时，表明这条PTE并不包含有用的信息，相当于告诉MMU，不能使用这条PTE

> 对于应用程序只用了1个page的例子中，我们使用了3个page directory，每个page directory中只有第0个PTE被使用了，所以只有第0个PTE的Valid bit位会被设置成`1`，其他511个PTE的Valid bit将设置为`0`

- `Readable/Writable`，表明是否可以读/写这个page
- `Executable` 表明是否可以从这个page执行指令
- `User` 表明这个page可以被运行在用户空间的进程访问
- ...

**page fault**

当一个PTE是无效的，会返回一个page fault，对于这个page fault，操作系统可以更新 page table 并再次尝试指令，或者其他的操作

page directory 的条目中必须存的是 PPN，因为需要在物理内存中查找下一个 page directory 的地址。不能让我们的地址翻译依赖于另一个翻译，否则可能会陷入递归的无限循环中

---

**页表缓存**

当处理器从内存加载或者存储数据时，基本上都要做3次内存查找，第一次在最高级的page directory，第二次在中间级的page directory，最后一次在最低级的page directory。所以对于一个虚拟内存地址的寻址，需要读三次内存。

所以实际中，几乎所有的处理器都会对于最近使用过的虚拟地址的翻译结果有缓存，称为页表缓存（TLB），也就是对 Page Table Entry (PTE)的缓存

因此当切换了page table，操作系统需要告诉处理器当前正在切换page table，而处理器会清空TLB

在RISC-V中，清空TLB的指令是 `sfence_vma`

---

**page table是由硬件实现的**

三级的page table是由硬件实现的，所以三级 page table 的查找都发生在硬件中。且MMU是硬件的一部分而不是操作系统的一部分。

> 在XV6中，`walk` 函数也实现了对 page table 的查找，因为 XV6 偶尔也需要完成硬件的工作

xv6 中使用软件模拟页表寻址的功能，原因是

* 操作系统需要通过 `walk` 函数设置最初的 page table，即需要对三级 page table 进行编程，因此需要能模拟三级 page table
* 在XV6中，**内核空间有它自己的page table，用户空间也有自己的page table**，为了在同一进程切换用户态/内核态时，还能传递某些数据，需要用户空间中指向 `sys_info` 结构体的指针（该指针存在于用户空间的page table）翻译成一个内核空间也可以读写的物理地址

内核空间会通过用户空间进程的 page table，将用户的虚拟地址翻译得到物理地址，这样内核可以读写相应的物理内存地址

## Kernel Page Table

XV6的虚拟地址与物理地址的映射关系图

![image-20251211104955551](/pic/image-20251211104955551.png)

右侧物理内存中的各个设备，包括RAM的分布都是由硬件设计者决定的

左侧虚拟内存中大部分的映射关系都是，一对一相等关系（对应图中的水平箭头）

> XV6 为尽可能的简单易懂，将大部分虚拟地址到物理地址的映射关系设置为了相等

操作系统启动时，会从地址 `0x80000000` 开始运行

> 启动地址 `0x80000000` 是由硬件设计者决定的

在完成了虚拟到物理地址的翻译之后，以RISC-V开发板为例

* 如果得到的物理地址大于 `0x80000000` 会走向DRAM芯片
* 如果得到的物理地址低于 `0x80000000` 会走向不同的I/O设备

> 这是由这个主板的设计人员决定的物理结构

比如，地址`0`是保留的，地址 `0x10090000` 对应以太网，地址 `0x80000000` 对应DDR内存

其他的I/O设备：

- PLIC（Platform-Level Interrupt Controller）是中断控制器
- CLINT（Core Local Interruptor）也是中断的一部分。所以多个设备都能产生中断，需要中断控制器来将这些中断路由到合适的处理函数
- UART0（Universal Asynchronous Receiver/Transmitter）负责与Console和显示器交互
- VIRTIO disk，与磁盘进行交互

比如地址 `0x02000000` 对应CLINT，当向这个地址执行读写指令，是向实现了CLINT的芯片执行读写。这里可以认为直接在与设备交互，而不是读写物理内存

**guard page**

左侧虚拟内存中存在 guard page 分布

| Virtual Address |      |
| :-------------: | ---- |
|   Trampoline    | R-X  |
|   Guard page    | ---  |
|    Kstack 0     | RW-  |
|   Guard page    | ---  |
|       ...       |      |

这样当kernel stack耗尽了，它会溢出到Guard page，但是因为Guard page的PTE中Valid标志位未设置，会导致立即触发page fault

同时Guard page不会占用物理内存，因为 Guard page 不会映射到任何物理内存，它只是占据了虚拟地址空间的一段地址

另外，kernel stack实际上被映射了两次，在这里的虚拟地址（ `MAXVA` 至 `PHYSTOP` 之间）映射了一次，在 `PHYSTOP` 下的 Kernel data 中又映射了一次，但是实际使用的时候用的是上面的部分，因为有 Guard page 会更加安全

> 映射关系可以是向同一个物理地址映射两个虚拟地址，可以不将一个虚拟地址映射到物理地址，可以是一对一映射，一对多映射，多对一映射

每一个用户进程都有一个对应的 kernel stack

在kernel page table的 `PHYSTOP` 至 `KERNBASE` 之间，有一段 Free Memory，它直接对应了物理内存中的一段地址，XV6使用这段 free memory 来存放用户进程的page table，text和data

## 地址映射初始化

从操作系统启动后，什么时候开始使用虚拟地址？

当机器刚刚启动时，还没有可用的page，XV6 会设置好内核使用的虚拟地址空间，具体来说

从 `kernel/main.c -> main()` 函数中可以发现这一初始化过程

````c
// kernel/main.c
...
// start() jumps here in supervisor mode on all CPUs.
void main(){
  if(cpuid() == 0){
    consoleinit();
    printfinit();
    printf("\n");
    printf("xv6 kernel is booting\n");
    printf("\n");
    kinit();         // physical page allocator
    kvminit();       // create kernel page table
    kvminithart();   // turn on paging
  ...
}
````

1.  `kvminit()` 函数

````c
// Initialize the one kernel_pagetable
void
kvminit(void)
{
  kernel_pagetable = kvmmake();
}


// Make a direct-map page table for the kernel.
pagetable_t
kvmmake(void)
{
  pagetable_t kpgtbl;

  kpgtbl = (pagetable_t) kalloc();
  memset(kpgtbl, 0, PGSIZE);

  // uart registers
  kvmmap(kpgtbl, UART0, UART0, PGSIZE, PTE_R | PTE_W);

  // virtio mmio disk interface
  kvmmap(kpgtbl, VIRTIO0, VIRTIO0, PGSIZE, PTE_R | PTE_W);

  // PLIC
  kvmmap(kpgtbl, PLIC, PLIC, 0x400000, PTE_R | PTE_W);

  // map kernel text executable and read-only.
  kvmmap(kpgtbl, KERNBASE, KERNBASE, (uint64)etext-KERNBASE, PTE_R | PTE_X);

  // map kernel data and the physical RAM we'll make use of.
  kvmmap(kpgtbl, (uint64)etext, (uint64)etext, PHYSTOP-(uint64)etext, PTE_R | PTE_W);

  // map the trampoline for trap entry/exit to
  // the highest virtual address in the kernel.
  kvmmap(kpgtbl, TRAMPOLINE, (uint64)trampoline, PGSIZE, PTE_R | PTE_X);

  // allocate and map a kernel stack for each process.
  proc_mapstacks(kpgtbl);
  
  return kpgtbl;
}
````

`kpgtbl = (pagetable_t) kalloc();` 为最高一级page directory分配物理page

`memset(kpgtbl, 0, PGSIZE);` 将这段内存初始化为0

`kvmmap(kpgtbl, XXX, XXX, PGSIZE, PTE_R | PTE_W);` 通过`kvmmap`函数，将每一个I/O设备映射到内核，且是将物理地址映射到相同的虚拟地址

内核会持续的按照这种方式，调用kvmmap来设置地址空间，之后会对VIRTIO0、CLINT、PLIC、kernel text、kernel data 以及 TRAMPOLINE进行地址映射

2.  `kvminithart` 函数

````c
// Switch h/w page table register to the kernel's page table,
// and enable paging.
void kvminithart(){
  // wait for any previous writes to the page table memory to finish.
  sfence_vma();

  w_satp(MAKE_SATP(kernel_pagetable));

  // flush stale entries from the TLB.
  sfence_vma();
}
````

该函数将设置 SATP 寄存器， MMU 自此开始使用刚刚设置好的 page table

之后的下一条指令被执行时，程序计数器中的地址值会被内存中的 page table 作为虚拟地址翻译

地址翻译从这条指令之后开始生效，之后的每一个使用的内存地址都可能对应到与之不同的物理内存地址

在这条指令之前，我们使用的都是物理内存地址，这条指令之后page table开始生效
