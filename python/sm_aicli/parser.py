from lark import Lark
from .grammar import GRAMMAR

PARSER = Lark(GRAMMAR, start='start')
