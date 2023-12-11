# --------------------------------------------------------------------
import contextlib as cl
import typing as tp

from .bxerrors  import Reporter
from .bxast     import *
from .bxscope   import Scope
from .bxtysizer import TypeSize

# ====================================================================
SigType    = tuple[tuple[Type], Opt[Type]]
ProcSigMap = dict[str, SigType]
TypedefMap = dict[str, Type]

# --------------------------------------------------------------------
class PreTyper:
    def __init__(self, reporter : Reporter):
        self.reporter = reporter

    def pretype(self, prgm : Program) -> tuple[Scope, ProcSigMap, TypedefMap]:
        scope = Scope()
        procs = dict()
        typedefs = dict()

        for topdecl in prgm:
            match topdecl:
                case ProcDecl(name, arguments, rettype, body):
                    if name.value in procs:
                        self.reporter(
                            f'duplicated procedure name: {name.value}',
                            position = name.position
                        )
                        continue

                    procs[name.value] = (
                        tuple(x[1] for x in arguments),
                        BasicType.VOID if rettype is None else rettype
                    )

                case GlobVarDecl(name, init, type_):
                    if name.value in scope:
                        self.reporter(
                            f'duplicated global variable name: {name.value}',
                            position = name.position
                        )
                        continue

                    scope.push(name.value, type_)

                case TypedefDecl(alias, original_type):
                    if alias.value in typedefs : 
                        self.reporter(
                            f"duplicated type definition: {alias.value}",
                            position = alias.position
                        ) 
                        continue
                
                    typedefs[alias] = original_type


                case _:
                    assert(False)

        if 'main' not in procs:
            self.reporter('this program is missing a main subroutine')
        elif procs['main'] != ((), BasicType.VOID):
            self.reporter(
                '"main" should not take any argument and should not return any value'
            )

        return scope, procs, typedefs

# --------------------------------------------------------------------
class TypeChecker:
    B : Type = BasicType.BOOL
    I : Type = BasicType.INT

    SIGS = {
        ('opposite',                  I)    : I,
        ('bitwise-negation',          B)    : I,
        ('boolean-not',               B)    : B,
        ('addition',                  I, I) : I,
        ('subtraction',               I, I) : I,
        ('multiplication',            I, I) : I,
        ('division',                  I, I) : I,
        ('modulus',                   I, I) : I,
        ('logical-right-shift',       I, I) : I,
        ('logical-left-shift',        I, I) : I,
        ('bitwise-and',               I, I) : I,
        ('bitwise-or',                I, I) : I,
        ('bitwise-xor',               I, I) : I, 
        ('boolean-and',               B, B) : B,
        ('boolean-or',                B, B) : B,
        ('cmp-equal',                 I, I) : B,
        ('cmp-not-equal',             I, I) : B,
        ('cmp-lower-than',            I, I) : B,
        ('cmp-lower-or-equal-than',   I, I) : B,
        ('cmp-greater-than',          I, I) : B,      
        ('cmp-greater-or-equal-than', I, I) : B,
    }

    def __init__(self, scope : Scope, procs : ProcSigMap, typedefs : TypedefMap, reporter : Reporter):
        self.scope    = scope
        self.procs    = procs
        self.typedefs = typedefs
        self.loops    = 0
        self.proc     = None
        self.reporter = reporter

    def report(self, msg: str, position: Opt[Range] = None):
        self.reporter(msg, position = position)

    @staticmethod
    def is_type_simple(type_ : Type):
        return isinstance(type_, BasicType) or isinstance(type_, PointerType)

    @staticmethod
    def op_signature(opname : str, arg_types: list[Type]) -> Type | None:
        """
        Returns the type signature of an operator application, given the
        types of its arguments
        """

        #try to check if this type sign is simple in form
        opkey = tuple([opname] + arg_types)
        all_hashable = all( isinstance(t, tp.Hashable) for t in  arg_types )

        if all_hashable and opkey in TypeChecker.SIGS:
            return TypeChecker.SIGS[opkey]
        else:  
            #any special cases for operator signatures
            match opkey :
                case ("cmp-equal", t1, t2) | ("cmp-not-equal", t1, t2):
                    is_pointer_comp = (
                                       (isinstance(t1, PointerType) and t1 == t2) or 

                                       (any(isinstance(t, PointerType) for t in arg_types)
                                        and BasicType.NULL in arg_types) or 

                                        (arg_types == [BasicType.NULL, BasicType.NULL])
                                      )
                        
                    if is_pointer_comp: 
                        return BasicType.BOOL


    @cl.contextmanager
    def in_loop(self):
        self.loops += 1
        try:
            yield self
        finally:
            self.loops -= 1

    @cl.contextmanager
    def in_proc(self, proc: ProcDecl):
        assert(self.proc is None)

        self.proc = proc
        self.scope.open()
        try:
            yield self
        finally:
            self.proc = None
            self.scope.close()

    def check_local_free(self, name : Name):
        if self.scope.islocal(name.value):
            self.report(f'duplicated variable declaration for {name.value}')
            return False
        return True

    def check_local_bound(self, name : Name):
        if name.value not in self.scope:
            self.report(
                f'missing variable declaration for {name.value}',
                position = name.position,
            )
            return None
        return self.scope[name.value]

    def check_integer_constant_range(self, value : int):
        if value not in range(-(1 << 63), 1 << 63):
            self.report(f'integer literal out of range: {value}')
            return False
        return True

    def resolve_type(self, type_ : Type) -> Type : 
        """
        Processes type info to make it into a format appropriate for the 
        muncher (only directly affects structs and type stand-ins)
        """

        #untouched types
        if isinstance(type_, BasicType): 
            return type_

        #special cases
        match type_ : 
            case PointerType(target):
                return PointerType(
                    target = self.resolve_type(target)
                )
            
            case ArrayType(target, size):
                return ArrayType(
                    target = self.resolve_type(target),
                    size = size
                )

            case StructType(attributes, attr_lookup):
                if attr_lookup is not None : 
                    return type_

                #compute the offsets and types for munch phase
                offset = 0
                type_.attr_lookup = dict()

                for (attr_name, attr_t) in attributes : 
                    real_t = self.resolve_type(attr_t)
                    type_.attr_lookup[attr_name] = (offset, real_t)
                    offset += TypeSize.size(real_t)

                return type_


            case StandinType(type_name):
                real_type = self.typedefs.get(type_name.value)

                if real_type is None : 
                    self.report(
                        f"Undefined type alias : {type_name.value}",
                        position = type_name.position
                    )
                    assert(False)

                return real_type

            case _ : 
                assert(False)
        

    def for_expression(self, expr : Expression, etype : tp.Optional[Type] = None):
        type_ = None

        match expr:
            case BoolExpression(_):
                type_ = BasicType.BOOL

            case IntExpression(value):
                self.check_integer_constant_range(value)
                type_ = BasicType.INT

            case NullExpression():
                #conform to any pointer type 
                if etype : 
                    if isinstance(etype, PointerType):
                        type_ = etype
                else : 
                    type_ = BasicType.NULL

            case OpAppExpression(opname, arguments):
                
                arg_types = []
                for arg in arguments: 
                    self.for_expression(arg)
                    arg_types.append(arg.type_)

                opsig = TypeChecker.op_signature(opname, arg_types)

                if not opsig :
                    arg_types_s = map(str, arg_types)
                    self.report(
                        f"""No variant of '{opname}' with type signature: 
                            {', '.join(arg_types_s)} -> <Output>""",
                        expr.position
                    )

                type_ = opsig

            case CallExpression(name, arguments):
                atypes, retty = [], None

                if name.value not in self.procs:
                    self.report(
                        f'unknown procedure: {name.value}',
                        position = name.position,
                    )
                else:
                    atypes, retty = self.procs[name.value]

                    if len(atypes) != len(arguments):
                        self.report(
                            f'invalid number of arguments: expected {len(atypes)}, got {len(arguments)}',
                            position = expr.position,
                        )

                for i, a in enumerate(arguments):
                    self.for_expression(a, atypes[i] if i in range(len(atypes)) else None)

                type_ = retty

            case PrintExpression(e):
                self.for_expression(e);

                if e.type_ is not None:
                    if e.type_ not in (BasicType.INT, BasicType.BOOL):
                        self.report(
                            f'can only print integers and booleans, not {e.type_}',
                            position = e.position,
                        )

                type_ = BasicType.VOID

            case AllocExpression(alloctype, size):
                real_alloctype = self.resolve_type(alloctype)
                expr.alloctype = real_alloctype
                self.for_expression(size, BasicType.INT)

                type_ = PointerType(real_alloctype)

            case RefExpression(argument):
                self.for_expression(argument)

                if argument.type_ == BasicType.NULL:
                    self.report(
                        "Cannot reference null pointer",
                        position = argument.position
                    )

                type_ = PointerType(argument.type_)


            case Assignable():
                self.for_assignable(expr)
                type_ = expr.type_
                

            case _:
                print(expr)
                assert(False)

        if type_ is not None:
            if etype is not None:
                if type_ != etype:
                    self.report(
                        f'invalid type: get {type_}, expected {etype}',
                        position = expr.position,
                    )

        expr.type_ = type_

    def for_assignable(self, assign : Assignable):
        """
        Computes and stores the type of an assignable object
        """
        type_ = None 

        match assign : 
            case VarAssignable(name):
                type_ = self.check_local_bound(name)

            case DerefAssignable(argument):
                self.for_expression(argument)

                if not isinstance(argument.type_, PointerType) :
                    self.report(
                        'cannot dereference non-pointer value',
                        position = assign.position,
                    )

                type_ = argument.type_.target


            case ArrayAssignable(argument, index):
                self.for_expression(argument)
                self.for_expression(index, BasicType.INT)

                correct_type = (isinstance(argument.type_, ArrayType) or 
                                isinstance(argument.type_, PointerType)) 
                if not correct_type:
                    self.report(
                        'can only index pointers and arrays',
                        position = assign.position,
                    )

                #check index within bounds for constant indexes
                if isinstance(argument.type_, ArrayType):
                    match index : 
                        case IntExpression(value):
                            if value not in range(0, argument.type_.size):
                                self.report(
                                    'array index out of bounds',
                                    position = assign.position
                                )


                type_ = argument.type_.target

            case AttributeAssignable(argument, attribute):
                self.for_expression(argument)
                if not isinstance(argument.type_, StructType):
                    self.report(
                        'illegal field access on non-struct type',
                        position = argument.position
                    )
                    return

                attr_entry = argument.type_.attr_lookup.get(attribute)

                if attr_entry is None : 
                    self.report(
                        'unrecognized struct field name',
                        position = argument.position
                    )
                else :
                    type_ = attr_entry[1]

            case _ : 
                self.report(
                    'unsupported assignable',
                    position = assign.position,
                )

        assign.type_ = type_

    def for_statement(self, stmt : Statement):
        match stmt:
            case VarDeclStatement(name, init, type_):
                real_type = self.resolve_type(type_)

                if self.check_local_free(name):
                    self.scope.push(name.value, real_type)

                #check zero initialization for arrays and struct
                if isinstance(real_type, ArrayType) or isinstance(real_type, StructType): 
                    self.for_expression(init)
                    
                    match init : 
                        case IntExpression(value = 0):
                            pass
                        case _ : 
                            self.report(
                                'arrays and structs can only be initialized with literal "0"',
                                position = stmt.position,
                            )                
                else: 
                    self.for_expression(init, etype = real_type)

            case AssignStatement(lhs, rhs):
                self.for_assignable(lhs)
                self.for_expression(rhs, etype = lhs.type_)

            case ExprStatement(expression):
                self.for_expression(expression)

            case BlockStatement(block):
                self.for_block(block)

            case IfStatement(condition, iftrue, iffalse):
                self.for_expression(condition, etype = BasicType.BOOL)
                self.for_statement(iftrue)
                if iffalse is not None:
                    self.for_statement(iffalse)

            case WhileStatement(condition, body):
                self.for_expression(condition, etype = BasicType.BOOL)
                with self.in_loop():
                    self.for_statement(body)

            case BreakStatement() | ContinueStatement():
                if self.loops == 0:
                    self.report(
                        'break/continue statement outside of a loop',
                        position = stmt.position,
                    )

            case PrintStatement(init):
                self.for_expression(init, etype = BasicType.INT)

            case ReturnStatement(e):
                if e is None:
                    if self.proc.rettype is not None:
                        self.report(
                            'value-less return statement in a function',
                            position = stmt.position,
                        )
                    self.for_expression(e, etype = self.proc.retty)
                else:
                    if self.proc.rettype is None:
                        self.report(
                            'return statement in a subroutine',
                            position = stmt.position,
                        )

            case _:
                print(stmt)
                assert(False)

    def for_block(self, block : Block):
        with self.scope.in_subscope():
            for stmt in block:
                self.for_statement(stmt)

    def for_topdecl(self, decl : TopDecl):
        match decl:
            case ProcDecl(name, arguments, retty, body):
                with self.in_proc(decl):

                    #can't have aggregate type arguments
                    for vname, vtype_ in arguments:
                        if not TypeChecker.is_type_simple(vtype_) : 
                            self.report(
                                "functions may only have non-aggregate type arguments",
                                position = decl.position
                            )

                        if self.check_local_free(vname):
                            self.scope.push(vname.value, self.resolve_type(vtype_))

                    self.for_statement(body)

                    #check existence and soundness of return value
                    if retty is not None:
                        if not TypeChecker.is_type_simple(retty) : 
                            self.report(
                                "functions may only have non-aggregate return types",
                                position = decl.position
                            )

                        if not self.has_return(body):
                            self.report(
                                'this function is missing a return statement',
                                position = decl.position,
                            )

            case GlobVarDecl(name, init, type_):
                self.for_expression(init, etype = type_)

                if not self.check_constant(init):
                    self.report(
                        'this expression is not a literal',
                        position = init.position,
                    )

    def for_program(self, prgm : Program):
        for decl in prgm:
            self.for_topdecl(decl)

    def check_constant(self, expr: Expression):
        match expr:
            case IntExpression(_):
                return True

            case BoolExpression(_):
                return True 

            case _:
                return False

    def has_return(self, stmt: Statement):
        match stmt:
            case ReturnStatement(_):
                return True

            case IfStatement(_, iftrue, iffalse):
                return \
                    self.has_return(iftrue) and \
                    self.has_return(iffalse)

            case BlockStatement(block):
                return any(self.has_return(b) for b in block)

            case _:
                return False

    def check(self, prgm : Program):
        self.for_program(prgm)

# --------------------------------------------------------------------
def check(prgm : Program, reporter : Reporter):
    with reporter.checkpoint() as checkpoint:
        scope, procs, typedefs = PreTyper(reporter).pretype(prgm)
        TypeChecker(scope, procs, typedefs, reporter).check(prgm)
        return bool(checkpoint)
