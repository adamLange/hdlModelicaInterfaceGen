## Overview

An overview on the project: https://hackaday.io/project/161284-coupled-physics-and-fpga-simulation 

hdlModelicaInterfaceGen is a modelica to HDL cosimulation interface generator.  It currently supports
verilog to modelica coupling.

It works with any modelica tool as it uses the modelica standard external function interface.
cocotb is used on the hdl side.  The project could be extended to work with myHDL as well.

Invitation to join the project chatroom: https://discord.gg/qJcY5vd

## Usage

### 1. Create a json input file

See test.json for an example. You can put your input file wherever you want in your filesystem, 
just be sure to modify the variables in the input file to point back to the repo directory.

### 2. Run the parser script

  ~/yourProjectDirectory$ python3 pathToRepoDir/parse.py your_input_file.json

A few files will be generated:

  - .c and .so file. The .so file will get dynamically linked to the modelica tool.
  - .py file.  You need to import this module into you cocotb testbench.
  - .mo file.  You need to put this block into your modelica model.

### 3. Run the coupled simulation

  - Start the hdl simulation first; it is the server.
  - Start the modelica simulation.
  - Wait for the simulation to finish.

## TODO

  - Test (this is a buggy work in progress now)
  - Add more variable types. Now there only boolean outputs and real inputs (inputs and outputs as 
    viewed on the interface block diagram icon in modelica)
  - Expand on the documentation (there's this README and https://hackaday.io/project/161284-coupled-physics-and-fpga-simulation so far...)
  - Trim down the communication interface.  Now if you set the event queue depth to say 12, whether only
    3 events occur or 12, the number of bytes are sent across the network.
