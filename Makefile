# -*- Makefile -*-

.PHONY: all clean

SOURCES := unit_tests/fact.bx
EXE := $(SOURCES:%.bx=%.exe)
OBJECTS := $(SOURCES:%.bx=%.o)
ASM := $(SOURCES:%.bx=%.s)

all: $(EXE)

%.exe: %.bx
	python3 bxc.py $<

clean:
	# rm -f $(EXE) $(OBJECTS) $(ASM)
	rm -f *.o *.s *.exe