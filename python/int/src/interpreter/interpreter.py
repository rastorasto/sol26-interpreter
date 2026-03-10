"""
This module contains the main logic of the interpreter.

IPP: You must definitely modify this file. Bend it to your will.

Author: Ondřej Ondryáš <iondryas@fit.vut.cz>
Author: Rastislav Uhliar <xuhliar00@stud.fit.vutbr.cz>
"""

import logging
from pathlib import Path
from typing import TextIO

from lxml import etree
from lxml.etree import ParseError
from pydantic import ValidationError

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError
from interpreter.input_model import Block, Program

from .sol_classes import SOLInt, SOLString

logger = logging.getLogger(__name__)


class Interpreter:
    """
    The main interpreter class, responsible for loading the source file and executing the program.
    """

    def __init__(self) -> None:
        self.current_program: Program | None = None
        # Variable storage maybe change for storing objects later or something TODO
        self.environment: dict[str, object] = {}

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
            self.current_program = Program.from_xml_tree(xml_tree.getroot())  # type: ignore
        except ValidationError as e:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="Invalid SOL-XML structure"
            ) from e

    def execute(self, input_io: TextIO) -> None:
        """
        Executes the currently loaded program, using the provided input stream as standard input.
        """
        # if self.current_program is None:
        #     raise InterpreterError(
        #         error_code=ErrorCode.INT_STRUCTURE, message="No program loaded"
        #     )

        logger.info("Executing program")

        for classes in self.current_program.classes:
            if classes.name == "Main":
                main_class = classes
                break

        if main_class is None:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="No Main class found in program"
            )

        for method in main_class.methods:
            if method.selector == "run":
                run_method = method
                break
        if run_method is None:
            raise InterpreterError(
                error_code=ErrorCode.INT_STRUCTURE, message="No run method found in Main class"
            )


        self.execute_block(run_method.block)
        logger.debug("Program finished execution")


    def execute_block(self, block: Block) -> None:
        """
        Executes a block of code
        """
        logger.debug("Executing block with %d assignments", len(block.assigns))
        for assign in block.assigns:
            logger.debug("Assignment #%d to %s", assign.order, assign.target.name or assign.target.send)
            eval_result = self.evaluate_expr(assign.expr)
            logger.debug("Result: %r", eval_result)

            target = assign.target
            if target.name is not None:
                var_name = target.name
                self.environment[var_name] = eval_result
            elif target.send is not None:
                logger.debug("TODO implement send assignment for: %s", target.send)


    def evaluate_expr(self, expr) -> object:
        """
        Evaluates expression
        """
        if expr.literal is not None:
            logger.debug("Literal: %s(%s)", expr.literal.class_id, expr.literal.value)
            return self.evaluate_literal(expr.literal)
        if expr.var is not None:
            var_name = expr.var.name
            if var_name in self.environment:
                var_value = self.environment[var_name]
                logger.debug("Variable: %s = %r", var_name, var_value)
                return var_value
            logger.debug("Variable '%s' not found!", var_name)
            return None
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

        logger.warning("Unknown literal class_id: %s", literal.class_id)
        return None

    def evaluate_send(self, send) -> object:
        """
        Evaluates send expression - dynamically dispatches methods
        """
        receiver = self.evaluate_expr(send.receiver)
        logger.debug("%r.%s", receiver, send.selector)

        method_name = send.selector.rstrip(':') + '_method'
        
        method = getattr(receiver, method_name, None)
        
        if method is None:
            logger.warning("Method '%s' not found on %r", send.selector, receiver)
            return None
        
        if len(send.args) > 0:
            args = [self.evaluate_expr(arg.expr) for arg in send.args]
            logger.debug("Method arguments %r", args)
            return method(*args)
        else:
            logger.debug("Method has no arguments")
            return method()

