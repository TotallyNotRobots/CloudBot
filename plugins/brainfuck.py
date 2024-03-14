"""brainfuck interpreter adapted from (public domain) code at
https://brainfuck.sourceforge.net/brain.py"""

import random
import re

from cloudbot import hook

BUFFER_SIZE = 5000
MAX_STEPS = 1000000


class UnbalancedBrackets(ValueError):
    pass


class BrainfuckProgram:
    def __init__(self, text):
        self.op_map = {
            "+": self.inc,
            "-": self.dec,
            ">": self.next_cell,
            "<": self.prev_cell,
            ".": self.print,
            ",": self.set_random,
            "[": self.loop_enter,
            "]": self.loop_exit,
        }

        self.ip = 0  # instruction pointer
        self.mp = 0  # memory pointer
        self.steps = 0
        self.memory = [0] * BUFFER_SIZE  # initial memory area
        self.rightmost = 0
        self.text = text
        self.program_size = len(text)
        self.output = ""
        self.bracket_map = self.populate_brackets()

    def populate_brackets(self):
        open_brackets = []
        bracket_map = {}
        for pos, c in enumerate(self.text):
            if c == "[":
                open_brackets.append(pos)
            elif c == "]":
                if not open_brackets:
                    raise UnbalancedBrackets()

                pos1 = open_brackets.pop()
                bracket_map[pos] = pos1
                bracket_map[pos1] = pos

        if open_brackets:
            raise UnbalancedBrackets()

        return bracket_map

    def grow_memory(self):
        self.memory.extend([0] * BUFFER_SIZE)

    def get(self):
        return self.memory[self.mp]

    def set(self, val):
        self.memory[self.mp] = val % 256
        return self.get()

    def set_random(self):
        return self.set(random.randrange(1, 256))

    def inc(self):
        self.set(self.get() + 1)

    def dec(self):
        self.set(self.get() - 1)

    def next_cell(self):
        self.mp += 1
        if self.mp > self.rightmost:
            self.rightmost = self.mp
            if self.mp >= len(self.memory):
                # no restriction on memory growth!
                self.grow_memory()

    def prev_cell(self):
        self.mp -= 1 % len(self.memory)

    def get_op(self, pos):
        return self.text[pos]

    def get_cur_op(self):
        return self.get_op(self.ip)

    def loop_enter(self):
        if self.get() == 0:
            self.ip = self.bracket_map[self.ip]

    def loop_exit(self):
        if self.get() != 0:
            self.ip = self.bracket_map[self.ip]

    def print(self):
        self.output += chr(self.get())


@hook.command("brainfuck", "bf")
def bf(text):
    """<prog> - executes <prog> as Brainfuck code"""

    program_text = re.sub(r"[^][<>+\-.,]", "", text)

    try:
        program = BrainfuckProgram(program_text)
    except UnbalancedBrackets:
        return "Unbalanced brackets"

    # the main program loop:
    while program.ip < program.program_size:
        program.op_map[program.get_cur_op()]()

        program.ip += 1
        program.steps += 1
        if program.steps > MAX_STEPS:
            if not program.output:
                program.output = "(no output)"

            program.output += "(exceeded {} iterations)".format(MAX_STEPS)
            break

    stripped_output = re.sub(r"[\x00-\x1F]", "", program.output)

    if not stripped_output:
        if program.output:
            return "No printable output"

        return "No output"

    return stripped_output[:430]
