# --------------------------------------------------------------------
import contextlib as cl

from typing import Optional as Opt

from .bxast   import *
from .bxscope import Scope
from .bxtac   import *

# ====================================================================
# Maximal munch

class MM:
    _counter = -1

    PRINTS = {
        BasicType.INT  : 'print_int',
        BasicType.BOOL : 'print_bool',
    }

    def __init__(self):
        self._proc    = None
        self._tac     = []
        self._scope   = Scope()
        self._loops   = []

    tac = property(lambda self: self._tac)

    @staticmethod
    def mm(prgm: Program):
        mm = MM(); mm.for_program(prgm)
        return mm._tac

    @staticmethod 
    def get_type_size(type_ : Type): 
        """
        Compute and return the size of a type (in bytes)
        """
        size = 0

        match type_ : 
            case BasicType.INT : 
                size = 8
            case BasicType.BOOL : 
                size = 8
            case BasicType.NULL : 
                size = 8

            case PointerType(target):
                size = 8

            case ArrayType(target, size):
                size = MM.get_type_size(target) * size

            case _ : 
                assert(False)
                

        return size


    @classmethod
    def fresh_temporary(cls):
        cls._counter += 1
        return f'%{cls._counter}'

    @classmethod
    def fresh_label(cls):
        cls._counter += 1
        return f'.L{cls._counter}'

    def push(
            self,
            opcode     : str,
            *arguments : str | int,
            result     : Opt[str] = None,
    ):
        self._proc.tac.append(TAC(opcode, list(arguments), result))

    def push_label(self, label: str):
        self._proc.tac.append(f'{label}:')

    def push_load(self, store_reg : str, 
                        tb : str, 
                        no : int,
                        ti : Opt[str] = None, 
                        ns : Opt[int] = None, ):

        #tuple can either be length 2 or length 4
        if ti : 
            args = f"({tb}, {ti}, {ns}, {no})"
        else : 
            args = f"({tb}, {no})"

        self._proc.tac.append( TAC(opcode = "load", 
                                   result = store_reg, 
                                   arguments = [args]  ) )

    def push_store(self, value_reg : str, 
                         tb : str, 
                         no : int,
                         ti : Opt[str] = None, 
                         ns : Opt[int] = None, ) : 

        #tuple can either be length 2 or length 4
        if ti : 
            args = f"({tb}, {ti}, {ns}, {no})"
        else : 
            args = f"({tb}, {no})"

        self._proc.tac.append( TAC(opcode = "store", 
                                   arguments = [value_reg, args]  ) )


    @cl.contextmanager
    def in_loop(self, labels: tuple[str, str]):
        self._loops.append(labels)
        try:
            yield
        finally:
            self._loops.pop()

    def for_program(self, prgm: Program):
        for decl in prgm:
            match decl:
                case GlobVarDecl(name, init, type_):
                    assert(isinstance(init, IntExpression) or isinstance(init, BoolExpression))

                    #any boolean constant gets converted to an int 
                    self._tac.append(TACVar(name.value, int(init.value)))
                    self._scope.push(name.value, f'@{name.value}')
                        

        for decl in prgm:
            match decl:
                case ProcDecl(name, arguments, retty, body):
                    assert(self._proc is None)
                    with self._scope.in_subscope():
                        self._proc = TACProc(
                            name      = name.value,
                            arguments = [f'%{x[0].value}' for x in arguments],
                        )

                        for argument in arguments:
                            self._scope.push(argument[0].value, f'%{argument[0].value}')

                        self.for_statement(body)

                        if name.value == 'main':
                            self.for_statement(ReturnStatement(IntExpression(0)));

                        self._tac.append(self._proc)
                        self._proc = None

    def for_block(self, block: Block):
        with self._scope.in_subscope():
            for stmt in block:
                self.for_statement(stmt)

    def for_statement(self, stmt: Statement):
        match stmt:
            case VarDeclStatement(name, init, type):
                self._scope.push(name.value, self.fresh_temporary())

                if not isinstance(type, ArrayType):
                    temp = self.for_expression(init)
                    self.push('copy', temp, result = self._scope[name.value])
                else:  
                    #the array var only stores a pointer to the real array on stack
                    array_size = type.size * MM.get_type_size(type.target)
                    self.push("s_alloc", array_size, result = self._scope[name.value]) 
                    self.push("zero_out", f"({self._scope[name.value]}, {array_size})")

            case AssignStatement(lhs, rhs):
                self.for_assignment(lhs, rhs)

            case ExprStatement(expr):
                self.for_expression(expr)

            case PrintStatement(value):
                temp = self.for_expression(value)
                self.push('print', temp)

            case IfStatement(condition, then, else_):
                tlabel = self.fresh_label()
                flabel = self.fresh_label()
                olabel = self.fresh_label()

                self.for_bexpression(condition, tlabel, flabel)
                self.push_label(tlabel)
                self.for_statement(then)
                self.push('jmp', olabel)
                self.push_label(flabel)
                if else_ is not None:
                    self.for_statement(else_)
                self.push_label(olabel)

            case WhileStatement(condition, body):
                clabel = self.fresh_label()
                blabel = self.fresh_label()
                olabel = self.fresh_label()

                with self.in_loop((clabel, olabel)):
                    self.push_label(clabel)
                    self.for_bexpression(condition, blabel, olabel)
                    self.push_label(blabel)
                    self.for_statement(body)
                    self.push('jmp', clabel)
                    self.push_label(olabel)

            case ContinueStatement():
                self.push('jmp', self._loops[-1][0])

            case BreakStatement():
                self.push('jmp', self._loops[-1][1])

            case BlockStatement(body):
                self.for_block(body)

            case ReturnStatement(expr):
                if expr is None:
                    self.push('ret')
                else:
                    temp = self.for_expression(expr)
                    self.push('ret', temp)

            case _:
                assert(False)

    def for_assignment(self, lhs : Assignable, rhs : Expression):
        """
        Special munch case for assignments
        """
        rhs_val = self.for_expression(rhs)

        # handle non-variable assignments separately
        if isinstance(lhs, VarAssignable):
            self.push("copy", rhs_val, result = self._scope[lhs.name.value])
        else:
            lhs_address = self.store_elem_address(lhs)

            self.push_store(rhs_val, tb = lhs_address, no = 0)


    def for_expression(self, expr: Expression, force = False) -> str:
        target = None

        if not force and expr.type_ == BasicType.BOOL:
            target = self.fresh_temporary()
            tlabel = self.fresh_label()
            flabel = self.fresh_label()

            self.push('const', 0, result = target)
            self.for_bexpression(expr, tlabel, flabel)
            self.push_label(tlabel)
            self.push('const', 1, result = target)
            self.push_label(flabel)

        else:
            match expr:
                case VarAssignable(name):
                    target = self._scope[name.value]

                case IntExpression(value):
                    target = self.fresh_temporary()
                    self.push('const', value, result = target)
                
                case NullExpression():
                    target = self.fresh_temporary()
                    self.push("const", 0, result = target)

                case OpAppExpression(operator, arguments):
                    target    = self.fresh_temporary()
                    arguments = [self.for_expression(e) for e in arguments]
                    self.push(OPCODES[operator], *arguments, result = target)

                case CallExpression(proc, arguments):
                    for i, argument in enumerate(arguments):
                        temp = self.for_expression(argument)
                        self.push('param', i+1, temp)
                    if expr.type_ != BasicType.VOID:
                        target = self.fresh_temporary()
                    self.push('call', proc.value, len(arguments), result = target)

                case PrintExpression(argument):
                    temp = self.for_expression(argument)
                    self.push('param', 1, temp)
                    proc = self.PRINTS[argument.type_]
                    self.push('call', proc, 1)

                case DerefAssignable(argument) : 
                    assert(isinstance(argument.type_, PointerType))
                    address = self.for_expression(argument)
                    target = self.fresh_temporary()

                    self.push_load(target, tb = address, no = 0)

                case ArrayAssignable(_, _):
                    address = self.store_elem_address(expr)
                    target = self.fresh_temporary()
                    self.push_load(target, address, 0)

                case RefExpression(argument):
                    print("munching a ref WHAT")
                    target = self.store_elem_address(argument)
                    
                case _:
                    assert(False)

        return target


    def store_elem_address(self, elem : Assignable) -> str :
        """
        Computes the address of an assignable.
        Returns a register where that address is stored.
        """

        #iterate over class of elem
        match elem : 
            case VarAssignable(name) :
                target = self.fresh_temporary()

                var_reg = self._scope[name.value]
                self.push("ref", var_reg, result = target)

            case DerefAssignable(argument=sub_arg):
                target  = self.for_expression(sub_arg)

            case ArrayAssignable(argument = sub_arg, index=index):

                assert(isinstance(sub_arg.type_, ArrayType) or isinstance(sub_arg.type_, PointerType) )

                address_shift = self.for_expression(index)
                elem_size = MM.get_type_size(sub_arg.type_.target)

                #iterate over type of sub_arg
                match sub_arg.type_:
                    case PointerType(target = sub_target) :
                        base_address = self.for_expression(sub_arg)
                        
                    case ArrayType(target = sub_target, size = sub_size):
                        base_address = self.store_elem_address(sub_arg)

                total_shift = self.fresh_temporary()
                elem_size_reg = self.fresh_temporary()
                target = self.fresh_temporary() 
                self.push("const", elem_size, result = elem_size_reg)
                self.push("mul", address_shift, elem_size_reg, result = total_shift)
                self.push("copy", base_address, result = target)
                self.push("add", target, address_shift, result = target)

        return target


    CMP_JMP = {
        'cmp-equal'                 : 'jz',
        'cmp-not-equal'             : 'jnz',
        'cmp-lower-than'            : 'jgt',
        'cmp-lower-or-equal-than'   : 'jge',
        'cmp-greater-than'          : 'jlt',
        'cmp-greater-or-equal-than' : 'jle',
    }

    def for_bexpression(self, expr: Expression, tlabel: str, flabel: str):
        assert(expr.type_ == BasicType.BOOL)

        match expr:
            case VarAssignable(name):
                temp = self._scope[name.value]
                self.push('jz', temp, flabel)
                self.push('jmp', tlabel)

            case BoolExpression(True):
                self.push('jmp', tlabel)

            case BoolExpression(False):
                self.push('jmp', flabel)

            case OpAppExpression(
                    'cmp-equal'                |
                    'cmp-not-equal'            |
                    'cmp-lower-than'           |
                    'cmp-lower-or-equal-than'  |
                    'cmp-greater-than'         |
                    'cmp-greater-or-equal-than',
                    [e1, e2]):

                t1 = self.for_expression(e1)
                t2 = self.for_expression(e2)
                t  = self.fresh_temporary()
                self.push(OPCODES['subtraction'], t2, t1, result = t)

                self.push(self.CMP_JMP[expr.operator], t, tlabel)
                self.push('jmp', flabel)

            case OpAppExpression('boolean-and', [e1, e2]):
                olabel = self.fresh_label()
                self.for_bexpression(e1, olabel, flabel)
                self.push_label(olabel)
                self.for_bexpression(e2, tlabel, flabel)

            case OpAppExpression('boolean-or', [e1, e2]):
                olabel = self.fresh_label()
                self.for_bexpression(e1, tlabel, olabel)
                self.push_label(olabel)
                self.for_bexpression(e2, tlabel, flabel)

            case OpAppExpression('boolean-not', [e]):
                self.for_bexpression(e, flabel, tlabel)

            case CallExpression(_):
                temp = self.for_expression(expr, force = True)
                self.push('jz', temp, flabel)
                self.push('jmp', tlabel)

            case _:
                assert(False)
