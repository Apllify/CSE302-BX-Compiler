	.data
	.globl	x
x:
	.quad	15
	.text
	.globl	fact
fact:
	pushq	%rbp
	movq	%rsp, %rbp
	subq	$32, %rsp
	movq	%rdi, -8(%rbp)
.L12:
	movq	$1, -16(%rbp)
	movq	-16(%rbp), %rdi
	movq	-8(%rbp), %rsi
	callq	fact_
	movq	%rax, -24(%rbp)
	movq	-24(%rbp), %rax
	jmp	.E_fact
	movq	$0, %rax
.E_fact:
	movq	%rbp, %rsp
	popq	%rbp
	retq
	.text
	.globl	fact_
fact_:
	pushq	%rbp
	movq	%rsp, %rbp
	subq	$64, %rsp
	movq	%rdi, -8(%rbp)
	movq	%rsi, -16(%rbp)
.L13:
	movq	$0, -24(%rbp)
	movq	-24(%rbp), %r11
	subq	-16(%rbp), %r11
	movq	%r11, -32(%rbp)
	cmpq	$0, -32(%rbp)
	jge	.L2
.L4:
	movq	-8(%rbp), %rax
	imulq	-16(%rbp)
	movq	%rax, -40(%rbp)
	movq	$1, -48(%rbp)
	movq	-16(%rbp), %r11
	subq	-48(%rbp), %r11
	movq	%r11, -56(%rbp)
	movq	-40(%rbp), %rdi
	movq	-56(%rbp), %rsi
	callq	fact_
	movq	%rax, -64(%rbp)
	movq	-64(%rbp), %rax
	jmp	.E_fact_
.L2:
	movq	-8(%rbp), %rax
	jmp	.E_fact_
	movq	$0, %rax
.E_fact_:
	movq	%rbp, %rsp
	popq	%rbp
	retq
	.text
	.globl	main
main:
	pushq	%rbp
	movq	%rsp, %rbp
	subq	$16, %rsp
.L15:
	movq	x(%rip), %rdi
	callq	fact
	movq	%rax, -8(%rbp)
	movq	-8(%rbp), %rdi
	callq	print
	jmp	.E_main
	movq	$0, %rax
.E_main:
	movq	%rbp, %rsp
	popq	%rbp
	retq
