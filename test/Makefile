# Makefile

# defaults
SIM ?= ghdl 
TOPLEVEL_LANG ?= vhdl

VHDL_SOURCES := $(shell /usr/bin/bender script flist)
$(info VHDL_SOURCES is "$(VHDL_SOURCES)")

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = static_uart_tx 

# MODULE is the basename of the Python test file
MODULE = my_test 

SIM_ARGS = -gBAUD_RATE=115200
ifeq ($(WAVE), 1)
	SIM_ARGS += --wave=$(SIM_BUILD)/wave.ghw
endif

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim