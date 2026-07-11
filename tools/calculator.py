"""
CalculatorTool — implements AbstractTool. Pure Python, no external API.

Uses ast-based whitelisted evaluation instead of eval() to prevent
arbitrary code execution from user-supplied expressions.
"""

import ast
import operator
from typing import Any

from core.contracts import ToolName, ToolResult
from tools.base import AbstractTool
from utils.logger import get_logger

logger = get_logger(__name__)

# Whitelist: only these AST node types / operators are allowed to execute.
# Anything else (function calls, attribute access, imports, etc.) is rejected.
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,  # unary minus, e.g. -5
}


class CalculatorTool(AbstractTool):
    name = ToolName.CALCULATOR

    def execute(self, params: dict[str, Any], request_id: str) -> ToolResult:
        expression = params.get("expression", "")

        if not expression or not isinstance(expression, str):
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=False,
                error_message="No valid 'expression' provided",
            )

        try:
            result = self._safe_eval(expression)
            logger.info(f"[{request_id}] Calculator evaluated '{expression}' = {result}")
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=True,
                data={"expression": expression, "result": result},
            )
        except ZeroDivisionError:
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=False,
                error_message="Division by zero",
            )
        except (ValueError, SyntaxError, TypeError) as e:
            return ToolResult(
                request_id=request_id,
                tool_name=self.name,
                success=False,
                error_message=f"Invalid expression: {e}",
            )

    def _safe_eval(self, expression: str) -> float:
        """Parse expression into an AST and evaluate it, allowing ONLY
        whitelisted numeric operations. Rejects anything else (function
        calls, names, attribute access, imports, etc.) by raising ValueError."""
        node = ast.parse(expression, mode="eval").body
        return self._eval_node(node)

    def _eval_node(self, node: ast.AST):
        if isinstance(node, ast.Constant):  # a number literal
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Disallowed constant: {node.value!r}")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_OPERATORS:
                raise ValueError(f"Disallowed operator: {op_type.__name__}")
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return _ALLOWED_OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _ALLOWED_OPERATORS:
                raise ValueError(f"Disallowed unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand)
            return _ALLOWED_OPERATORS[op_type](operand)

        raise ValueError(f"Disallowed expression element: {type(node).__name__}")