from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict
from app.exceptions import ValidationError

class Operation(ABC):
    @abstractmethod
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        pass # pragma: no cover
    
    def validate_operands(self, a: Decimal, b: Decimal) -> None:
        pass

    def __str__(self) -> str:
        return self.__class__.__name__

class Addition(Operation):
    
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
       
        self.validate_operands(a, b)
        return a + b


class Subtraction(Operation):
   
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        
        self.validate_operands(a, b)
        return a - b


class Multiplication(Operation):
   
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        
        self.validate_operands(a, b)
        return a * b


class Division(Operation):
   

    def validate_operands(self, a: Decimal, b: Decimal) -> None:
       
        super().validate_operands(a, b)
        if b == 0:
            raise ValidationError("Division by zero is not allowed")

    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        
        self.validate_operands(a, b)
        return a / b


class Power(Operation):
   
    def validate_operands(self, a: Decimal, b: Decimal) -> None:
       
        super().validate_operands(a, b)
        if b < 0:
            raise ValidationError("Negative exponents not supported")

    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        
        self.validate_operands(a, b)
        return Decimal(pow(float(a), float(b)))


class Root(Operation):
   
    def validate_operands(self, a: Decimal, b: Decimal) -> None:
       
        super().validate_operands(a, b)
        if a < 0:
            raise ValidationError("Cannot calculate root of negative number")
        if b == 0:
            raise ValidationError("Zero root is undefined")

    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        
        self.validate_operands(a, b)
        return Decimal(pow(float(a), 1 / float(b)))


class OperationFactory:
   
    # Dictionary mapping operation identifiers to their corresponding classes
    _operations: Dict[str, type] = {
        'add': Addition,
        'subtract': Subtraction,
        'multiply': Multiplication,
        'divide': Division,
        'power': Power,
        'root': Root
    }

    @classmethod
    def register_operation(cls, name: str, operation_class: type) -> None:
      
        if not issubclass(operation_class, Operation):
            raise TypeError("Operation class must inherit from Operation")
        cls._operations[name.lower()] = operation_class

    @classmethod
    def create_operation(cls, operation_type: str) -> Operation:
       
        operation_class = cls._operations.get(operation_type.lower())
        if not operation_class:
            raise ValueError(f"Unknown operation: {operation_type}")
        return operation_class()