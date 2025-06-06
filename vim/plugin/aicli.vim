if exists("g:aicli_loaded")
  finish
endif

fun! AicliGetTempDir()
  " Get the system temporary files directory from $TMPDIR, $TEMP, or $TMP
  if exists('$TMPDIR')
    return $TMPDIR
  elseif exists('$TEMP')
    return $TEMP
  elseif exists('$TMP')
    return $TMP
  else
    return '/tmp'
  endif
endfun

if ! exists("g:aicli_errfile")
  let g:aicli_errfile = AicliGetTempDir() . '/aicli.err'
endif

if ! exists("g:aicli_script")
  let g:aicli_script = 'aicli-*.sh'
endif

if ! exists("g:aicli_plugin_version")
  let devroot = getenv('AICLI_ROOT')
  if ! empty(devroot)
    let g:aicli_plugin_version = substitute(
      \ system(devroot . '/python/aicli --version',''), "\n", "", 'g')
  else
    let g:aicli_plugin_version = 'version-to-be-filled-by-the-packager'
  endif
endif

fun! AicliGet(name)
  if exists('b:'.a:name)
    return get(b:, a:name, '')
  elseif exists('g:'.a:name)
    return get(g:, a:name, '')
  else
    return ''
  endif
endfun

fun! AicliCmdline(action, prompt, selmode, file, extras)
  let [action, prompt, selmode, file, extras] = [a:action, a:prompt,
        \ a:selmode, a:file, a:extras]
  let command = substitute(AicliGet('aicli_script'), '*', action, '')
  if prompt != '-'
    if len(trim(prompt)) == 0
      let prompt = input("Your question: ")
    endif
    if len(trim(prompt))>0
      let command = command . ' --prompt "'.prompt.'"'
    endif
  endif
  if len(selmode)>0 " 'raw' or 'paste'
    let command = command . ' --selection-'.selmode.' - '
  endif
  if &textwidth > 0
    let command = command . ' --textwidth '.string(&textwidth)
  endif
  if &filetype != ''
    let command = command . ' --output-format '.&filetype
  endif
  if len(file)>0
    let command = command . ' ' . file
  endif
  let errfile = AicliGet('aicli_errfile')
  let command = command . extras . ' 2>>'.errfile
  return command
endfun

fun! AicliGetVisualSelection() range
  " Get visual selection
  let [line_start, column_start] = getpos("'<")[1:2]
  let [line_end, column_end] = getpos("'>")[1:2]
  let lines = getline(line_start, line_end)
  if len(lines) == 0
    return ""
  endif
  let lines[-1] = lines[-1][: column_end - (&selection == 'inclusive' ? 1 : 2)]
  let lines[0] = lines[0][column_start - 1:]
  return join(lines, "\n")
endfun

fun! AicliReplace(action, prompt, source, selmode, file, extras) range " -> int
  let [action, prompt, source] = [a:action, a:prompt, a:source]
  let command = AicliCmdline(action, prompt, a:selmode, a:file, a:extras)
  let vimcommand = "silent! ".source."! ".command
  " echomsg vimcommand
  execute vimcommand
  let errcode = v:shell_error
  return errcode
endfun

fun! AicliReplaceFile(action, prompt, selmode, file) range " -> int
  return AicliReplace(a:action, a:prompt, "%", a:selmode, a:file, "")
endfun

fun! AicliPushSelection(action, prompt, selmode) range
  let [action, prompt] = [a:action, a:prompt]
  let command = AicliCmdline(action, prompt, a:selmode, "", "")
  let selection = AicliGetVisualSelection() . "\n"
  silent let result = system(command, selection)
  echom result
  let errcode = v:shell_error
  return errcode
endfun

fun! AicliPush(action, prompt, selmode) range
  let [action, prompt] = [a:action, a:prompt]
  let command = AicliCmdline(action, prompt, a:selmode, "", "")
  silent let result = system(command)
  echom result
  let errcode = v:shell_error
  return errcode
endfun

fun! AicliPull(action, prompt) range
  let [action, prompt] = [a:action, a:prompt]
  let command = AicliCmdline(action, prompt, "", "", "")
  silent execute 'r!'.command .'</dev/null'
  let errcode = v:shell_error
  return errcode
endfun

fun! AicliReplaceSelectionOrPull(action, prompt, selmode) range " -> int
  if len(a:selmode)>0
    return AicliReplace(a:action, a:prompt, "'<,'>", a:selmode, "", "--reindent")
  else
    return AicliPull(a:action, a:prompt)
  endif
endfun

fun! AicliTerminal() range
  execute "terminal litrepl repl ai"
  call feedkeys(" /cat out\n")
  return 0
endfun

fun! AicliPushSelectionOrPush(action, prompt, selmode) range " -> int
  if len(a:selmode)>0
    return AicliPushSelection(a:action, a:prompt, a:selmode)
  else
    return AicliPush(a:action, a:prompt, a:selmode)
  endif
endfun

fun! Arg0(line)
  " Split the line into words and return the first word
  return split(a:line)[0]
endfun

fun! ArgStar(line)
  let first_space_index = match(a:line, '\s')
  if first_space_index != -1
    return trim(a:line[first_space_index:])
  else
    return ''
  endif
endfun

fun! ArgSelMode(range, bang)
  if a:range != 0
    if a:bang == '!'
      return "raw"
    else
      return "paste"
    endif
  else
    return ""
  endif
endfun

fun! AicliCompletion(ArgLead, CmdLine, CursorPos)
  if a:CmdLine =~ '\<\w\+\>\s\<\w\+\>\s'
    return []
  endif
  let result = []
  let executables = globpath(substitute($PATH,':',',','g'), g:aicli_script, 1, 1, 1)
  for e in executables
    let matches = matchlist(fnamemodify(e, ':t'), substitute(g:aicli_script, '\*', '\\(.\\+\\)', ''))
    if len(matches)>=2
      call add(result, matches[1].' ')
    endif
  endfor
  return filter(result, 'v:val =~ "^".a:ArgLead')
endfun

if exists(":AI") != 2
  command! -complete=customlist,AicliCompletion -range -bar -nargs=* -bang AI
        \ call AicliReplaceSelectionOrPull(
        \        Arg0(<q-args>), ArgStar(<q-args>), ArgSelMode(<range>, "<bang>"))
endif

if !exists(":AIPush")
  command! -complete=customlist,AicliCompletion -range -bar -nargs=* -bang AIPush
        \ call AicliPushSelectionOrPush(Arg0(<q-args>), ArgStar(<q-args>),
        \        ArgSelMode(<range>, "<bang>"))
endif

if !exists(":AIFile")
  command! -complete=customlist,AicliCompletion -range -bar -nargs=* -bang AIFile
        \ call AicliReplaceFile(Arg0(<q-args>), ArgStar(<q-args>),
        \        ArgSelMode(<range>, "<bang>"), expand("%:p"))
endif

if !exists(":AITerm")
  command! -range -bar -nargs=0 AITerm call AicliTerminal()
endif

let g:aicli_loaded = 1
