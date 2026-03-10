import ast
import operator

# Safe AST-based math evaluator

ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

ALLOWED_FUNCTIONS = {
    'max': max,
    'min': min,
    'round': round,
    'abs': abs,
}


class FormulaError(Exception):
    pass


def evaluate_formula(expression: str, variables: dict[str, float]) -> float:
    """Safely evaluate a math expression with variables.

    Allowed operators: +, -, *, /, **
    Allowed functions: max, min, round, abs
    Known variables: time, leader_time, position, participants, max_time
    """
    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError as e:
        raise FormulaError(f'Invalid formula syntax: {e}')

    return _eval_node(tree.body, variables)


def _eval_node(node, variables: dict[str, float]) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError(f'Unsupported constant type: {type(node.value)}')

    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        raise FormulaError(f'Unknown variable: {node.id}')

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPS:
            raise FormulaError(f'Unsupported operator: {op_type.__name__}')
        left = _eval_node(node.left, variables)
        right = _eval_node(node.right, variables)
        if op_type == ast.Div and right == 0:
            raise FormulaError('Division by zero')
        return ALLOWED_OPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in ALLOWED_OPS:
            raise FormulaError(f'Unsupported unary operator: {op_type.__name__}')
        operand = _eval_node(node.operand, variables)
        return ALLOWED_OPS[op_type](operand)

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaError('Only simple function calls are allowed')
        func_name = node.func.id
        if func_name not in ALLOWED_FUNCTIONS:
            raise FormulaError(f'Unknown function: {func_name}')
        args = [_eval_node(arg, variables) for arg in node.args]
        return float(ALLOWED_FUNCTIONS[func_name](*args))

    raise FormulaError(f'Unsupported expression type: {type(node).__name__}')
