#!/usr/bin/env python

import argparse

def class_url(url_template, file_name, entity) -> str:
  line_number = None
  with open(file_name, 'r') as file:
    for i, line in enumerate(file, start=1):
      if f"class {entity}" in line.strip():
        line_number = i
        break
  if line_number is None:
    raise ValueError(f"Class '{entity}' not found in file '{file_name}'.")
  return url_template.replace("%L", str(line_number))

def typelink(entity, file_name):
  url_template = f'{file_name}#L%L'
  url = class_url(url_template, file_name, entity)
  return f"[{entity}]({url})"

def main(entities, file_name):
  print(' | '.join([typelink(x, file_name) for x in entities]))
  print()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Generate links for class references in a Python file.')
  parser.add_argument('entities', metavar='E', type=str, nargs='+',
                      help='entities to generate links for')
  parser.add_argument('--file', metavar='F', type=str, required=True,
                      help='path to the Python file to search for classes')

  args = parser.parse_args()
  main(args.entities, args.file)
