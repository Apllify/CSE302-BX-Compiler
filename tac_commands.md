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
- %t1 = load (tb, ti, ns, no)
- store %t1, (tb, ti, ns, no)  
=> Commands suggested by TD
- %t1 = ref %t2   
=> Encodes the & operator
- %t1 = alloc %t2
- zero_out (%tb, num_bytes)   
=> Refer to runtime c functions
