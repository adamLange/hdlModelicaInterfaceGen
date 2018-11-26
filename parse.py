#!/usr/bin/env python

import jinja2

import argparse

import json

from math import log,ceil

from subprocess import run

class Port:

    """
    Needed parameters:

    modelica_type
    interface_type
    name
    index_slug
    """
    def __init__(self,cosimulation_interface,d,index):
        self.d = d

        self.index = index
        self.cosimulation_interface = cosimulation_interface

        self.width = d["width"]

        if d["direction"] == "input":
            self.direction = "input"
        elif d["direction"] == "output":
            self.direction = "output"
        else:
            raise Warning("not input!, not output!")

        if (d["width"] == 1) or None:
            self.index_slug = ""
        else:
            self.index_slug = "[{}]".format(d["width"])

        if d["type"] == "Real":
            self.modelica_type = "Real"
            if d["direction"] == "input":
                self.interface_type = "RealInput"
            elif d["direction"] == "output":
                self.interface_type = "RealOutput"
            else:
                raise Warning("not input!, not output!")

        if d["type"] == "Boolean":
            self.modelica_type = "Boolean"
            if d["direction"] == "input":
                self.interface_type = "BooleanInput"
            elif d["direction"] == "output":
                self.interface_type = "BooleanOutput"
            else:
                raise Warning("not input!, not output!")

        self.name = d["name"]


    @property
    def y_position(self):
      if self.direction == "input":
        nPorts = len(self.cosimulation_interface.inputPorts)
      else: #output
        nPorts = len(self.cosimulation_interface.outputPorts)

      if nPorts == 1:
        return 0

      delta_y = 40
      b = - delta_y * (nPorts - 1) / 2
      y = delta_y * self.index + b

      return y

    @property
    def output_struct_member(self):
        if self.d["type"] == "Real":
            return "double {}[{}];".format(self.name,self.cosimulation_interface.event_queue_max_depth*self.d["width"])
        if self.d["type"] == "Boolean":
            numCharRequired = ceil(self.d["width"]/8)*self.cosimulation_interface.event_queue_max_depth
            return "char {}[{}];".format(self.name,numCharRequired)

    @property
    def input_struct_member(self):
        if self.d["type"] == "Real":
            if self.d["width"] > 1:
                s = "int32_t {}[{}];".format(self.name,self.d["width"])
            else:
                s = "int32_t {};".format(self.name)
            return s

        if self.d["type"] == "Boolean":
            numCharRequired = ceil(self.d["width"]/8)
            if self.d["width"] > 1:
                s =  "char {}[{}];".format(self.name,numCharRequired)
            else:
                s =  "char {};".format(self.name)
            return s

    @property
    def input_update_argument(self):
        if self.d["type"] == "Real":
            if self.d["width"] > 1:
                s = "double *{}".format(self.name)
            else:
                s = "double {}".format(self.name)
            return s

        if self.d["type"] == "Boolean":
            raise Warning("Boolean modelica input not implemented")

    @property
    def digitization_code_snippet(self):
        return self.d["digitization_code_snippet"]

    @property
    def send_c(self):
        context = {"port":self,
                   "num_bytes":self.width*4}
        t = self.cosimulation_interface.env.get_template('real_send.c.tmpl')
        return t.render(**context)

    @property
    def getNextEventValues_argument(self):
        raise Warning( "not implemented in Port base class")

    @property
    def getNextEventValues_assignment(self):
        raise Warning( "not implemented in Port base class")

    @property
    def serialized_size(self):
        raise Warning( "not implemented in Port base class")

    @property
    def pack_string(self):
        raise Warning( "not implemented in Port base class")

class BooleanPort(Port):

  def __init__(self,cosimulation_interface,d,index):
      super().__init__(cosimulation_interface,d,index)
      self.numStructElementsPerEvent = ceil(self.d["width"]/8)

  @property
  def serialized_size(self):
     return self.numStructElementsPerEvent

  @property
  def getNextEventValues_argument(self):
    s = "char *{}".format(self.d["name"])
    return s

  @property
  def output_struct_member(self):
      numCharRequired = ceil(self.d["width"]/8)*self.cosimulation_interface.event_queue_max_depth
      return "char {}[{}];".format(self.name,numCharRequired)

  @property
  def getNextEventValues_assignment(self):
      if self.d["width"] == 1:
        return "*{0} = (obj->{0});".format(self.d["name"])
      else:
        s = ""
        for i in range(self.d["width"]):
          char_index = int(i/8)
          bit_index = i%8
          s += "{}[{}] = (obj->{}[obj->eventIndex*{}+{}] >> {} ) & 1;\n  ".format(
            self.d["name"],
            i,
            self.d["name"],
            self.numStructElementsPerEvent,
            char_index,
            bit_index
            )
        return s

  @property
  def modelicaGetNextOutputValuesArgument(self):
    if self.d["width"] == 1:
      s = "output Boolean {};".format(self.d["name"])
    else:
      s = "output Boolean {} [{}];".format(self.d["name"],self.d["width"])
    return s

  @property
  def pack_recieved_output_event_values(self):
    s = ""
    for i in range(self.numStructElementsPerEvent):
      s += "obj->{}[i*{}+{}] = cmdData.{}[i*{}+{}];".format(
           self.d["name"],self.numStructElementsPerEvent,i,
           self.d["name"],self.numStructElementsPerEvent,i)
      if i < self.numStructElementsPerEvent - 1:
        s += "\n    ".format(self.d["name"],i)
    return s

  @property
  def pack_string(self):
    return "c"

  @property
  def output_struct_pack_string(self):
    return "{}".format(self.cosimulation_interface.event_queue_max_depth*self.serialized_size) + "c"

  @property
  def recv_c(self):
    context = {"port":self,
               "num_bytes":self.numStructElementsPerEvent\
                   *self.cosimulation_interface.event_queue_max_depth}
    t = self.cosimulation_interface.env.get_template('boolean_recv.c.tmpl')
    return t.render(**context)

class RealPort(Port):

  def __init__(self,cosimulation_interface,d,index):
    super().__init__(cosimulation_interface,d,index)

  @property
  def serialized_size(self):
     return 4

  @property
  def modelica_update_function_argument(self):

    if self.direction == "output":
      raise Warning("Calling modelica_update_function_argument on an output of the modelica interface block!")

    if self.d["width"] == 1:
      s = "input Real {};".format(self.d["name"])
    else:
      s = "input Real {}[{}];".format(self.d["name"],self.d["width"])
    return s

  @property
  def pack_string(self):
    return "i"

class CosimulationInterface:

    def __init__(self,inputDict):
        self.inputDict = inputDict
        self.event_queue_max_depth = inputDict["event_queue_max_depth"]
        self.inputPorts = []
        self.outputPorts = []
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(inputDict["template_directory"]),
                            lstrip_blocks=True,
                            trim_blocks=True
                            )

    def addInputPort(self,d):
        index = len(self.inputPorts)
        if d["type"] == "Boolean":
          self.inputPorts.append(BooleanPort(self,d,index))
        elif d["type"] == "Real":
          self.inputPorts.append(RealPort(self,d,index))
        else:
          self.inputPorts.append(Port(self,d,index))

    def addOutputPort(self,d):
        index = len(self.outputPorts)
        if d["type"] == "Boolean":
          self.outputPorts.append(BooleanPort(self,d,index))
        elif d["type"] == "Real":
          self.inputPorts.append(RealPort(self,d,index))
        else:
          self.outputPorts.append(Port(self,d,index))

    def generateTemplateFilling(self):
        return d

    @property
    def input_struct_size(self):
        size = 0
        for i in self.inputPorts:
          size += i.serialized_size
        return size

    @property
    def input_struct_unpack_string(self):
      s = ">"
      for i in self.inputPorts:
        s += i.pack_string
      return s

    @property
    def output_struct_pack_string(self):
      # the first i is for acqDeltaT (this tells modelica how long it should run)
      s = ">i"
      # pack the event delta T
      s += "{}i".format(self.event_queue_max_depth)
      for i in self.outputPorts:
        s += i.output_struct_pack_string
      return s

def main():

    parser =  argparse.ArgumentParser(description = "Creates a modelica-to-controller model interface")
    parser.add_argument("inFile",help="json file to parse")
    args = parser.parse_args()

    f = open(args.inFile)
    raw = f.read()
    f.close()
    inputDict = json.loads(raw)

    context = dict()

    #baseDir = os.environ["MODELICA_EXT_INTERFACE_GEN_TEMPLATE_DIR"]
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(inputDict["template_directory"]),
                            lstrip_blocks=True,
                            trim_blocks=True
                            )

    context = {}

    modelicaBlock = CosimulationInterface(inputDict)

    for key in inputDict:
      context[key] = inputDict[key]

    context["cosimulationInterface"] = modelicaBlock
    context["inputPorts"] = modelicaBlock.inputPorts
    context["outputPorts"] = modelicaBlock.outputPorts
    context["json_string"] = raw

    for i in inputDict["modelica_interface_block_inputs"]:
      i["direction"] = "input"
      modelicaBlock.addInputPort(i)

    for i in inputDict["modelica_interface_block_outputs"]:
      i["direction"] = "output"
      modelicaBlock.addOutputPort(i)

    t = env.get_template('ExternalInterface.mo.tmpl')
    out_f = open(inputDict["modelica_output_file"], 'w')
    out_f.write(t.render(**context))
    out_f.close()

    t = env.get_template('connectionObject.c.tmpl')
    out_f = open(inputDict["c_output_file"], 'w')
    out_f.write(t.render(**context))
    out_f.close()

    t = env.get_template('Makefile.tmpl')
    out_f = open(inputDict["makefile"], 'w')
    out_f.write(t.render(**context))
    out_f.close()

    t = env.get_template('ModelInterface.py.tmpl')
    out_f = open(inputDict["py_output_file"], 'w')
    out_f.write(t.render(**context))
    out_f.close()

    run(["make"])

if __name__=="__main__":

    main()
