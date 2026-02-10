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

    - **Diferencia Clave**:
        - **Regex Simple**: Se usa cuando el token es *estático* (siempre es el mismo texto, como `+` o `if`). El valor del token es exactamente lo que se escaneó.
        - **Regex con Acción (Función)**: Se usa cuando el token es *dinámico* (como un número `123`, `45.6` o un nombre `myVar`) o requiere procesamiento (como quitar comillas a un string, convertir a int/float, o verificar palabras reservadas).

### C. Manejo de Indentación (`IndentLexer`)

Python usa indentación significativa para definir bloques, pero las gramáticas libres de contexto (como la de yacc) no "entienden" de espacios en blanco; solo entienden tokens de inicio (`{`) y fin (`}`).
Para solucionar esto, transformamos la indentación visual en tokens explícitos: `INDENT` (inicio de bloque) y `DEDENT` (fin de bloque).

**1. El Patrón de Filtro (Wrapper)**:
La clase `IndentLexer` envuelve al lexer original. Funciona como un "interceptor" (middleware).
- `lexer.token()` original devuelve tokens crudos.
- `IndentLexer.token()` llama al original, pero inyecta `INDENT` y `DEDENT` cuando detecta cambios de nivel.

**2. La Lógica Paso a Paso (`filter_tokens`)**:
Mantenemos una **pila (`indent_stack`)** que rastrea los niveles de indentación anidados. Empieza con `[0]` (nivel base).

Cuando el lexer encuentra un token `NEWLINE` (fin de línea):
1.  **Lectura Manual**: Dado que PLY ignora los espacios (`t_ignore`), debemos leer manualmente los caracteres siguientes (`lexdata`) para contar cuántos espacios o tabulaciones hay al inicio de la nueva línea.
2.  **Comparación con la Pila**:
    - **Mayor Indentación (> tope pila)**:
        - Significa que **se abrió un nuevo bloque**.
        - Acción: Generar token `INDENT`, empujar nueva indentación a la pila.
        - Ejemplo: De 0 espacios pasamos a 4 espacios. Pila `[0]` -> `[0, 4]`. Token `INDENT`.
    - **Menor Indentación (< tope pila)**:
        - Significa que **se cerró uno o más bloques**.
        - Acción: Generar token `DEDENT` repetidamente y sacar elementos de la pila hasta encontrar el nivel actual.
        - **Error**: Si la indentación actual no coincide con ningún nivel anterior en la pila, es un `IndentationError` (ej. desindentar a 3 espacios cuando los niveles previos eran 0 y 4).
        - Ejemplo: De 8 espacios bajamos a 0. Pila `[0, 4, 8]` -> `DEDENT` (saca 8) -> `DEDENT` (saca 4) -> Pila `[0]`.
    - **Igual Indentación (== tope pila)**:
        - Continuamos en el mismo bloque. No se genera ningún token especial.

**3. Ejemplo Visual ("Traza")**:

Código:
```python
def foo():      # Nivel 0
    print("x")  # Nivel 4
print("y")      # Nivel 0
```

**Flujo de Tokens**:
1.  `DEF` `NAME` `LPAREN` `RPAREN` `COLON` `NEWLINE`. (El lexer ve el `\n`).
2.  **Filtro**: Lee 4 espacios en la siguiente línea.
    - `4 > 0` (Tope pila).
    - **Genera**: `INDENT`. Pila: `[0, 4]`.
3.  `PRINT` `LPAREN` `STRING` `RPAREN` `NEWLINE`.
4.  **Filtro**: Lee 0 espacios en la siguiente línea ("print").
    - `0 < 4` (Tope pila).
    - **Genera**: `DEDENT`. Pop 4. Pila: `[0]`.
    - ¿Coincide 0 con el nuevo tope (0)? Sí. Listo.
5.  `PRINT`... `EOF`.
6.  **Fin de Archivo**: Si quedaran niveles en la pila (ej. si el archivo termina indentado), se generan `DEDENT`s hasta vaciarla a 0.

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

### C. Construcción del AST (Árbol Sintáctico Abstracto)
El AST es una representación jerárquica del código que elimina los detalles innecesarios de la sintaxis (como paréntesis, dos puntos, o palabras clave) y se queda solo con la estructura lógica.

*   **¿Por qué "Árbol"?**: Porque el código es jerárquico. Una suma `2 + 3` es hija de una asignación `x = ...`.
*   **¿Por qué "Abstracto"?**: Porque abstrae (elimina) la sintaxis "ruidosa". En el código escribes `(2 + 3)`, pero en el árbol solo importa que es una SUMA de 2 y 3. Los paréntesis ya no hacen falta porque la estructura del árbol define la prioridad.

En cada regla `p[0] = ...`, construimos una tupla que representa un nodo de este árbol:
- Ejemplo `assign_stmt`: `x = 5` -> `('assign', 'x', '=', 5)`
- Ejemplo `binop`: `2 + 3` -> `('arith', '+', 2, 3)`
- Ejemplo `funcdef`: `def nombre(args): ...` -> `('func_def', nombre, [args], cuerpo)`

Este AST es la "salida" del análisis sintáctico. Es una versión pura y estructurada del código fuente, lista para ser ejecutada o convertida a código de máquina.

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
