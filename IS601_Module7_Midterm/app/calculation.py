from decimal import Decimal, InvalidOperation
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.exceptions import OperationError


class Calculation:
    """
    Represents a single calculation with operation, operands, result, and timestamp.
    """

    def __init__(self, operation: str, operand1: Decimal, operand2: Decimal):
        self.operation = operation
        self.operand1 = operand1
        self.operand2 = operand2
        self.timestamp = datetime.now()
        self.result = self._compute()

    def _compute(self) -> Decimal:
        """Execute the operation and return the result."""
        op = self.operation

        if op == "Addition":
            return self.operand1 + self.operand2

        elif op == "Subtraction":
            return self.operand1 - self.operand2

        elif op == "Multiplication":
            return self.operand1 * self.operand2

        elif op == "Division":
            if self.operand2 == 0:
                raise OperationError("Division by zero is not allowed")
            return self.operand1 / self.operand2

        elif op == "Power":
            if self.operand2 < 0:
                raise OperationError("Negative exponents are not supported")
            return self.operand1 ** self.operand2

        elif op == "Root":
            if self.operand1 < 0:
                raise OperationError("Cannot calculate root of negative number")
            return self.operand1 ** (Decimal("1") / self.operand2)

        else:
            raise OperationError(f"Unknown operation: {op}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the calculation to a dictionary."""
        return {
            "operation": self.operation,
            "operand1": str(self.operand1),
            "operand2": str(self.operand2),
            "result": str(self.result),
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Calculation":
        """Deserialize a Calculation from a dictionary."""
        try:
            operand1 = Decimal(str(data["operand1"]))
            operand2 = Decimal(str(data["operand2"]))
        except (InvalidOperation, KeyError) as e:
            raise OperationError(f"Invalid calculation data: {e}")

        calc = cls(
            operation=data["operation"],
            operand1=operand1,
            operand2=operand2,
        )

        # Restore original timestamp if present
        if "timestamp" in data:
            try:
                calc.timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass

        # Warn if saved result doesn't match computed result
        if "result" in data:
            try:
                saved_result = Decimal(str(data["result"]))
                if saved_result != calc.result:
                    logging.warning(
                        f"Loaded calculation result {saved_result} differs from "
                        f"computed result {calc.result}"
                    )
            except InvalidOperation:
                pass

        return calc

    def format_result(self, precision: int = 10) -> str:
        """Return the result formatted to the given decimal precision."""
        return str(round(self.result, precision))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Calculation):
            return NotImplemented
        return (
            self.operation == other.operation
            and self.operand1 == other.operand1
            and self.operand2 == other.operand2
            and self.result == other.result
        )

    def __repr__(self) -> str:
        return (
            f"Calculation(operation={self.operation!r}, "
            f"operand1={self.operand1}, operand2={self.operand2}, "
            f"result={self.result})"
        )