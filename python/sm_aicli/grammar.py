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
CMD_PROMPT = "/prompt"
CMD_DBG = "/dbg"
CMD_EXPECT = "/expect"
CMD_IMGSZ = "/imgsz"

COMMANDS = [CMD_HELP, CMD_EXIT, CMD_ECHO, CMD_MODEL, CMD_NTHREADS, CMD_RESET, CMD_TEMP,
            CMD_APIKEY, CMD_IMG, CMD_PROMPT, CMD_DBG, CMD_ASK, CMD_IMGSZ]
COMMANDS_ARG = [CMD_MODEL, CMD_NTHREADS, CMD_TEMP, CMD_APIKEY, CMD_VERBOSE,
                CMD_EXPECT, CMD_IMGSZ, CMD_IMG]
COMMANDS_NOARG = r'|'.join(sorted(list(set(COMMANDS)-set(COMMANDS_ARG)))).replace('/','\\/')

GRAMMAR = fr"""
  start: (command | escape | text)? (command | escape | text)*
  escape.3: /\\./
  command.2: /{COMMANDS_NOARG}/ | \
             /\/model/ / +/ model_string | \
             /\/apikey/ / +/ apikey_string | \
             /\/nthreads/ / +/ (number | def) | \
             /\/verbose/ / +/ (number | def) | \
             /\/temp/ / +/ (float | def ) | \
             /\/expect/ / +/ modality_string | \
             /\/img/ / +/ string | \
             /\/imgsz/ / +/ string

  string: "\"" string_quoted "\"" | string_raw
  string_quoted: /[^"]+/ -> string_value
  string_raw: /[^"][^ ]*/ -> string_value

  model_string: "\"" model_quoted "\"" | model_raw
  model_quoted: (model_provider ":")? string_quoted -> model
  model_raw: (model_provider ":")? string_raw -> model
  model_provider: "gpt4all" -> mp_gpt4all | "openai" -> mp_openai | "dummy" -> mp_dummy

  modality_string: "\"" modality "\"" | modality
  modality: /img/ -> modality_img | /text/ -> modality_text

  apikey_string: "\"" apikey_quoted "\"" | apikey_raw
  apikey_quoted: (apikey_schema ":")? string_quoted -> apikey
  apikey_raw: (apikey_schema ":")? string_raw -> apikey
  apikey_schema: "verbatim" -> as_verbatim | "file" -> as_file

  number: /[0-9]+/
  float: /[0-9]+\.[0-9]*/
  def: "default"
  text.0: /(.(?!\/|\\))*./s
"""
