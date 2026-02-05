import ply.lex as lex

# --- Definición de Tokens ---

# Palabras reservadas
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

tokens = [
    'NAME', 'INT', 'FLOAT', 'STRING',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE',
    'EQUAL', 'PLUSEQ', 'MINUSEQ',
    'EQEQ', 'NEQ', 'LT', 'GT',
    'LPAREN', 'RPAREN', 'COMMA', 'COLON',
    'NEWLINE', 'INDENT', 'DEDENT'
] + list(reserved.values())

# --- Expresiones Regulares Simples ---

t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_EQUAL   = r'='
t_PLUSEQ  = r'\+='
t_MINUSEQ = r'-='
t_EQEQ    = r'=='
t_NEQ     = r'!='
t_LT      = r'<'
t_GT      = r'>'
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_COMMA   = r','
t_COLON   = r':'

# --- Expresiones Regulares con Acción ---

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

# ... (rest of imports/definitions if needed, but I'll stick to inserting/modifying specific chunks)

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

    def filter_tokens(self, lexer):
        indent_stack = [0]
        tokens = iter(lexer.token, None)
        
        for token in tokens:
            yield token
            if token.type == 'NEWLINE':
                # Mirar el siguiente token para ver la indentación
                # Necesitamos "espiar" el input del lexer para ver los espacios
                # Pero PLY ya se comió los espacios por t_ignore.
                # ESTRATEGIA ALTERNATIVA TÍPICA PARA PLY+PYTHON:
                # Usar un estado o revisar lexer.lexdata en la posición actual.
                
                # Vamos a calcular la indentación manualmente leyendo lexdata
                # desde lexpos hasta que encontremos algo que no sea espacio.
                
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
                        # Línea vacía con espacios, reiniciamos conteo para la sig línea
                        current_indent = 0
                        pos += 1
                        # Opcional: emitir otro NEWLINE si queremos preservar líneas vacías
                        # pero la gramática suele ignorarlas o colapsarlas.
                        # Ajustar lineno manual si saltamos \n extra
                        lexer.lineno += 1
                    elif char == '#':
                        # Comentario al inicio de linea o indentado, lo saltamos hasta el final de linea
                        while pos < len(data) and data[pos] != '\n':
                            pos += 1
                        # Si encontramos \n, se procesará en la siguiente iteración del while externo (si volvemos)
                        # Pero aquí estamos dentro del cálculo de indent.
                        # Simplemente continuamos el bucle de indentación desde el \n
                        if pos < len(data) and data[pos] == '\n':
                            # current_indent = 0 # Reset para la próxima línea
                            # pos += 1
                            # lexer.lineno += 1
                            # En realidad, si hay comentario, esa linea no cuenta para indent changes
                            # mejor dejar que el lexer normal lo procese?
                            # El problema es que t_ignore se come los espacios antes del #.
                            pass
                        
                        # Simplificación: Si es comentario, ignorar esta línea para propósitos de indent
                        # y tratar como si tuviera la misma indentación que la anterior o simplemente 
                        # no generar tokens INDENT/DEDENT.
                        
                        # Lo más fácil: dejar que el lexer siga.
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
                
                # NO actualizamos lexer.lexpos manualmente aquí porque el lexer
                # normal de PLY se saltará los espacios gracias a t_ignore.
                # Solo inyectamos los tokens.
        
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
