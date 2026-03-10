from __future__ import annotations


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

    def equalTo_method(self, other) -> bool:
        """
        Checks if integer is equal to other integer
        """
        return self.value == other.value

    def greaterThan_method(self, other) -> bool:
        """
        Checks if integer is greater than other integer
        """
        return self.value > other.value

    def plus_method(self, other) -> SOLInt:
        """
        Basic arithmetic operation
        Increments this integer by another
        """
        return SOLInt(self.value + other.value)

    def minus_method(self, other) -> SOLInt:
        """
        Decreses this integer by another
        """
        return SOLInt(self.value - other.value)

    def multiplyBy_method(self, other) -> SOLInt:
        """
        Multiplies this integer by another
        """
        return SOLInt(self.value * other.value)

    def devideBy_method(self, other) -> SOLInt:
        """
        Deviced this integer by another
        """
        if other.value == 0:
            print("Division by zero")
            raise ZeroDivisionError("Division by zero")
        return SOLInt(self.value / other.value)

    def asString_method(self) -> SOLString:
        """
        Returns this integer as SOLString
        """
        return SOLString(str(self.value))

    def asInteger_method(self) -> SOLInt:
        """
        Returns this integer
        """
        return self

    def timeRepeats_method(self, block) -> None:
        """
        While loop that repeats block of code
        """
        for value in range(self.value):
            print("Repeating block, iteration:", value)
            # TODO implement


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

    def read_method(self) -> SOLString:
        """
        Read user input and return it as SOLString
        """
        user_input = input()
        return SOLString(user_input)

    def print_method(self) -> None:
        """
        Print this string to standard output
        """
        print(self.value)

    def equalTo_method(self, other) -> bool:
        """
        Check if this string is equal to other string
        """
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

    def concatanateWith_method(self, other) -> SOLString:
        """
        Concatanates this string with another string annd returns the result as new SOLString
        """
        return SOLString(self.value + other.value)

    def startsWithEndsWith_method(self, other) -> bool:
        """
        Check if this string starts and ends with other string
        """
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
