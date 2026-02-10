import ply.lex as lex

# --- Definición de Tokens ---
# El lexer necesita una lista de tokens para exportar al parser.

# Palabras reservadas: Se definen en un diccionario para mapear
# la cadena (ej: 'def') a su TIPO DE TOKEN (ej: 'DEF').
# Esto permite diferenciar variables llamadas 'def' (ilegal) de la palabra clave.
reserved = {
    'def': 'DEF',
    'if': 'IF',       
    'print': 'PRINT',
    'len': 'LEN',
    'round': 'ROUND',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT'
}

# Lista completa de tokens:
# Incluye los definidos arriba (reserved) y los declarados abajo como regex.
# INDENT/DEDENT/NEWLINE son cruciales para el análisis de bloques en Python.
tokens = [
    'NAME', 'INT', 'FLOAT', 'STRING',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
    'EQUAL', 'PLUSEQ', 'MINUSEQ',
    'EQEQ', 'NEQ', 'LT', 'GT',
    'LPAREN', 'RPAREN', 'COMMA', 'COLON',
    'NEWLINE', 'INDENT', 'DEDENT'
] + list(reserved.values())

# --- Expresiones Regulares Simples ---
# Definen tokens que no requieren procesamiento del valor (solo coincidencia).
# El prefijo r'' indica 'raw strings' para simplificar los escapes de regex.

t_PLUS    = r'\+'   # Escapamos + porque es caracter especial en regex
t_MINUS   = r'-'
t_TIMES   = r'\*'   # Escapamos *
t_DIVIDE  = r'/'
t_EQUAL   = r'='
t_PLUSEQ  = r'\+='
t_MINUSEQ = r'-='
t_EQEQ    = r'=='
t_NEQ     = r'!='
t_LT      = r'<'
t_GT      = r'>'
t_LPAREN  = r'\('   # Paréntesis literales
t_RPAREN  = r'\)'
t_COMMA   = r','
t_COLON   = r':'

# --- Expresiones Regulares con Acción ---
# Se usan funciones cuando necesitamos procesar el texto coincidente (t.value).

def t_FLOAT(t):
    r'\d+\.\d+([eE][+-]?\d+)?'
    t.value = float(t.value)
    return t

def t_INT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STRING(t):
    r'(\"([^\\\n]|(\\.))*\")|(\'([^\\\n]|(\\.))*\')'
    t.value = t.value[1:-1] # Eliminar comillas
    return t

def t_NAME(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'NAME') # Verificar palabras reservadas
    return t

def t_COMMENT(t):
    r'\#.*'
    pass # Ignorar comentarios

# Definir NEWLINE para rastrear números de línea
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.type = 'NEWLINE'
    # Para el manejo de indentación, necesitamos devolver este token
    return t


t_ignore = ' \t'

# Lista para acumular errores léxicos
lexical_errors = []

def t_error(t):
    msg = f"Error léxico: Carácter ilegal '{t.value[0]}' en línea {t.lineno}"
    print(msg)
    lexical_errors.append(msg)
    t.lexer.skip(1)

# --- Filtro de Indentación ---

class IndentLexer(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.token_stream = None

    def input(self, data):
        self.lexer.input(data)
        self.lexer.lineno = 1
        self.token_stream = self.filter_tokens(self.lexer)

    def token(self):
        try:
            return next(self.token_stream)
        except StopIteration:
            return None

    # filter_tokens es un generador que intercepta el flujo de tokens
    def filter_tokens(self, lexer):
        indent_stack = [0] # Pila para rastrear niveles de indentación (top es nivel actual)
        tokens = iter(lexer.token, None)
        
        
        for token in tokens:
            yield token
            if token.type == 'NEWLINE':
                # Al encontrar enter, chequeamos la indentación de la línea SIGUIENTE.
                # PLY ignora espacios (t_ignore), así que debemos leer lexdata manualmente.
                
                
                current_indent = 0
                pos = lexer.lexpos
                data = lexer.lexdata
                
                while pos < len(data):
                    char = data[pos]
                    if char == ' ':
                        current_indent += 1
                        pos += 1
                    elif char == '\t':
                        current_indent += 4 # Asumimos tab = 4 espacios o ajuste según pref
                        pos += 1
                    elif char == '\n':
                        # Línea vacía: reiniciar conteo y avanzar
                        current_indent = 0
                        pos += 1
                        lexer.lineno += 1
                    elif char == '#':
                        # Ignorar comentarios hasta el final de la línea
                        while pos < len(data) and data[pos] != '\n':
                            pos += 1
                        break 
                    else:
                        break
                
                # Si llegamos al final del archivo con espacios, ignorar
                if pos >= len(data):
                    break

                # Comprobar niveles
                if current_indent > indent_stack[-1]:
                    indent_stack.append(current_indent)
                    t = lex.LexToken()
                    t.type = 'INDENT'
                    t.value = current_indent
                    t.lineno = token.lineno 
                    t.lexpos = pos
                    yield t
                elif current_indent < indent_stack[-1]:
                    while current_indent < indent_stack[-1]:
                        indent_stack.pop()
                        t = lex.LexToken()
                        t.type = 'DEDENT'
                        t.value = indent_stack[-1]
                        t.lineno = token.lineno
                        t.lexpos = pos
                        yield t
                    if current_indent != indent_stack[-1]:
                        print(f"Error de Indentación en línea {token.lineno}")
                
                # No modificamos lexpos del lexer real; PLY saltará los espacios gracias a t_ignore
                # Nosotros solo los leímos para calcular INDENT/DEDENT.
        
        # Al final del archivo, vaciar la pila de indentación
        while len(indent_stack) > 1:
            indent_stack.pop()
            t = lex.LexToken()
            t.type = 'DEDENT'
            t.value = 0
            t.lineno = lexer.lineno
            t.lexpos = lexer.lexpos
            yield t

# Construir el lexer básico
lexer_base = lex.lex()

# Envolverlo
lexer = IndentLexer(lexer_base)
