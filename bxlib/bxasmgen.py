# --------------------------------------------------------------------
import abc

from .bxtac import *

# --------------------------------------------------------------------
class AsmGen(abc.ABC):
    BACKENDS   = {}

    def __init__(self):
        self._tparams = dict()
        self._temps   = dict()
        self._current_index = 0 #represents the byte size of the stack divided by 8
        self._temp_sizes : dict[str, int] = dict() 

        self._asm     = []

    def set_temp_sizes(self, temp_sizes : dict[str, int]):
        self._temp_sizes = temp_sizes

    def _temp(self, temp):
        if temp.startswith('@'):
            return self._format_temp(temp[1:])
        if temp in self._tparams:
            return self._format_param(self._tparams[temp])
        
        temp_index = self._temps.get(temp)

        if temp_index is not None: 
            return self._format_temp(temp_index)
        else:
            temp_size = self._temp_sizes.get(temp)
            if temp_size is not None: 
                prev_index = self._current_index

                assert(temp_size % 8 == 0)
                self._current_index += temp_size // 8 #division by 8 :)
                
                self._temps[temp] = prev_index
                return self._format_temp(prev_index)
            else :
                prev_index = self._current_index

                self._current_index += 1 #division by 8 :)
                
                self._temps[temp] = prev_index
                return self._format_temp(prev_index)                
                # raise Exception("Key Error : temporary name couldn't be sized (in bxasmgen)")
            


    @abc.abstractmethod
    def _format_temp(self, index):
        pass

    @abc.abstractmethod
    def _format_param(self, index):
        pass

    def __call__(self, instr: TAC | str):
        if isinstance(instr, str):
            self._asm.append(instr)
            return

        opcode = instr.opcode
        args   = instr.arguments[:]

        if instr.result is not None:
            args.append(instr.result)

        getattr(self, f'_emit_{opcode}')(*args)

    def _get_asm(self, opcode, *args):
        if not args:
            return f'\t{opcode}'
        return f'\t{opcode}\t{", ".join(args)}'

    def _get_label(self, lbl):
        return f'{lbl}:'

    def _emit(self, opcode, *args):
        self._asm.append(self._get_asm(opcode, *args))

    def _emit_label(self, lbl):
        self._asm.append(self._get_label(lbl))

    @classmethod
    def get_backend(cls, name):
        return cls.BACKENDS[name]

# --------------------------------------------------------------------
class AsmGen_x64_Linux(AsmGen):
    PARAMS = ['%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']

    def __init__(self):
        super().__init__()
        self._params = []
        self._endlbl = None

    def _format_temp(self, index):
        if isinstance(index, str):
            return f'{index}(%rip)'
        return f'-{8*(index+1)}(%rbp)'

    def _format_param(self, index):
        return f'{8*(index+2)}(%rbp)'

    def _emit_const(self, ctt, dst):
        self._emit('movq', f'${ctt}', self._temp(dst))

    def _emit_copy(self, src, dst):
        self._emit('movq', self._temp(src), '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_alu1(self, opcode, src, dst):
        self._emit('movq', self._temp(src), '%r11')
        self._emit(opcode, '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_neg(self, src, dst):
        self._emit_alu1('negq', src, dst)

    def _emit_not(self, src, dst):
        self._emit_alu1('notq', src, dst)

    def _emit_alu2(self, opcode, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%r11')
        self._emit(opcode, self._temp(op2), '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_add(self, op1, op2, dst):
        self._emit_alu2('addq', op1, op2, dst)

    def _emit_sub(self, op1, op2, dst):
        self._emit_alu2('subq', op1, op2, dst)

    def _emit_mul(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%rax')
        self._emit('imulq', self._temp(op2))
        self._emit('movq', '%rax', self._temp(dst))

    def _emit_div(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%rax')
        self._emit('cqto')
        self._emit('idivq', self._temp(op2))
        self._emit('movq', '%rax', self._temp(dst))

    def _emit_mod(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%rax')
        self._emit('cqto')
        self._emit('idivq', self._temp(op2))
        self._emit('movq', '%rdx', self._temp(dst))

    def _emit_and(self, op1, op2, dst):
        self._emit_alu2('andq', op1, op2, dst)

    def _emit_or(self, op1, op2, dst):
        self._emit_alu2('orq', op1, op2, dst)

    def _emit_xor(self, op1, op2, dst):
        self._emit_alu2('xorq', op1, op2, dst)

    def _emit_shl(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%r11')
        self._emit('movq', self._temp(op2), '%rcx')
        self._emit('salq', '%cl', '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_shr(self, op1, op2, dst):
        self._emit('movq', self._temp(op1), '%r11')
        self._emit('movq', self._temp(op2), '%rcx')
        self._emit('sarq', '%cl', '%r11')
        self._emit('movq', '%r11', self._temp(dst))

    def _emit_print(self, arg):
        self._emit('leaq', '.lprintfmt(%rip)', '%rdi')
        self._emit('movq', self._temp(arg), '%rsi')
        self._emit('xorq', '%rax', '%rax')
        self._emit('callq', 'printf@PLT')

    def _emit_jmp(self, lbl):
        self._emit('jmp', lbl)

    def _emit_cjmp(self, cd, op, lbl):
        self._emit('cmpq', '$0', self._temp(op))
        self._emit(cd, lbl)

    def _emit_jz(self, op, lbl):
        self._emit_cjmp('jz', op, lbl)

    def _emit_jnz(self, op, lbl):
        self._emit_cjmp('jnz', op, lbl)

    def _emit_jlt(self, op, lbl):
        self._emit_cjmp('jl', op, lbl)

    def _emit_jle(self, op, lbl):
        self._emit_cjmp('jle', op, lbl)

    def _emit_jgt(self, op, lbl):
        self._emit_cjmp('jg', op, lbl)

    def _emit_jge(self, op, lbl):
        self._emit_cjmp('jge', op, lbl)

    def _emit_param(self, i, arg):
        assert(len(self._params)+1 == i)
        self._params.append(arg)

    def _emit_call(self, lbl, arg, ret = None):
        assert(arg == len(self._params))

        for i, x in enumerate(self._params[:6]):
            self._emit('movq', self._temp(x), self.PARAMS[i])

        qarg = 0 if arg <= 6 else arg - 6

        if qarg & 0x1:
            self._emit('subq', '$8', '%rsp')

        for x in self._params[6:][::-1]:
            self._emit('pushq', self._temp(x))

        self._emit('callq', lbl)

        if qarg > 0:
            self._emit('addq', f'${qarg + qarg & 0x1}', '%rsp')

        if ret is not None:
            self._emit('movq', '%rax', self._temp(ret))

        self._params = []

    def _emit_ret(self, ret = None):
        if ret is not None:
            self._emit('movq', self._temp(ret), '%rax')
        self._emit('jmp', self._endlbl)

    def _emit_load(self, address_temp, dest):
        self._emit("movq", self._temp(address_temp), '%rax')
        self._emit("movq", f"(%rax)", "%rbx")
        self._emit("movq", "%rbx", self._temp(dest))
        
    def _emit_store(self, value_temp, address_temp):
        self._emit("movq", self._temp(value_temp), "%rax")
        self._emit("movq", self._temp(address_temp), "%rbx")
        self._emit("movq", "%rbx", f"(%rax)")

    def _emit_ref(self, refed, dest):
        #store the address of the referenced temp in dest
        self._emit("leaq", self._temp(refed), "%rax")
        self._emit("movq", "%rax", self._temp(dest))

    def _emit_alloc(self, bcount : str, bsize : int, dest):
        #use runtime malloc
        self._emit('xorq', '%rax', '%rax')
        self._emit("movq", self._temp(bcount), "%rdi")
        self._emit("movq", f"${bsize}", "%rsi")
        self._emit("callq", "alloc")
        self._emit("movq", "%rax", self._temp(dest))


    def _emit_zero_out(self, address_temp : str, nbytes : int):
        self._emit("xorq", "%rax", "%rax")
        self._emit("movq", self._temp(address_temp), "%rdi")
        self._emit("movq", f"${nbytes}", "%rsi")
        self._emit("callq", "zero_out")

    def _emit_copy_array(self, dest : str, src : str, nbytes : int):
        self._emit("xorq", "%rax", "%rax")
        self._emit("movq", self._temp(dest), "%rdi")
        self._emit("movq", self._temp(src), "%rsi")
        self._emit("movq", f"${nbytes}", "%rdx")
        self._emit("callq", "copy_array")

    
    @classmethod
    def lower1(cls, tac: TACProc | TACVar) -> list[str]:
        emitter = cls()

        match tac:
            case TACVar(name, init):
                emitter._emit('.data')
                emitter._emit('.globl', name)
                emitter._emit_label(name)
                emitter._emit('.quad', str(init))

                return emitter._asm

            case TACProc(name, arguments, ptac):
                emitter._endlbl = f'.E_{name}'
                emitter.set_temp_sizes(tac.temp_sizes)

                for i in range(min(6, len(arguments))):
                    emitter._emit('movq', emitter.PARAMS[i], emitter._temp(arguments[i]))

                for i, arg in enumerate(arguments[6:]):
                    emitter._tparams[arg] = i

                for instr in ptac:
                    emitter(instr)

                nvars  = len(emitter._temps)

                nvars += nvars & 1

                return [
                    emitter._get_asm('.text'),
                    emitter._get_asm('.globl', name),
                    emitter._get_label(name),
                    emitter._get_asm('pushq', '%rbp'),
                    emitter._get_asm('movq', '%rsp', '%rbp'),
                    emitter._get_asm('subq', f'${8*nvars}', '%rsp'),
                ] + emitter._asm + [
                    emitter._get_label(emitter._endlbl),
                    emitter._get_asm('movq', '%rbp', '%rsp'),
                    emitter._get_asm('popq', '%rbp'),
                    emitter._get_asm('retq'),
                ]

    @classmethod
    def lower(cls, tacs: list[TACProc | TACVar]) -> str:
        aout = [cls.lower1(tac) for tac in tacs]
        aout = [x for tac in aout for x in tac]
        return "\n".join(aout) + "\n"

AsmGen.BACKENDS['x64-linux'] = AsmGen_x64_Linux
