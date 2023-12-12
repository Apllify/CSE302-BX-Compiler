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

            case StructType(attributes):
                for (a_name, a_type) in attributes : 
                    size += TypeSize.size(a_type)

            case _ : 
                raise ValueError("Input type must be resolved")
                

        return size