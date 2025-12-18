---
layout: post
title: XV6-Lab3：page tables
category: "MIT6.S081 Note"
date: 2025-12-18
---


> 课程作业：https://pdos.csail.mit.edu/6.828/2022/labs/pgtbl.html
>
> 第三方答案：
>
> - https://github.com/relaxcn/xv6-labs-2022-solutions/blob/main/doc/pagetable.md
> - https://blog.miigon.net/posts/s081-lab3-page-tables/

文件具体修改见仓库 [commit](https://github.com/M3ngL/xv6-labs-2022-ans/commits/pgtbl/)

## Speed up system calls 

> When each process is created, map one read-only page at USYSCALL (a virtual address defined in `memlayout.h`). At the start of this page, store a `struct usyscall` (also defined in `memlayout.h`), and initialize it to store the PID of the current process. For this lab, `ugetpid()` has been provided on the userspace side and will automatically use the USYSCALL mapping. You will receive full credit for this part of the lab if the `ugetpid` test case passes when running `pgtbltest`.

题目大意：当每一个进程被创建，映射一个只读的页在 **USYSCALL** （在`memlayout.h`定义的一个虚拟地址）处。存储一个 `struct usyscall` （定义在 `memlayout.h`）结构体在该页的开始处，并且初始化这个结构体来保存当前进程的 PID

难点在于：这个只读页内部存储的是哪个变量，首先变量值来源肯定是 `p->pid`，该值赋值给新建的结构体 `struct usyscall`

如果是在 `proc_pagetable` 函数中定义一个临时结构体变量，临时声明一段内存给到该变量

````c
struct usyscall *u = kalloc();
u->pid = p->pid;
mappages(pagetable, USYSCALL, PGSIZE, (uint64)u, PTE_R | PTE_U);
````

当 `proc_pagetable` 函数退出后，该变量将消失，因为该变量是栈上的局部变量；这样将导致释放这段内存时调用 `kfree` 无法找到对应的物理内存地址

 因此，我们需要将指向这段内存的指针保存下来，最方便的即是保存到 `proc` 结构体中（题目背景就是以进程为单位的）

首先在 `proc` 结构体增加新字段

````c
 struct usyscall *u;
````

新建进程且分配为该进程分配内存时，在函数 `allocproc` 中为新字段分配内存，且将内存指针赋值给 `p->u`

````c
if((p->u = (struct usyscall *)kalloc()) == 0){
    freeproc(p);
    release(&p->lock);
    return 0;
}
````

对应的，释放进程占用的内存时，也需要显式释放这段内存，在 `freeproc` 函数中增加

````c
if(p->u) kfree((void*)p->u);
````

本题的另一个重点在于为进程建立独立的虚拟地址空间，我们需要在 `proc_pagetable` 函数中顺带将 `p->u` 映射到页面的虚拟地址 `USYSCALL`

````c
p->u->pid = p->pid;
if(mappages(pagetable, USYSCALL, PGSIZE,
          (uint64)p->u, PTE_R | PTE_U) < 0){
    uvmfree(pagetable, 0);
    return 0;
}
````

同样对应的，当释放这段虚拟地址空间时，也需要在 `proc_freepagetable` 函数中将这段映射释放掉

````c
uvmunmap(pagetable, USYSCALL, 1, 0);
````

该函数的参数分别是

* `pagetable`：需要释放的页表
* `USYSCALL`：该页表中的偏移量
* `1`：需要释放多少个页面
* `0`：是否需要释放对应的物理内存

## Print a page table

> Define a function called `vmprint()`. It should take a `pagetable_t` argument, and print that pagetable in the format described below. Insert `if(p->pid==1) vmprint(p->pagetable)` in exec.c just before the `return argc`, to print the first process's page table. You receive full credit for this part of the lab if you pass the `pte printout` test of `make grade`.

题目大意：写新函数 `vmprint()` 来打印页表的内容。它应该接收一个 `pagetable_t` 类型的参数，并且按照下面的格式打印。在 `exec.c` 中的 `return argc` 之前插入 `if(p->pid==1) vmprint(p->pagetable)` ，用来打印第一个进程的页表。

![image-20251218113320060](/pic/image-20251218113320060.png)

根据打印内容，我们可以发现该函数 `vmprint()` 需要实现对页表进行递归形式地遍历

`最高级页表 -> 中间级页表 -> 最低级页表`，需要将这三级页表中记录的每个PTE都打印出来

构造递归函数，函数传参包括页表与当前的递归深度，即第几级页表

````bash
void vmprint(pagetable_t pagetable, uint16 depth){
	...
}
````

在递归的基础上，我们需要判断什么时候不再进行递归，显然是到最低级页表时不再进行递归，为了代码的冗余度这里从PTE标志位来判断：当前PTE是否为叶子节点

````c
if((pte & (PTE_R|PTE_W|PTE_X)) == 0){
    vmprint((pagetable_t)xxx, depth);
}
````

`if` 语句条件意思是当前 PTE 的读/写/执行标志位，其中任意一个是否存在，若都不存在则认为当前 PTE 为叶子节点

综上，完整的 `vmprint` 函数如下

````c
// kernel/vm.c
void vmprint(pagetable_t pagetable, uint16 depth){
  if(depth++ == 1)
    printf("page table %p\n", pagetable);

  for(int i = 0; i < 512; i++){
    pte_t pte = pagetable[i];
    if(pte & PTE_V){
      for(int j = 1; j < depth; j++) printf(" ..");
      uint64 child = PTE2PA(pte);
      printf("%d: pte %p pa %p\n", i, pte, child);
      if((pte & (PTE_R|PTE_W|PTE_X)) == 0)
        vmprint((pagetable_t)child, depth);
    }
  }
}
````

注意：`depth` 变量在传递给下一级递归时，不能在这层递归进行自增（这层的 `for` 循环很可能还没有结束），否则会影响到打印时同级页表的深度，打印出的层级如下  `.. ..255` 本应该是 `..255`，诸如此类

````bash
page table 0x0000000087f6b000
 ..0: pte 0x0000000021fd9c01 pa 0x0000000087f67000
 .. ..0: pte 0x0000000021fd9801 pa 0x0000000087f66000
 .. .. ..0: pte 0x0000000021fda01b pa 0x0000000087f68000
 .. .. ..1: pte 0x0000000021fd9417 pa 0x0000000087f65000
 .. .. ..2: pte 0x0000000021fd9007 pa 0x0000000087f64000
 .. .. ..3: pte 0x0000000021fd8c17 pa 0x0000000087f63000
 .. ..255: pte 0x0000000021fda801 pa 0x0000000087f6a000
 .. .. ..511: pte 0x0000000021fda401 pa 0x0000000087f69000
 .. .. .. ..509: pte 0x0000000021fdcc13 pa 0x0000000087f73000
 .. .. .. ..510: pte 0x0000000021fdd007 pa 0x0000000087f74000
 .. .. .. ..511: pte 0x0000000020001c0b pa 0x0000000080007000
init: starting sh
````

因此将 `depth` 变量自增放在了 `for`  循环以外

## Detect which pages have been accessed

> Your job is to implement `pgaccess()`, a system call that reports which pages have been accessed. The system call takes three arguments. First, it takes the starting virtual address of the first user page to check. Second, it takes the number of pages to check. Finally, it takes a user address to a buffer to store the results into a bitmask (a datastructure that uses one bit per page and where the first page corresponds to the least significant bit). You will receive full credit for this part of the lab if the `pgaccess` test case passes when running `pgtbltest`.

题目大意：实现一个系统调用 `sys_pgaccess()` 在文件 `kernel/sysproc.c` 中。这个系统调用会告诉我们哪一个页被访问过。此系统调用接收三个参数。第一：被检查的第一个用户页的起始虚拟地址；第二：被检查页面的数量；第三：接收来自用户地址空间的一个 buffer 地址，将结果以掩码（bitmask）的形式写入。（掩码 bitmask 就是一个数据结构，其一个位代表一个页面，第一个页代表最低有效位）。

实现效果：我们需要在当前进程的页表中，根据第一个参数作为需要检查页面的起始地址，根据第二个参数的数量按顺序逐个访问页面，若某个页面的标志位显示曾被访问过，那么将该页面的序号写入**函数内定义的临时变量** `bitmask`，最终通过第三个参数的地址从内核空间传回用户空间

> 页面的序号写入 `bitmask` 的方式如下：
>
> 若第2个被检查的页面显示被访问过，第1个被检查的页面显示没有被访问过，那么 `bitmask` 此时的值应该是 `0b10`
>
> `bitmask` 的总位数取决于被检查页面的数量

首先理解函数的传参以及使用方法（包括返回值 `abits` 处理），从官方给的使用样例来看

````c
// user/pgtbltest.c
void pgaccess_test(){
  char *buf;
  unsigned int abits;
  printf("pgaccess_test starting\n");
  testname = "pgaccess_test";
  buf = malloc(32 * PGSIZE);
  if (pgaccess(buf, 32, &abits) < 0)
    err("pgaccess failed");
  buf[PGSIZE * 1] += 1;
  buf[PGSIZE * 2] += 1;
  buf[PGSIZE * 30] += 1;
  if (pgaccess(buf, 32, &abits) < 0)
    err("pgaccess failed");
  if (abits != ((1 << 1) | (1 << 2) | (1 << 30)))
    err("incorrect access bits set");
  free(buf);
  printf("pgaccess_test: OK\n");
}
````

用户空间中 `pgaccess` 函数接收 `buf, 32, &abits`

* `buf` 是这里声明的**第一个用户页的起始虚拟地址**

````
char *buf;
buf = malloc(32 * PGSIZE);
````

> `malloc()` 返回的地址是进程虚拟地址空间中合法的部分，由页表正确映射到物理内存

* `32` 代表被检查页面的数量
* `abits` 是定义在用户空间，准备接收来自内核空间结果的变量，传递的是其地址 `&abits`，方便后续 `copyout` 函数写入

当从用户空间调用 `pgaccess` 函数后，跳转到内核空间执行系统调用 `sys_pgaccess`，需要按顺序从寄存器获取这些参数

````c
int pagenum;
uint64 buf_addr, abits_addr;

argaddr(0, &buf_addr);
argint(1, &pagenum);
argaddr(2, &abits_addr);
````

在实际处理逻辑之前，还需要定义新的 access 标志位的宏定义 `PTE_A`

根据官方 hint 给出的文档  [RISC-V privileged architecture manual](https://github.com/riscv/riscv-isa-manual/releases/download/Ratified-IMFDQC-and-Priv-v1.11/riscv-privileged-20190608.pdf)，可以发现 access 标志位位于低位第6位

![image-20251218143002753](/pic/image-20251218143002753.png)

因此定义

````c
#define PTE_A (1L << 6) // access bit
````

接下来开始实际处理，使用 `for` 逐个遍历要求检查的页面，起始位置为函数传参 `buf`

由于我们目前只有页面的序号，不是真实的页面，需要使用 `walk` 函数访问到实际的页面，即 PTE

````c
for(int i = 0; i < pagenum; i++){
    pte_t* pte = walk(pagetable, buf + i * PGSIZE, 0);
    ...
}
````

> `walk(pagetable_t pagetable, uint64 va, int alloc)` 函数参数 `alloc` 表示当前传入的 `pagetable` 是否需要分配内存

进一步地，检查当前页面的 access 标志位，并将结果写入 `bitmask`

````c
bitmask += ((PTE_A & PTE_FLAGS(*pte)) != 0) << i;
````

其中 `PTE_FLAGS` 是将 PTE 的位数剪裁只剩标志位，再与 `PTE_A` 做**与运算**，查看得到的结果是否为 `0`

* 若为 `0`，则表示当前页面未被访问
* 若不为 `0`（实际上为 `1<<6`），则表示当前页面被访问过

检查完成后，根据官方 hint 还要将 access 标志位置 `0`，我们已经有当前页面 PTE，直接将结果赋值给ta即可

````c
*pte = ~PTE_A & *pte;
````

`for` 循环结束后，即所有的页面检查完成后，调用 `copyout` 函数

````c
copyout(pagetable, abits, (char*) &bitmask, sizeof(uint64))
````

完整的内核空间 `pgaccess` 函数实现如下：

````c
// kernel/vm.c
int pgaccess(uint64 buf, int pagenum, uint64 abits, pagetable_t pagetable){
  uint64 bitmask = 0;
  for(int i = 0; i < pagenum; i++){
    pte_t* pte = walk(pagetable, buf + i * PGSIZE, 0);
    if (pte == 0)
      panic("page not exist.");
    bitmask += ((PTE_A & PTE_FLAGS(*pte)) != 0) << i;
    *pte = ~PTE_A & *pte;
  }
  
  if(copyout(pagetable, abits, (char*) &bitmask, sizeof(uint64)) < 0){
    return -1;
  }
  return 0;
}
````

 中转函数 `sys_pgaccess` 实现如下：

````c
int sys_pgaccess(void){
  int pagenum;
  uint64 buf_addr, abits_addr;

  argaddr(0, &buf_addr);
  argint(1, &pagenum);
  argaddr(2, &abits_addr);

  struct proc *p = myproc();

  if(pgaccess(buf_addr, pagenum, abits_addr, p->pagetable) < 0){
    return -1;
  }
  
  return 0;
}
````
