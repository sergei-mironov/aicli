CMD_HELP = "/help"
CMD_ASK  = "/ask"
CMD_EXIT = "/exit"
CMD_ECHO = "/echo"
CMD_MODEL = "/model"
CMD_NTHREADS = "/nthreads"
CMD_RESET = "/reset"
CMD_TEMP = "/temp"
CMD_APIKEY = "/apikey"
CMD_VERBOSE = "/verbose"
CMD_IMG = "/img"

COMMANDS = [CMD_HELP, CMD_EXIT, CMD_ASK, CMD_ECHO, CMD_MODEL, CMD_NTHREADS, CMD_RESET, CMD_TEMP,
            CMD_APIKEY, CMD_IMG]
COMMANDS_ARG = [CMD_ECHO, CMD_MODEL, CMD_NTHREADS, CMD_TEMP, CMD_APIKEY, CMD_VERBOSE]
COMMANDS_NOARG = r'|'.join(sorted(list(set(COMMANDS)-set(COMMANDS_ARG)))).replace('/','\\/')

GRAMMAR = fr"""
  start: (command | escape | text)? (command | escape | text)*
  escape.3: /\\./
  command.2: /{COMMANDS_NOARG}/ | \
             /\/model/ / +/ (/"/ model_string /"/ | /"/ /"/) | \
             /\/apikey/ / +/ (/"/ apikey_string /"/ | /"/ /"/) | \
             /\/nthreads/ / +/ (number | def) | \
             /\/verbose/ / +/ (number | def) | \
             /\/temp/ / +/ (float | def ) | \
             /\/echo/
  model_string: (model_provider ":")? model_name
  model_provider: "gpt4all" -> mp_gpt4all | "openai" -> mp_openai | "dummy" -> mp_dummy
  model_name: /[^"]+/
  apikey_string: (apikey_schema ":")? apikey_value
  apikey_schema: "verbatim" -> as_verbatim | "file" -> as_file
  apikey_value: /[^"]+/
  number: /[0-9]+/
  float: /[0-9]+\.[0-9]*/
  def: "default"
  text: /(.(?!\/|\\))*./s
"""
