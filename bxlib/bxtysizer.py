from .bxast   import *

class TypeSize : 
    @staticmethod 
    def size(type_ : Type): 
        """
        Compute and return the size of a type (IN BYTES)
        Only accepts already RESOLVED types 
        """
        if isinstance(type_, BasicType):
            return 8

        size = 0

        match type_ : 
            case PointerType(target):
                size = 8

            case ArrayType(target, size):
                size = TypeSize.size(target) * size

            case _ : 
                assert(False)
                

        return size