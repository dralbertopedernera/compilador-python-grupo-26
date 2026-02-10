import ply.yacc as yacc
from lexer import tokens

# Lista para acumular errores
errors = []

# --- Reglas Gramaticales ---
# Las funciones p_ definen la gramática. EL docstring contiene la regla BNF.

# Regla inicial: El punto de entrada de la gramática.
# Un programa es simplemente una lista de sentencias.
def p_program(p):
    '''program : stmt_list'''
    # p[0] es el resultado de la regla. Aquí, simplemente pasamos la lista.
    p[0] = p[1]

# Lista de sentencias: Definición recursiva.
# Puede ser una lista seguida de una linea, o una sola linea inicial.
def p_stmt_list(p):
    '''stmt_list : stmt_list stmt_line
                 | stmt_line'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]] # Concatenar listas
    else:
        p[0] = [p[1]]        # Iniciar lista

# Línea de sentencia
def p_stmt_line(p):
    '''stmt_line : simple_stmt NEWLINE
                 | funcdef
                 | NEWLINE'''
    if len(p) == 3:
        p[0] = p[1]
    elif len(p) == 2:
        if p.slice[1].type == 'NEWLINE':
             p[0] = None
        else:
             p[0] = p[1]

# Definición de función:
# Estructura: def nombre(args): \n indent bloque dedent
# Note el uso de INDENT y DEDENT para delimitar el cuerpo de la función.
def p_funcdef(p):
    '''funcdef : DEF NAME LPAREN NAME COMMA NAME RPAREN COLON NEWLINE INDENT stmt_block DEDENT'''
    # Construimos un nodo ('func_def', nombre, [param1, param2], cuerpo)
    p[0] = ('func_def', p[2], [p[4], p[6]], p[11])

# Bloque de sentencias (dentro de función)
def p_stmt_block(p):
    '''stmt_block : stmt_block stmt_line
                  | stmt_line'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

# Sentencias simples
def p_simple_stmt(p):
    '''simple_stmt : assign_stmt
                   | expr_stmt'''
    p[0] = p[1]

# Asignación:
# nombre = expresión
def p_assign_stmt(p):
    '''assign_stmt : NAME assign_op expr'''
    # AST: ('assign', variable, operador, valor)
    p[0] = ('assign', p[1], p[2], p[3])

def p_assign_op(p):
    '''assign_op : EQUAL
                 | PLUSEQ
                 | MINUSEQ'''
    p[0] = p[1]

# Expresión como sentencia
def p_expr_stmt(p):
    '''expr_stmt : expr'''
    p[0] = p[1]

# --- Expresiones y Precedencia ---
# La jerarquía de funciones define la precedencia de operadores (de menor a mayor).
# or -> and -> not -> comparación -> suma/resta -> mult/div -> unario -> átomo

def p_expr(p):
    '''expr : or_expr'''
    p[0] = p[1]

def p_or_expr(p):
    '''or_expr : and_expr
               | or_expr OR and_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('or', p[1], p[3])

def p_and_expr(p):
    '''and_expr : not_expr
                | and_expr AND not_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('and', p[1], p[3])

def p_not_expr(p):
    '''not_expr : NOT not_expr
                | comparison'''
    if len(p) == 3:
        p[0] = ('not', p[2])
    else:
        p[0] = p[1]

def p_comparison(p):
    '''comparison : arith_expr
                  | arith_expr comp_op arith_expr'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('comparison', p[2], p[1], p[3])

def p_comp_op(p):
    '''comp_op : EQEQ
               | NEQ
               | LT
               | GT'''
    p[0] = p[1]

def p_arith_expr(p):
    '''arith_expr : term
                  | arith_expr PLUS term
                  | arith_expr MINUS term'''
    # Se evalúa de izquierda a derecha (recursividad por izquierda)
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('arith', p[2], p[1], p[3])

def p_term(p):
    '''term : factor
            | term TIMES factor
            | term DIVIDE factor'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ('term', p[2], p[1], p[3])

def p_factor(p):
    '''factor : MINUS factor
              | atom'''
    if len(p) == 3:
        p[0] = ('unary_minus', p[2])
    else:
        p[0] = p[1]

# Átomo: La unidad más básica (alta precedencia).
# Puede ser un nombre, literal, paréntesis o llamada a función.
def p_atom(p):
    '''atom : NAME
            | literal
            | LPAREN expr RPAREN
            | call'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]

def p_call(p):
    '''call : NAME LPAREN arglist_opt RPAREN
            | PRINT LPAREN arglist_opt RPAREN
            | LEN LPAREN arglist_opt RPAREN
            | ROUND LPAREN arglist_opt RPAREN'''
    p[0] = ('call', p[1], p[3])

def p_arglist_opt(p):
    '''arglist_opt : empty
                   | arglist'''
    p[0] = p[1] if p[1] is not None else []

def p_arglist(p):
    '''arglist : expr
               | arglist COMMA expr'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = p[1] + [p[3]]

def p_literal(p):
    '''literal : INT
               | FLOAT
               | STRING'''
    # Envolvemos el valor en una tupla para identificarlo como literal en el AST
    p[0] = ('literal', p[1])

def p_empty(p):
    '''empty :'''
    pass

# --- Manejo de Errores ---

def p_error(p):
    if p:
        msg = f"Error sintáctico en línea {p.lineno}: Se encontró token inesperado '{p.value}' ({p.type})"
        print(msg)
        errors.append(msg)
    else:
        # p es None si se llega al final del archivo (EOF) inesperadamente
        msg = "Error sintáctico: Fin de archivo inesperado (posiblemente falta cerrar paréntesis o bloque)"
        print(msg)
        errors.append(msg)

# Construir el parser
parser = yacc.yacc()
