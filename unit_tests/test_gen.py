import random

def make_main(commands):
    """
    Return the starting line and ending line of any program
    """

    return ["def main(){"] + commands + ["}"]

def pointer_decl(output_file):
    """
    Outputs many pointer var declarations
    """
    output = []

    t1 = "int"
    t2 = "bool"

    for i in range(50):
        output.append(f"\tvar x{i} = null : {t1};")
        output.append(f"\tvar y{i} = null : {t2};")

        t1 += "*"
        t2 += "*"

    with open(output_file, "w") as file : 
        file.write("\n".join(make_main(output)))



def pointer_assign(output_file):
    """
    Outputs many pointer assignments
    """

    output = []
    var_names = [f"a{i}" for i in range(50)]
    star_suffix = ""

    #define many dummy ints 
    for var_name in var_names:  
        output.append(f"\tvar {var_name} = {random.randint(2, 2**16)} : int;")


    #define pointers to those dummy vars
    for i in range(20):
        
        output.append("\n\n")
        star_suffix += "*"

        for var_name in var_names : 
            output.append(f"\tvar {var_name}{'p' * (i+1)} = &{var_name}{'p' * (len(star_suffix) -1)} : int{star_suffix};")

    with open(output_file, "w") as file : 
        file.write("\n".join(make_main(output)))



#generate all of the unit tests
if __name__ == "__main__":
    pointer_decl("pointer_decl.bx")
    pointer_assign("pointer_assign.bx")