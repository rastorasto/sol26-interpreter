from __future__ import annotations

from interpreter.error_codes import ErrorCode
from interpreter.exceptions import InterpreterError


class RuntimeInstance:
    """
    Runtime class
    """
    def __init__(self, class_name: str):
        self.class_name = class_name
        self.attributes: dict[str, object] = {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class RuntimeBlock:
    """
    Runtime wrapper for SOL blocks.
    """

    def __init__(self, interpreter, block):
        self.interpreter = interpreter
        self.block = block

    def __repr__(self) -> str:
        return "RuntimeBlock()"

    def value_method(self, *args):
        return self.interpreter.execute_runtime_block(self.block, list(args))


class SOLClassObject:
    """
    Runtime receiver for class literals (e.g., Object, Integer, String).
    """

    def __init__(self, class_name: str):
        self.class_name = class_name

    def __repr__(self) -> str:
        return f"SOLClassObject({self.class_name})"

    def new_method(self) -> RuntimeInstance:
        return RuntimeInstance(self.class_name)

    def from_method(self, value) -> SOLInt:
        if self.class_name != "Integer":
            raise InterpreterError(ErrorCode.INT_DNU, f"Method 'from:' not found on class {self.class_name}")

        if isinstance(value, SOLInt):
            return SOLInt(value.value)

        raise InterpreterError(ErrorCode.INT_OTHER, "Integer from: expects Integer argument")

    def read_method(self) -> SOLString:
        if self.class_name != "String":
            raise InterpreterError(ErrorCode.INT_DNU, f"Method 'read' not found on class {self.class_name}")

        return SOLString(input())

class SOLObject:
    """
    Base class for objects
    """
    def __init__(self, class_name: str):
        self.class_name = class_name
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

class SOLInt(SOLObject):
    """
    Object for Integer
    """
    def __init__(self, value: int):
        super().__init__(class_name="Integer")
        self.value = value

    # def __str__(self) -> str:
    #     return str(self.value)
    
    def __repr__(self) -> str:
        return f"SOLInt({self.value})"

    def _require_int(self, other) -> SOLInt:
        if not isinstance(other, SOLInt):
            raise InterpreterError(ErrorCode.INT_OTHER, "Expected Integer argument")

        return other

    def equalTo_method(self, other) -> bool:
        """
        Checks if integer is equal to other integer
        """
        other = self._require_int(other)
        return self.value == other.value

    def greaterThan_method(self, other) -> bool:
        """
        Checks if integer is greater than other integer
        """
        other = self._require_int(other)
        return self.value > other.value

    def plus_method(self, other) -> SOLInt:
        """
        Basic arithmetic operation
        Increments this integer by another
        """
        other = self._require_int(other)
        return SOLInt(self.value + other.value)

    def minus_method(self, other) -> SOLInt:
        """
        Decreses this integer by another
        """
        other = self._require_int(other)
        return SOLInt(self.value - other.value)

    def multiplyBy_method(self, other) -> SOLInt:
        """
        Multiplies this integer by another
        """
        other = self._require_int(other)
        return SOLInt(self.value * other.value)

    def divBy_method(self, other) -> SOLInt:
        """
        Deviced this integer by another
        """
        other = self._require_int(other)
        if other.value == 0:
            raise InterpreterError(ErrorCode.INT_INVALID_ARG, "Division by zero")
        return SOLInt(self.value // other.value)

    def asString_method(self) -> SOLString:
        """
        Returns this integer as SOLString
        """
        return SOLString(str(self.value))

    def print_method(self) -> SOLInt:
        """
        Print this integer and return self.
        """
        print(self.value)
        return self

    def asInteger_method(self) -> SOLInt:
        """
        Returns this integer
        """
        return self

    def timesRepeat_method(self, block) -> SOLInt:
        """
        While loop that executes block
        """
        if not isinstance(block, RuntimeBlock):
            raise InterpreterError(ErrorCode.INT_OTHER, "timesRepeat: expects Block argument")

        for value in range(1, self.value + 1):
            block.value_method(SOLInt(value))

        return self


class SOLString(SOLObject):
    """
    Object for String
    """
    def __init__(self, value: str):
        super().__init__(class_name="String")
        self.value = value

    # def __str__(self) -> str:
    #     return self.value
    
    def __repr__(self) -> str:
        return f"SOLString({self.value!r})"

    def _require_string(self, other) -> SOLString:
        if not isinstance(other, SOLString):
            raise InterpreterError(ErrorCode.INT_OTHER, "Expected String argument")

        return other

    def read_method(self) -> SOLString:
        """
        Read user input and return it as SOLString
        """
        user_input = input()
        return SOLString(user_input)

    def print_method(self) -> SOLString:
        """
        Print this string to standard output and return self.
        """
        print(self.value)
        return self

    def equalTo_method(self, other) -> bool:
        """
        Check if this string is equal to other string
        """
        other = self._require_string(other)
        return self.value == other.value

    def asString_method(self) -> SOLString:
        """
        Return this string
        """
        return self

    def asInteger_method(self) -> SOLInt:
        """
        Converts this string to SOLInt and returns it
        """
        # TODO try passing something that cant be converted to see how it reacts :3
        return SOLInt(int(self.value))

    def concatenateWith_method(self, other) -> SOLString:
        """
        Concatanates this string with another string annd returns the result as new SOLString
        """
        other = self._require_string(other)
        return SOLString(self.value + other.value)

    def startsWithEndsWith_method(self, other) -> bool:
        """
        Check if this string starts and ends with other string
        """
        other = self._require_string(other)
        return self.value.startswith(other.value) and self.value.endswith(other.value)

    def length_method(self) -> SOLInt:
        """
        Returns length of this string
        """
        return SOLInt(len(self.value))

class TrueClass(SOLObject):
    def __init__(self):
        super().__init__(class_name="True")
        self.value = True

    def asString_method(self) -> SOLString:
        """
        Returns this boolean as SOLString
        """
        return SOLString("true")

    def not_method(self) -> FalseClass:
        """
        Negates this boolean
        """
        return FalseClass()

    def and_method(self, other) -> TrueClass:
        """
        Logical and
        """
        # TODO
        return

    def or_method(self, other) -> TrueClass:
        """
        Logical or
        """
        # TODO
        return

    def ifTrueifFalse_method(self, true_block, false_block) -> None:
        """
        If statement
        """
        # TODO
        return

    def isBoolean_method(self) -> TrueClass:
        """
        Checks if this object is boolean
        """
        # TODO maybe return self ? not sure
        return True

class FalseClass(SOLObject):
    def __init__(self):
        super().__init__(class_name="False")
        self.value = False

    def asString_method(self) -> SOLString:
        """
        Returns this boolean as SOLString
        """
        return SOLString("false")

    def not_method(self) -> TrueClass:
        """
        Negates this boolean
        """
        return TrueClass()

    def and_method(self, other) -> FalseClass:
        """
        Logical and
        """
        # TODO
        return

    def or_method(self, other) -> FalseClass:
        """
        Logical or
        """
        # TODO
        return

    def ifTrueifFalse_method(self, true_block, false_block) -> None:
        """
        If statement
        """
        # TODO
        return

    def isBoolean_method(self) -> TrueClass:
        """
        Checks if this object is boolean
        """
        # TODO maybe return self ? not sure
        return True
