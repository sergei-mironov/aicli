CMD_HELP = "/help"
CMD_ASK  = "/ask"
CMD_EXIT = "/exit"
CMD_ECHO = "/echo"
CMD_MODEL = "/model"
CMD_NTHREADS = "/nthreads"
CMD_RESET = "/reset"

COMMANDS = [CMD_HELP, CMD_EXIT, CMD_ASK, CMD_ECHO, CMD_MODEL, CMD_NTHREADS, CMD_RESET]

CMDNAMES = r'|'.join(set(COMMANDS)-{CMD_ECHO,CMD_MODEL,CMD_NTHREADS}).replace('/','\\/')

GRAMMAR = fr"""
  start: (command | escape | text)? (command | escape | text)*
  escape.3: /\\./
  command.2: /{CMDNAMES}/ | \
             /\/model/ / +/ string | \
             /\/nthreads/ / +/ number | \
             /\/echo/ | /\/echo/ / /
  string: /"[^\"]+"/ | /""/
  number: /[1-9][0-9]*/
  text: /(.(?!\/|\\))*./s
"""
