# Term Definitions : 
[op] := neg | add | sub | mul | div | mod | not | and | or | xor | shl | shr  
[jcc] := jz | jnz | jgt | jge | jlt | jle

# Previously available TAC commands : 
- %t1 = copy %t2
- %t1 = const n
- %t1 = [op] %t2 / [op] %t2 %t3
- param n %t1
- [label] : 
- print %t1
- ret
- jmp [label]
- [jcc] %condition [label]
- %t1 = call [func_name] %n


# Newly added commands : 
## Any name preceded by a % is a temporary, anything else is a constant : 
- %t1 = load %tb
- %t1 = load (%tb, offset)  
- store %t1, %tb 
- store %t1, (%tb, offset)  
=> Commands suggested by TD  

- %t1 = ref %t2   
=> Removed by asm phase
- %t1 = alloc %block_count, block_size
- zero_out %tb, num_bytes   
- copy_array %dest, %src, num_bytes   
=> Refer to runtime c functions
