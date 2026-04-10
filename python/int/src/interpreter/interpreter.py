"""
This module contains the main logic of the interpreter.

IPP: You must definitely modify this file. Bend it to your will.

Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
Author: Rastislav Uhliar <xuhliar00@stud.fit.vutbr.cz>
"""

import logging
import sys
from pathlib import Path
from typing import TextIO

from lxml import etree
from lxml.etree import ParseError
from pydantic import ValidationError

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError
from interpreter.input_model import Block, Program

from .sol_classes import RuntimeBlock, RuntimeInstance, SOLClassObject, SOLInt, SOLString

logger = logging.getLogger(__name__)


class Interpreter:
    """
    The main interpreter class, responsible for loading the source file and executing the program.
    """

    def __init__(self) -> None:
        self.current_program: Program | None = None
        self.environment: dict[str, object] = {}
        self.classes: dict[str, type] = {}
        self.stack: list[dict[str, object]] = []
        self.parameter_stack: list[set[str]] = []

    def load_program(self, source_file_path: Path) -> None:
        """
        Reads the source SOL-XML file and stores it as the target program for this interpreter.
        If any program was previously loaded, it is replaced by the new one.

        IPP: If you wish to run static checks on the program before execution, this is a good place
             to call them from.
        """
        logger.info("Opening source file: %s", source_file_path)
        try:
            xml_tree = etree.parse(source_file_path)
        except ParseError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_XML, message="Error parsing input XML"
            ) from e
        try:
            self.current_program = Program.from_xml_tree(xml_tree.getroot())
        except ValidationError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="Invalid SOL-XML structure"
            ) from e

    def execute(self, input_io: TextIO) -> None:
        """
        Executes the currently loaded program, using the provided input stream as standard input.
        """
        if self.current_program is None:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="No program loaded"
            )

        logger.info("Executing program")

        main_class = None
        for classes in self.current_program.classes:
            if classes.name == "Main":
                main_class = classes
                break

        if main_class is None:
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message="No Main class found in program"
            )

        run_method = None
        for method in main_class.methods:
            if method.selector == "run":
                run_method = method
                break
        if run_method is None:
            raise InterpreterError(
                error_code=ErrorCode.SEM_MAIN, message="No run method found in Main class"
            )

        self.build_class_table()

        main_instance = RuntimeInstance(main_class.name)
        self.frame_push(main_instance, [], [])
        original_stdin = sys.stdin
        # If user input is passed as argument, use it as stdin
        sys.stdin = input_io
        try:
            self.execute_block(run_method.block)
        finally:
            sys.stdin = original_stdin
            self.frame_pop()
        logger.debug("Program finished execution")

    def build_class_table(self) -> None:
        """
        Builds a class table
        """
        self.classes = {}

        for class_def in self.current_program.classes:
            self.classes[class_def.name] = class_def

    def lookup_method(self, class_name: str, selector: str):
        """
        Looks up a method in the classes table
        """
        class_def = self.classes.get(class_name)
        
        while class_def is not None:
            for method in class_def.methods:
                if method.selector == selector:
                    return method

            # If method was not found, try looking in the parent class
            class_def = self.classes.get(class_def.parent)

    def frame_push(self, receiver: object, parameters: list[str], arguments: list[object]) -> None:
        """
        Pushes a new frame to the stack
        """
        frame: dict[str, object] = {"self": receiver}

        for param, arg in zip(parameters, arguments):
            frame[param] = arg

        self.stack.append(frame)
        self.parameter_stack.append(set(parameters))

    def frame_pop(self) -> None:
        """
        Pops the frame from the stack
        """
        if self.stack:
            self.stack.pop()
        if self.parameter_stack:
            self.parameter_stack.pop()

    def is_parameter(self, name: str) -> bool:
        """
        Checks whether the given name belongs to the current frame parameters.
        """
        if not self.parameter_stack:
            return False

        return name in self.parameter_stack[-1]

    def stack_top(self) -> dict[str, object] | None:
        """
        Returns the top frame of the stack
        """
        if not self.stack:
            return None

        return self.stack[-1]

    def execute_runtime_block(self, block: Block, arguments: list[object]) -> object | None:
        """
        Executes a runtime block with argument-to-parameter binding.
        """
        parameter_names = [parameter.name for parameter in block.parameters]
        if len(arguments) != len(parameter_names):
            raise InterpreterError(
                error_code=ErrorCode.INT_DNU,
                message="Block called with wrong number of arguments",
            )

        current_frame = self.stack_top()
        receiver = current_frame.get("self") if current_frame is not None else RuntimeInstance("Object")

        self.frame_push(receiver, parameter_names, arguments)
        try:
            return self.execute_block(block)
        finally:
            self.frame_pop()

    def execute_block(self, block: Block) -> object | None:
        """
        Executes a block of code
        """
        logger.debug("Executing block with %d assignments", len(block.assigns))
        last_value: object | None = None
        for assign in block.assigns:
            logger.debug("Assignment #%d to %s", assign.order, assign.target.name or assign.target.send)
            eval_result = self.evaluate_expr(assign.expr)
            logger.debug("Result: %r", eval_result)
            last_value = eval_result

            target = assign.target
            if target.name is not None:
                var_name = target.name
                top_frame = self.stack_top()
                if top_frame is not None and self.is_parameter(var_name):
                    raise InterpreterError(
                        error_code=ErrorCode.SEM_COLLISION,
                        message=f"Assignment to method parameter '{var_name}' is not allowed",
                    )
                if top_frame is not None:
                    top_frame[var_name] = eval_result
                else:
                    self.environment[var_name] = eval_result
            elif target.send is not None:
                logger.debug("TODO implement send assignment for: %s", target.send)

        return last_value


    def evaluate_expr(self, expr) -> object:
        """
        Evaluates expression
        """
        if expr.literal is not None:
            logger.debug("Literal: %s(%s)", expr.literal.class_id, expr.literal.value)
            return self.evaluate_literal(expr.literal)
        if expr.block is not None:
            logger.debug("Block expression")
            return RuntimeBlock(self, expr.block)
        if expr.var is not None:
            var_name = expr.var.name
            top_frame = self.stack_top()
            if top_frame is not None and var_name in top_frame:
                var_value = top_frame[var_name]
                logger.debug("Variable (frame): %s = %r", var_name, var_value)
                return var_value
            if var_name in self.environment:
                var_value = self.environment[var_name]
                logger.debug("Variable: %s = %r", var_name, var_value)
                return var_value
            raise InterpreterError(
                error_code=ErrorCode.SEM_UNDEF,
                message=f"Variable '{var_name}' is not defined",
            )
        if expr.send is not None:
            logger.debug("Send: %s", expr.send.selector)
            return self.evaluate_send(expr.send)
        logger.debug("Unknown expression type")
        return None


    def evaluate_literal(self, literal) -> object:
        """
        Evaluates literal
        """
        if literal.class_id == "Integer":
            return SOLInt(int(literal.value))
        if literal.class_id == "String":
            return SOLString(literal.value)
        if literal.class_id == "class" and literal.value in {"Object", "Integer", "String"}:
            return SOLClassObject(literal.value)
        if literal.class_id == "class" and literal.value == "String":
            return SOLString("")

        logger.warning("Unknown literal class_id: %s", literal.class_id)
        return None

    def evaluate_send(self, send) -> object:
        """
        Evaluates send expression
        """
        receiver = self.evaluate_expr(send.receiver)
        args = [self.evaluate_expr(arg.expr) for arg in send.args]
        method_name = send.selector.rstrip(":") + "_method"

        logger.debug("%r.%s", receiver, send.selector)

        builtin_method = getattr(receiver, method_name, None)
        if builtin_method is not None:
            logger.debug("Calling built-in method %s with args %r", method_name, args)
            return builtin_method(*args)

        if not isinstance(receiver, RuntimeInstance):
            raise InterpreterError(
                error_code=ErrorCode.INT_DNU,
                message=f"Method '{send.selector}' not found on {receiver!r}",
            )

        method_def = self.lookup_method(receiver.class_name, send.selector)
        if method_def is None:
            is_setter = send.selector.endswith(":")
            if is_setter and len(args) == 1:
                attr_name = send.selector[:-1]
                if self.lookup_method(receiver.class_name, attr_name) is not None:
                    raise InterpreterError(
                        error_code=ErrorCode.INT_INST_ATTR,
                        message=f"Attribute '{attr_name}' collides with method",
                    )
                receiver.attributes[attr_name] = args[0]
                return args[0]

            if not is_setter and len(args) == 0 and send.selector in receiver.attributes:
                return receiver.attributes[send.selector]

            raise InterpreterError(
                error_code=ErrorCode.INT_DNU,
                message=f"Method '{send.selector}' not found on {receiver!r}",
            )

        if len(args) != len(method_def.block.parameters):
            raise InterpreterError(
                error_code=ErrorCode.SEM_ARITY,
                message=f"Method '{send.selector}' called with wrong number of arguments",
            )

        parameter_names = [parameter.name for parameter in method_def.block.parameters]
        self.frame_push(receiver, parameter_names, args)
        try:
            method_result = self.execute_block(method_def.block)
        finally:
            self.frame_pop()

        return method_result

