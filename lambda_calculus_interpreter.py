import re

# global variable used to Alpha-reduce expressions with same variable name
HIGHEST = 0
EXPRS = []

class Token:
    """
    Base class for token types
    Essentially just for REPR to return name of which Token child instance it is
    """
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return self.__class__.__name__


class LParen(Token):
    """
    Left parenthesis Token
    """
    def __init__(self, text):
        super().__init__(text)


class RParen(Token):
    """
    Right parenthesis Token
    """
    def __init__(self, text):
        super().__init__(text)


class Lambda(Token):
    """
    lambda call ("L") Token
    """
    def __init__(self, text):
        super().__init__(text)


class VarToken(Token):
    """
    Token for any variable
    - Attribute VAL is the value or name of the variable
    """
    def __init__(self, text):
        super().__init__(text)
    def __repr__(self):
        """
        Give instance name, not class name
        :return: name/VAL of variable, not the name VarToken
        """
        return super().__repr__() + f': {self.text}'


class Whitespace(Token):
    """
    Whitespace token
    """
    def __init__(self, text):
        super().__init__(text)


class Period(Token):
    """
    Period Token
    """
    def __init__(self, text):
        super().__init__(text)


class Equals(Token):
    """
    Equal sign token
    """
    def __init__(self, text):
        super().__init__(text)


class Newline(Token):
    """
    New line Token
    """
    def __init__(self, text):
        super().__init__(text)


token_dict = {
    't_lambda': (r'L', Lambda),
    't_left_paren': (r'\(', LParen),
    't_right_paren': (r'\)', RParen),
    't_variable': (r'[a-z][a-zA-Z]*', VarToken),
    't_dot': (r'\.', Period),
    't_whitespace': (r' +', Whitespace),
    't_equals': (r'=', Equals),
    't_newline': (r'\n[\s]*', Newline)
}


def build_token_grabber():
    """
    Construct RegEx string for tokenizer
    :return: RegEx string for re.match based on all token types
    """
    dct = token_dict
    return r'^(' + '|'.join([ f'(?P<{k}>{dct[k][0]})' for k in dct ]) + ')'


def take_next_token(text: str) -> tuple:
    """
    Called many times in tokenize()
    Gets and creates token class instance of next closest token (space separated)

    :param text: Lambda Calculus source code
    :return: Next token, rest of code
    """
    # return token type (in terms of our string dict) of NEXT token
    match_result = re.match(build_token_grabber(), text)
    token_result = None

    if match_result is None:
        # nothing in the remainder of the file matched any token
        raise Exception("Lambda invalid syntax")

    # get token and get rest
    span = match_result.span()
    token = text[span[0]:span[1]]
    rest = text[span[1]:]

    dct = match_result.groupdict()
    for k in dct:
        mtch = dct[k]
        if mtch is None:
            continue
        token_result = token_dict[k][1](token)
    print(token_result)
    return token_result, rest


def tokenize(text: str):
    """
    Lexer of source code
    takes in raw text and spits out list of tokens

    :param text: Lambda Calculus source code
    :return: list of all tokens in the source code
    """
    tokens_list = []

    while len(text) > 0:
        tok, rest = take_next_token(text)
        tokens_list.append(tok)
        text = rest
    return tokens_list


class ExprNode:
    """
    base class of three kinds of Terms
    """
    def __init__(self):
        pass


class Variable(ExprNode):
    """
    Variable node (Ex. 'x')

    Attr NAME is the character/name/value of the variable
    """
    def __init__(self, variable_name: str):
        super().__init__()
        self.name = variable_name

    def __repr__(self):
        return self.name


class Abstraction(ExprNode):
    """
    Abstraction term node (Ex. 'Lx.Ly.x')

    Attr VARIABLE is the name of the bound variable (Ex. would be 'x')
    Attr EXPRESSION is the inner expression of function (Ex. would be Abstraction 'Ly.x')
    """
    def __init__(self, variable_name: str, exp: ExprNode):
        super().__init__()
        self.variable = variable_name
        self.expression = exp

    def __repr__(self):
        """
        Display the actual whole term (wrapped in parentheses)
        :return: "(Lx.Ly.x)"
        """
        return f'(L{self.variable}.{self.expression.__repr__()})'

    # def __str__(self):
    #     succ_var = self.variable
    #     x = 0
    #     for s in self.expression.__repr__():
    #         if s == succ_var:
    #             x += 1
    #     return str(x)


class Application(ExprNode):
    """
    Application term node (Ex. "x y", x applied to y)

    Attr FN is left term (the function or value being applied to the right) (Ex. 'x')
    Attr OPERAND is the right term (Ex. 'y')
    """
    def __init__(self, term_a: ExprNode, term_b: ExprNode):
        super().__init__()
        self.fn = term_a
        self.operand = term_b

    def __repr__(self):
        """
        Display the actual application of two terms (wrapped in parentheses)
        :return: '(x y)'
        """
        return f'({self.fn.__repr__()}) ({self.operand.__repr__()})'


class StmtNode:
    """
    Base class for a statement in a program
    can be an expression or an assignment
    OR a block of multiple Statements
    """
    def __init__(self):
        pass

    def __str__(self):
        return repr(self)


class ExprStmt(StmtNode):
    """
    A statement which is an expression, ie an application
    on a file, it is a non-assignment/definition statament
    """
    def __init__(self, expr_node: ExprNode):
        super().__init__()
        self.expr = expr_node

    def __repr__(self):
        return f"ExprStmt({repr(self.expr)})"


class AssignmentStmt(StmtNode):
    """
    Definition of a function with a name and expression value
    """
    def __init__(self, name: str, expr_node: ExprNode):
        super().__init__()
        self.name = name
        self.expr = expr_node

    def __repr__(self):
        return f"Assignment: {self.name} <--> {repr(self.expr)}"


class BlockStmt(StmtNode):
    """
    Multiple statements warrant a Block
    Block = Stmt, rest (can be another block or statement)
    """
    def __init__(self, stmt: StmtNode, rest: StmtNode):
        super().__init__()
        self.stmt = stmt
        self.rest = rest

    def __repr__(self):
        return f"(Block: {repr(self.stmt)}, \n\trest:{repr(self.rest)})"


class NullStmt(StmtNode):
    """
    useful Null statement class that does nothing
    """
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return 'NULL'


def parse_statement(token_list, depth):
    """
    Parse a statement out of tokens, in this stage subbing in NAMES of defined terms
    ie we define: zero = Ls.Lz.z  --> then when called, 'zero' will be in tree spot not expression
    :param token_list: List of tokens lexed from file
    :param depth: For printing, how many recursions are we in
    :return: Parsed SYNTAX TREE of entire file, with Statements and Blocks at highest level
                Also return rest during recursion, final should be []
    """
    try:
        print(f"PARSING: {token_list[0]}")
    except:
        print("Done parsing")
#############################################################################

    result = None
    rest = None
    if len(token_list) == 0:
        print("returning NULL STMT and empty token list")
        return NullStmt(), []

    is_assign = False
    i = 0
    if isinstance(token_list[i], VarToken):
        i += 1
        while i < len(token_list) and isinstance(token_list[i], Whitespace):
            i += 1
        if i < len(token_list) and isinstance(token_list[i], Equals):
            is_assign = True
            i += 1
            while i < len(token_list) and isinstance(token_list[i], Whitespace):
                i += 1
            parsed, rest = parse_expression(token_list[i:], do_app=True, depth=0)
            # print(f"NEW ASSIGNMENT and PARSED IS: {parsed}({type(parsed)})")
            result = AssignmentStmt(token_list[0].text, parsed)




    if not is_assign:
        result, rest = parse_expression(token_list, do_app=True, depth=0)
        result = ExprStmt(result)

    i = 0
    while i < len(rest) and isinstance(rest[i], Whitespace):
        i += 1

    if i < len(rest) and not isinstance(rest[i], Newline):
        raise Exception('Need new line between statements')
    i += 1

    parsed, rest = parse_statement(rest[i:], depth + 1)

    # print(f"Block of result: {result}({type(result)}), parsed: {parsed}({type(parsed)}) and then rest: {rest}({type(rest)})")
    return BlockStmt(result, parsed), rest


def compile_tree(stmt: StmtNode, bindings=None):
    """
    Take parsed syntax tree with assignment names that need to be replaced with their value
    :param stmt: syntax tree of nested StmtNodes
    :param bindings: dictionary of bindings (ie 'zero' -> 'Ls.Lz.z')
    :return: renamed, pre-compiled to just expressions, syntax tree, and the bindings dict
    """
    global EXPRS
    bindings = bindings or dict()
    if isinstance(stmt, ExprStmt):
        e = stmt.expr
        for key in bindings:
            e = substitute_expr(key, bindings[key], e)
        EXPRS.append(repr(stmt.expr))
        return ExprStmt(e), bindings

    elif isinstance(stmt, NullStmt):
        return stmt, bindings

    elif isinstance(stmt, AssignmentStmt):
        bindings = dict(bindings)
        e = stmt.expr
        for key in bindings:
            e = substitute_expr(key, bindings[key], e)
        bindings[stmt.name] = e
        return NullStmt(), bindings

    elif isinstance(stmt, BlockStmt):
        new_stmt, new_bindings = compile_tree(stmt.stmt, bindings)
        rest_compiled, new_bindings = compile_tree(stmt.rest, new_bindings)
        if isinstance(new_stmt, NullStmt):
            return rest_compiled, new_bindings
        elif isinstance(rest_compiled, NullStmt):
            return new_stmt, new_bindings
        return BlockStmt(new_stmt, rest_compiled), new_bindings


def parse_expression(token_list, do_app, depth):
    """
    Parses an entire expression of Lambda Calculus
    :param token_list: List of all tokens in source code
    :param do_app: On/Off flag telling is whether we want to apply terms in inner-expressions (yes for Ab and Paren)
    :param depth: Depth of recursive calls to parse (0 is top level)
    :return: Expression in terms of abstract classes, ready for evaluator and rest of source code (eventually [])
    """
    result = None
    # for printing for clarity
    prefix = '\t' * depth

    # special print to include prefixes. also can be turned off
    # print_pre = lambda v: print(f'{prefix}{v}')
    print_pre = lambda v: None
    print_pre('--------------------------------------------------')
    print_pre(f"parse_expression({token_list}, {do_app}, {depth})")

    # if we see Lambda, make sure we then have Variable Period
    if isinstance(token_list[0], Lambda):
        # if not Variable, error
        if not isinstance(token_list[1], VarToken):
            raise Exception('Variable must follow Lambda')
        # if not Variable Period, error
        elif not isinstance(token_list[2], Period):
            raise Exception('Period must follow {Lambda}{Variable}')

        print_pre(f"Found Lambda: {token_list[:3]}, parsing: {token_list[3:]}\n\n")
        # sub_expression is chunked expression, then rest is rest of token list
        sub_expr, rest = parse_expression(token_list[3:], True, depth + 1)

        print_pre(f"\n-> Asbtraction: L{token_list[1].text}. {sub_expr}\n")
        # turn verified Lambda abstraction into Abstraction
        expr = Abstraction(token_list[1].text, sub_expr)
        print_pre(f"-> Parsing rest: {rest}")
        result = expr, rest

    # if we get just a raw variable, that's the term, return it and the rest separately
    elif isinstance(token_list[0], VarToken):
        # return variable and rest
        print_pre(f"Found variable: {token_list[0].text}, parsing rest: {token_list[1:]}")

        result = Variable(token_list[0].text), token_list[1:]

    # if we see left paren
    elif isinstance(token_list[0], LParen):
        print_pre(f"Found '(', parsing rest: {token_list[1:]}\n\n")
        sub_expr, rest = parse_expression(token_list[1:], True, depth + 1)
        print_pre(f"-> Sub expr: {sub_expr}, rest: {rest}")
        if not isinstance(rest[0], RParen):
            raise Exception('Unmatched left parenthesis')
        print_pre(f"-> paren-term: {sub_expr}")
        result = sub_expr, rest[1:]
    elif isinstance(token_list[0], Newline):
        raise Exception("Newline??")
    else:
        raise Exception(f"Invalid program, saw token: {token_list[0]}")

    # after getting a valid expression built, unpack
    expr, rest = result
    # if a whitespace follows the expression
    if do_app:
        if rest != [] and isinstance(rest[0], Newline):
            return expr, rest

        while rest != [] and isinstance(rest[0], Whitespace):
            print_pre(f"-> APPLYING because we have term on left and whitespace following:")
            # term_b of the application is FIRST expression of rest
            # do this simply by parsing rest
            print_pre(f"-> LEFT: {expr}, parsing: {rest}")
            right, rest = parse_expression(rest[1:], False, depth + 1)

            print_pre(f"-> RIGHT: {right}")
            # build Application
            print_pre(f"\n-> APPLICATION: {expr} <-> {right}\n")
            expr = Application(expr, right)

    print_pre('--------------------------------------------------')

    return expr, rest


def eval_expr(expr, depth):
    """
    Reduces entire expression of Lambda Calculus
    :param expr: Expression given from parse_expression()[0]
    :return: Reduced Lambda Calculus expression
    """
    prefix = '\t' * depth
    # special print to include prefixes. also can be turned off
    # print_pre = lambda v: print(f'{prefix}{v}')
    print_pre = lambda v: None


    global HIGHEST
    if isinstance(expr, Abstraction):
        # if Abstraction, then recursively evaluate and reduce inner expression then return rewritten Abstraction
        print_pre(f"Abstraction: {expr}")
        return Abstraction(expr.variable, eval_expr(expr.expression, depth + 1))

    # if variable, leave
    if not isinstance(expr, Application):
        print_pre(f"Eval Variable, pass: {expr}")
        return expr

    # must be some kind of Application henceforth
    print_pre(f"Application: {expr}")
    if not isinstance(expr.fn, Abstraction):
        print_pre(f"Evaluating left operator: {expr.fn}")
        # if left is NOT an Abstraction, first try to reduce left term
        reduced_left = eval_expr(expr.fn, depth + 1)
        if not isinstance(reduced_left, Abstraction):
            # if still not an abstraction, then we apply LEFT term to recursively evaluated RIGHT term
            print_pre(f"Still not an abstraction ({reduced_left}) so applying to evaluated ({expr.operand})")
            return Application(reduced_left, eval_expr(expr.operand, depth + 1))

        # if left became an abstraction, then we just apply it to recursively evaluated RIGHT term
        print_pre(f"Evaluate: {reduced_left} <-> EVAL({expr.operand})")
        return eval_expr(Application(reduced_left, eval_expr(expr.operand, depth + 1)), depth + 1)

    return eval_expr(substitute_expr(expr.fn.variable, expr.operand, expr.fn.expression), depth + 1)


def eval_stmt(compiled_tree):
    """
    Large final function to evaluate file:: uses eval_expr
    :param compiled_tree: file compiled into syntax tree of nested Statements
    :return: List of evaluated/reduced expressions in file. lists each
    """
    if isinstance(compiled_tree, NullStmt):
        return []

    elif isinstance(compiled_tree, AssignmentStmt):
        return []

    elif isinstance(compiled_tree, ExprStmt):
        return [eval_expr(compiled_tree.expr, depth=0)]

    elif isinstance(compiled_tree, BlockStmt):
        return eval_stmt(compiled_tree.stmt) + eval_stmt(compiled_tree.rest)
    else:
        raise Exception(f"Error: saw value of type {type(compiled_tree)}")


def is_free(variable, expr):
    """
    :param variable: variable in question that were searching for in expression
    :param expr: expression in which we're searching
    :return: True if variable is free in expr, false if not
    """
    if isinstance(expr, Variable):
        return variable == expr.name

    elif isinstance(expr, Abstraction):
        if variable == expr.variable:
            return False
        return is_free(variable, expr.expression)

    elif isinstance(expr, Application):
        return is_free(variable, expr.fn) or is_free(variable, expr.operand)


def substitute_expr(var_name: str, applicand, expr):
    """
    Used in application as well as plugging-in of bound definitions
    :param var_name: Variable being replaced
    :param applicand: the term/statement getting subbed in
    :param expr: context in which substitution should happen
    :return: new statement post substitution
    """
    global HIGHEST
    if isinstance(expr, Variable):
        if expr.name == var_name:
            return applicand
        else:
            return expr
    elif isinstance(expr, Abstraction):
        # Ly.Lx.
        # if x            =     y
        if expr.variable == var_name:
            return expr
        else:
            # find variables in expr.expression
            abs_body = expr.expression
            abs_var = expr.variable
            if is_free(abs_var, applicand):
                abs_var = str(HIGHEST)
                abs_body = substitute_expr(expr.variable, Variable(abs_var), abs_body)
                HIGHEST += 1
            inner_subbed_expr = substitute_expr(var_name, applicand, abs_body)
            return Abstraction(abs_var, inner_subbed_expr)
    elif isinstance(expr, Application):

        return Application(substitute_expr(var_name, applicand, expr.fn), substitute_expr(var_name, applicand, expr.operand))


def lambda_interpret_expr(lambda_expr):

    print('--------START TOKENIZING---------')
    tokens = tokenize(lambda_expr)
    print('--------DONE TOKENIZING---------')
    print(f'TOKENS: {tokens}')

    print('--------START PARSING--------')
    parsed, _ = parse_expression(tokens, True, depth=0)
    print('--------DONE PARSING--------')
    print(f'PARSED EXPR: {parsed}')

    print('--------START EVALUATING--------')
    result = eval_expr(parsed, depth=0)
    print('--------DONE EVALUATING--------')


    print(f'\n\n\nRESULT: {result}')
    return result


def church_num_from_int(n: int):
    if n == 0:
        return f"(Ls.Lz.z)"
    elif n == 1:
        return f"(Ls.Lz.s z)"
    return f"(Ls.Lz.s {'(s '*(n-1) } z{')'*(n-1)})"


def lambda_interpret_file(filename):
    with open(filename, 'r') as fn:
        text = fn.read()
    tokens = tokenize(text)
    print(f"TOKENS: {tokens}")
    parsed = parse_statement(tokens, depth=0)
    print(f"PARSED: {parsed[0]}")
    compiled_tree = compile_tree(parsed[0])
    print(f"REWRITTEN: {compiled_tree[0]}")

    evaluated = eval_stmt(compiled_tree[0])
    print(f"\n\n\nEVALUATED: {'\n'.join([ str(e) for e in evaluated ])}")


def visualize_tree_ascii(node, prefix="", is_last=True):
    tree_str = prefix
    tree_str += "└── " if is_last else "├── "

    if isinstance(node, Variable):
        tree_str += f"Variable: {node.name}\n"
    elif isinstance(node, Abstraction):
        tree_str += f"Abstraction: L{node.variable}. {node.expression}\n"
        new_prefix = prefix + ("    " if is_last else "│   ")
        tree_str += visualize_tree_ascii(node.expression, new_prefix, True)
    elif isinstance(node, Application):
        tree_str += f"Application: ({node.fn}) ({node.operand})\n"
        new_prefix = prefix + ("    " if is_last else "│   ")
        tree_str += visualize_tree_ascii(node.fn, new_prefix, False)
        tree_str += visualize_tree_ascii(node.operand, new_prefix, True)
    elif isinstance(node, ExprStmt):
        tree_str += f"ExprStmt: {node.expr}\n"
        new_prefix = prefix + ("    " if is_last else "│   ")
        tree_str += visualize_tree_ascii(node.expr, new_prefix, True)
    elif isinstance(node, AssignmentStmt):
        tree_str += f"AssignmentStmt: {node.name} = {node.expr}\n"
        new_prefix = prefix + ("    " if is_last else "│   ")
        tree_str += visualize_tree_ascii(node.expr, new_prefix, True)
    elif isinstance(node, BlockStmt):
        tree_str += "BlockStmt\n"
        new_prefix = prefix + ("    " if is_last else "│   ")
        tree_str += visualize_tree_ascii(node.stmt, new_prefix, False)
        tree_str += visualize_tree_ascii(node.rest, new_prefix, True)
    elif isinstance(node, NullStmt):
        tree_str += "NullStmt\n"

    return tree_str


def save_tree_visualization_ascii(root_node, filename='lambda_calculus_tree.txt'):
    tree_str = visualize_tree_ascii(root_node)
    with open(filename, 'w') as f:
        f.write(tree_str)




def lambda_interpret_file_viz(txt=None, filename=None):
    if filename:
        with open(filename, 'r') as fn:
            text = fn.read()
    else:
        text = txt
    tokens = tokenize(text)
    print(f"TOKENS: {tokens}")
    parsed = parse_statement(tokens, depth=0)
    print(f"PARSED: {parsed[0]}")

    # Visualize the parsed tree
    save_tree_visualization_ascii(parsed[0], f'{filename[:-7]}_parsed_tree.txt')

    compiled_tree = compile_tree(parsed[0])
    print(f"REWRITTEN: {compiled_tree[0]}")
    # Visualize the compiled tree

    evaluated = eval_stmt(compiled_tree[0])

    print(f'\nPROGRAM:')
    for x, y in zip(EXPRS, evaluated):
        print(f"{x} --> {y}")
    return EXPRS, evaluated

def format_church_numeral_output(term: str):
    # 1. Basic validation: two L's and two periods
    if term.count('L') != 2 or term.count('.') != 2:
        return f"{term} :: [Not integer]"

    # 2. Check balanced parentheses
    paren_count = 0
    for char in term:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        if paren_count < 0:
            return f"{term} :: [Not integer]"
    if paren_count != 0:
        return f"{term} :: [Not integer]"

    # 3. Get binding variables
    parts = term.split('L')[1:]
    binding_vars = [p[0] for p in parts]
    first_var = binding_vars[0]  # This is the one we want to count (usually 'f')

    # 4. Count occurrences of the first binding variable
    # We subtract 1 because one occurrence is the binding itself
    count = term.count(first_var) - 1

    if count <= 9:
        return f"{term} :: [{count}]"
    return f"(Ls.(Lz.(s) ((s) ((s) ((s) ((s) ((s) ((s) ((s) ........ (z)))))))))) :: [{count}]"


if __name__ == '__main__':

    lambda_interpret_file_viz(filename='code.lambda')


