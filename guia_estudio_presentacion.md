# Guía de Estudio para la Defensa del Proyecto: Compilador de Python (Subset)

Esta guía desglosa el funcionamiento de cada archivo del proyecto, explicando las decisiones de diseño, la estructura del código y cómo interactúan las partes.

## 1. Visión General del Proyecto

El objetivo es construir un compilador para un subconjunto del lenguaje Python.
- **Herramienta**: PLY (Python Lex-Yacc), una implementación de lex y yacc para Python.
- **Componentes**:
    - `lexer.py`: Analizador Léxico (Tokenización).
    - `parser.py`: Analizador Sintáctico (Gramática).
    - `main.py`: Punto de entrada y orquestador.

---

## 2. Analizador Léxico (`lexer.py`)

El lexer transforma el código fuente (texto) en una secuencia de tokens.

### A. Definición de Tokens
El código define una lista de `tokens` que el parser consumirá.
- **Palabras Reservadas**: Se definen en un diccionario `reserved` (`'def': 'DEF'`, `'if': 'IF'`, etc.). Esto permite verificar si un identificador es una variable o una palabra clave.
- **Tipos de Token**:
    - **Operadores**: `PLUS`, `MINUS`, `TIMES`, `DIVIDE`, `EQUAL` (asignación), `EQEQ` (comparación), etc.
    - **Delimitadores**: `LPAREN`, `RPAREN`, `COMMA`, `COLON`.
    - **Especiales**: `NEWLINE`, `INDENT`, `DEDENT` (cruciales para Python).

### B. Expresiones Regulares
Se usan regex para identificar patrones de texto.
- **Simples**: `t_PLUS = r'\+'` (el `\` escapa el caracter especial `+`).
- **Complejas (Funciones)**: Se usan cuando se necesita procesar el valor del token.
    - `t_FLOAT`: Detecta números con punto decimal o notación científica. Convierte el valor a `float`.
    - `t_INT`: Detecta secuencias de dígitos. Convierte a `int`.
    - `t_STRING`: Maneja cadenas con comillas simples o dobles. Elimina las comillas del valor.
    - `t_NAME`: Identifica nombres de variables o funciones. **Importante**: Aquí se verifica si el nombre es una palabra reservada usando `reserved.get(t.value, 'NAME')`.

### C. Manejo de Indentación (`IndentLexer`)
Python usa indentación para definir bloques, pero las gramáticas libres de contexto (como la de yacc) no entienden de espacios. Por eso, transformamos la indentación en tokens explícitos: `INDENT` (inicio de bloque) y `DEDENT` (fin de bloque).

**Clase `IndentLexer`**:
1.  **Filtro**: Envuelve el lexer original. Intercepta el flujo de tokens.
2.  **Lógica (`filter_tokens`)**:
    - Mantiene una pila (`indent_stack`) con los niveles de indentación (empieza en 0).
    - Cuando encuentra un `NEWLINE`, mira los espacios/tabs de la siguiente línea.
    - **Si la indentación aumenta**: Genera un token `INDENT` y apila el nuevo nivel.
    - **Si la indentación disminuye**: Genera uno o más tokens `DEDENT` hasta coincidir con un nivel previo en la pila. Si no coincide, reporta error.
    - **Si es igual**: No hace nada.
3.  **Final del archivo**: Genera `DEDENT`s restantes para cerrar todos los bloques abiertos.

### D. Manejo de Errores
- `t_error`: Se llama cuando el lexer encuentra un caracter que no coincide con ninguna regla. Imprime el error, lo guarda en `lexical_errors` y salta el caracter.

---

## 3. Analizador Sintáctico (`parser.py`)

El parser toma los tokens del lexer y verifica que sigan la gramática definida. Construye un Árbol de Sintaxis Abstracta (AST) o ejecuta acciones.

### A. Estructura de la Gramática
Las funciones `p_nombre_regla` definen la gramática en sus docstrings.
- **`p_program`**: Regla inicial. Un programa es una lista de sentencias (`stmt_list`).
- **`p_stmt_list`**: Define una secuencia de sentencias. Es recursiva: `lista -> lista sentencia | sentencia`.
- **`p_stmt_line`**: Una "línea" puede ser una sentencia simple, una definición de función (`funcdef`) o una línea vacía.

### B. Precedencia de Operadores
En lugar de usar una tabla `precedence`, la jerarquía de las reglas define el orden de operaciones (de menor a mayor precedencia):
1.  **`or_expr`**: Más baja precedencia.
2.  **`and_expr`**
3.  **`not_expr`**
4.  **`comparison`** (`==`, `<`, etc.)
5.  **`arith_expr`** (`+`, `-`)
6.  **`term`** (`*`, `/`)
7.  **`factor`** (Menos unario `-x`)
8.  **`atom`** (Paréntesis, números, variables): Más alta precedencia.

Esto asegura que `2 + 3 * 4` se parsee como `2 + (3 * 4)`.

### C. Construcción del AST (Árbol Sintáctico)
En cada regla `p[0] = ...`, construimos una tupla que representa el nodo del árbol.
- Ejemplo `assign_stmt`: `NAME = expr` -> `('assign', 'x', '=', 5)`
- Ejemplo `binop`: `expr + expr` -> `('arith', '+', izq, der)`
- Ejemplo `funcdef`: `def nombre(args): ...` -> `('func_def', nombre, [args], cuerpo)`

Este AST es la "salida" del compilador, una representación estructurada del código.

### D. Manejo de Errores
- `p_error`: Se llama cuando llega un token inesperado.
    - Si `p` existe: Imprime el token y línea.
    - Si `p` es `None` (EOF): Significa que el archivo terminó inesperadamente (ej. falta cerrar un paréntesis).

---

## 4. Archivo Principal (`main.py`)

El punto de entrada que une todo.

1.  **Argumentos**: Verifica que se pase un archivo como argumento (`sys.argv`).
2.  **Lectura**: Abre y lee el archivo fuente.
3.  **Fase 1: Lexing**:
    - Alimenta el lexer con el código.
    - Itera sobre los tokens e imprime cada uno.
    - Si hay errores léxicos (`lexical_errors` no vacío), detiene el proceso.
4.  **Fase 2: Parsing**:
    - Reinicia el lexer (importante porque es un iterador).
    - Llama a `parser.parse(data, lexer=lexer)`.
    - Si `parser.errors` está vacío, imprime el AST resultante (éxito).
    - Si hay errores, reporta la cantidad.

---

## Preguntas Frecuentes para la Defensa

1.  **¿Por qué una clase `IndentLexer`?**
    *   Porque PLY por defecto ignora espacios y saltos de línea. Python *necesita* saber cuántos espacios hay para definir bloques. `IndentLexer` cuenta esos espacios y emite tokens "virtuales" `INDENT`/`DEDENT`.

2.  **¿Cómo se maneja la ambigüedad en la gramática?**
    *   La gramática diseñada es no ambigua gracias a la jerarquía de expresiones (terminos, factores, etc.), lo que define explícitamente la precedencia y asociatividad.

3.  **¿Qué devuelve el parser?**
    *   Devuelve una estructura de datos (tuplas anidadas) que representa el árbol sintáctico del programa, listo para ser procesado por una etapa posterior (como un generador de código o intérprete).

---

## 5. Archivos Generados (PLY)

Al ejecutar el compilador, PLY genera dos archivos automáticamente:
- **`parsetab.py`**: Contiene las tablas del autómata LR compiladas. Esto hace que el arranque sea más rápido en ejecuciones subsecuentes, ya que no tiene que volver a procesar la gramática.
- **`parser.out`**: Un archivo de log detallado que describe el autómata de la gramática, los estados y, lo más importante, los **conflictos shift/reduce** o **reduce/reduce** si los hubiera. Es vital para depurar la gramática.
