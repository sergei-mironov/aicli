

def print_help():
  print(f"Commands: {' '.join(COMMANDS)}")

def print_aux(s:str)->None:
  print(f"INFO: {s}")

def print_aux_err(s:str)->None:
  print(f"ERROR: {s}")
