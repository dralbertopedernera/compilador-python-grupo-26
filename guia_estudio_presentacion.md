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

El parser es el "policía gramatical" del compilador. Recibe los tokens del lexer y verifica si el orden tiene sentido según las reglas del lenguaje.

### A. Concepto Básico: Reglas de Producción
Imagina que defines una oración en español:
`Oración -> Sujeto + Verbo + Predicado`

En nuestro compilador, definimos reglas similares para Python:
`asignacion -> NOMBRE + IGUAL + EXPRESION` (Ej: `x = 5`)

Cada función en `parser.py` representa una de estas reglas.

### B. Terminales vs No Terminales (Conceptos Clave)
Esta es la distinción más importante para entender cualquier gramática en Teoría de Lenguajes Formales:

1.  **Símbolo Terminal (Token)**:
    *   Es un elemento atómico del lenguaje definido por el análisis léxico.
    *   No puede ser derivado ni descompuesto en otros símbolos gramaticales.
    *   **En PLY**: Corresponde a los tokens definidos en `lexer.py` (ej. `'PLUS'`, `'IF'`, `'NAME'`).

2.  **Símbolo No Terminal (Variable)**:
    *   Es un símbolo que representa un conjunto de cadenas o estructuras sintácticas.
    *   Se define mediante **reglas de producción** (gramática).
    *   Puede ser sustituido por una secuencia de Terminales y/u otros No Terminales.
    *   **En PLY**: Corresponde a los nombres de las funciones `p_` (ej. `expr`, `stmt_list`, `func_def`).

**Ejemplo Formal**:
Regla: `asignacion -> NOMBRE IGUAL EXPRESION`
*   `NOMBRE`, `IGUAL`: Son **Terminales** (obtenidos directamente del código fuente).
*   `EXPRESION`: Es un **No Terminal** (se deriva de otras reglas como `EXPRESION -> TERMINO + TERMINO`).
*   `asignacion`: Es un **No Terminal** (el resultado de la regla).

### C. Cómo funciona PLY (Paso a Paso)
PLY utiliza un algoritmo **LR (Left-to-Right scanning, Rightmost derivation)**, que es un método de análisis sintáctico ascendente (bottom-up).

1.  **Desplazamiento (Shift)**: Lee tokens uno a uno y los coloca en una pila.
    *   Ejemplo: Pila = `[NAME(x), EQUAL(=), INT(5)]`.
2.  **Reducción (Reduce)**: Identifica si los elementos en el tope de la pila coinciden con el lado derecho de una regla gramatical.
    *   Regla encontrada: `assign_stmt : NAME EQUAL expr`.
3.  **Acción**: Agrupa los elementos reducidos en un nuevo nodo No Terminal (`assign_stmt`) y ejecuta la función `p_assign_stmt`.
4.  **Repetición**: Continúa hasta reducir todo el programa al símbolo inicial (`program`).

### D. La Estructura de `p` (El Objeto de Producción)
Dentro de cada función, `p` actúa como una secuencia que contiene los componentes de la regla gramatical.
Supongamos la regla: `expr : expr PLUS term` (Suma)
- `p[0]`: Es la **caja resultante** (lo que devolvemos).
- `p[1]`: El primer elemento (`expr` de la izquierda).
- `p[2]`: El símbolo `PLUS` (`+`).
- `p[3]`: El segundo elemento (`term` de la derecha).

**Código Real**:
```python
def p_arith_expr(p):
    '''arith_expr : arith_expr PLUS term'''
    # p[0]        p[1]       p[2] p[3]
    
    # Creamos una tupla que representa esta suma en el árbol
    p[0] = ('arith', '+', p[1], p[3])
```

### E. Recursividad y Listas
¿Cómo parseamos una lista de sentencias infinita? Usando recursividad.
`stmt_list -> stmt_list + stmt_line`
Traducción: "Una lista de sentencias es... una lista anterior MÁS una nueva línea".

**Ejemplo de Ejecución**:
Código:
```python
x = 1
print(x)
```
1.  Parser lee `x = 1` -> Lo convierte en `stmt_line`.
    - `stmt_list` inicial = [`stmt_line`].
2.  Parser lee `print(x)` -> Lo convierte en otro `stmt_line`.
    - Regla: `stmt_list (anterior) + stmt_line (nuevo)`.
    - Resultado: `stmt_list` ahora tiene 2 elementos.

### F. Precedencia de Operadores (Jerarquía)
Para que `2 + 3 * 4` se resuelva correctamente como `2 + (3 * 4)` y no `(2 + 3) * 4`, estructuramos la gramática en niveles:
1.  **`atom`** (Paréntesis, números): Nivel más alto (se resuelve primero).
2.  **`factor`** (Negativos `-5`).
3.  **`term`** (Multiplicación `*`, División `/`).
4.  **`arith_expr`** (Suma `+`, Resta `-`).
5.  **`comparison`** (`<`, `>`).
6.  **`not_expr`, `and_expr`, `or_expr`**: Operadores lógicos (nivel más bajo).

El parser intenta resolver primero los niveles más altos ("más pegajosos"). Como `*` está en `term` y `+` en `arith_expr`, el `term` se agrupa antes.

### G. Construcción del AST (Árbol Sintáctico Abstracto)
El resultado final es un árbol de tuplas.
Código: `x = 2 + 3`
AST:
```python
('assign', 'x', '=', 
    ('arith', '+', 
        ('literal', 2), 
        ('literal', 3)
    )
)
```
Observa cómo la "Suma" está anidada dentro de la "Asignación". Esto es lo que devuelve `parser.parse()`.

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
