# Guía de Estudio Técnica - Proyecto Compiladores (Grupo 26)

Este documento sirve como material de apoyo para la defensa oral del proyecto. Explica en detalle la arquitectura, el funcionamiento interno de cada módulo y el análisis de los casos de prueba.

## 1. Arquitectura General
El compilador se divide en dos fases principales, implementadas usando la librería **PLY (Python Lex-Yacc)**:
1. **Análisis Léxico (`lexer.py`)**: Convierte el código fuente en una secuencia de tokens. Se encarga de la tokenización y el manejo de la indentación (similar a Python).
2. **Análisis Sintáctico (`parser.py`)**: Verifica que la secuencia de tokens cumpla con las reglas gramaticales definidas. Construye una estructura lógica (o árbol de sintaxis abstracta implícito en las tuplas) y reporta errores de estructura.
3. **Controlador Principal (`main.py`)**: Orquesta la lectura del archivo y la ejecución secuencial de ambas fases.

---

## 2. Análisis Detallado de Archivos

### `lexer.py` (El Analizador Léxico)
**Responsabilidad**: Escanear el texto de entrada y producir tokens.

*   **Definición de Tokens**:
    *   Utilizamos `ply.lex`.
    *   **Lista `tokens`**: Define todos los nombres posibles de tokens (ej. `NAME`, `INT`, `PLUS`, `INDENT`).
    *   **Diccionario `reserved`**: Mapea palabras clave como `def`, `print`, `if` a sus tipos de token específicos (`DEF`, `PRINT`, `IF`). Esto evita que se confundan con identificadores genéricos (`NAME`).

*   **Expresiones Regulares**:
    *   Simples: `t_PLUS = r'\+'`.
    *   Con lógica (`def t_INT(t)`): Permiten convertir el valor del lexema (string a int/float) al momento de leerlo.
    *   `t_NEWLINE`: Es crucial. Incrementa el contador de líneas (`t.lexer.lineno`) para que los reportes de error sean precisos.

*   **Manejo de Indentación (`IndentLexer`)**:
    *   Python (y nuestro lenguaje) usa indentación significativa para bloques, no llaves `{}`.
    *   PLY estándar ignora espacios (`t_ignore`). Para solucionar esto, creamos la clase `IndentLexer` que envuelve al lexer base.
    *   **Lógica**:
        1. Intercepta los tokens generados.
        2. Al detectar un `NEWLINE`, espía los espacios/tabs de la siguiente línea.
        3. Compara con la pila de indentación (`indent_stack`, inicializada en 0).
        4. **Si es mayor**: Genera un token `INDENT` y lo apila.
        5. **Si es menor**: Genera uno o más tokens `DEDENT` hasta nivelar la pila.
        6. **Si es igual**: No hace nada.

### `parser.py` (El Analizador Sintáctico)
**Responsabilidad**: Validar la estructura gramatical.

*   **Gramática (BNF)**:
    *   Las funciones `p_...` definen las reglas de producción. El docstring de cada función contiene la regla en formato BNF.
    *   Ejemplo: `stmt : simple_stmt | funcdef` significa que una sentencia puede ser simple o una definición de función.

*   **Reglas Clave**:
    *   `program`: Punto de entrada.
    *   `funcdef`: Estructura de funciones (`DEF NAME LPAREN ... INDENT block DEDENT`). Nótese el uso explícito de `INDENT`/`DEDENT` aquí.
    *   `expr`: Maneja la precedencia de operadores descomponiendo en `or_expr`, `and_expr`, `comparison`, `arith_expr`, `term`, `factor`, `atom`. Esto asegura que `*` se evalúe antes que `+`, etc.

*   **Manejo de Errores (`p_error`)**:
    *   Se invoca automáticamente cuando llega un token inesperado para el estado actual del parser.
    *   Imprime un mensaje amigable con el número de línea.
    *   Agrega el error a una lista global `errors` para que `main.py` sepa al final que hubo fallos.

### `main.py` (Programa Principal)
**Responsabilidad**: Interfaz de usuario y flujo de control.

1.  **Entrada**: Recibe el nombre del archivo por línea de comandos (`sys.argv`).
2.  **Fase Léxica**:
    *   Primero recorre todo el archivo solo con el lexer para mostrar los tokens (modo debug/demostración). Esto es útil en la defensa para mostrar qué está "viendo" el compilador.
3.  **Fase Sintáctica**:
    *   Reinicia el lexer.
    *   Limpia la lista de errores previos (`parser_mod.errors.clear()`).
    *   Llama a `parser.parse()`.
4.  **Decisión Final**:
    *   Verifica si la lista `errors` está vacía. Si lo está, declara el programa **CORRECTO**. Si no, informa la cantidad de errores y lo declara **INVÁLIDO**.

### `parsetab.py` (Tablas Generadas)
**Responsabilidad**: Eficiencia.

*   Este archivo **SE GENERA AUTOMÁTICAMENTE** por PLY la primera vez que se corre el parser o cuando la gramática cambia.
*   **¿Qué contiene?**: Las tablas de transición del autómata LALR (Look-Ahead LR) y el diccionario de reglas gramaticales.
*   **Importancia**: Evita que PLY tenga que recalcular y analizar todas las funciones del `parser.py` cada vez que se ejecuta el programa, acelerando el inicio. **No se debe editar manualmente.**

---

## 3. Análisis de Casos de Prueba

### Caso 1: Programa Válido (`valido.py`)
Muestra todas las capacidades exitosas:
*   Definición de funciones (`def suma...`).
*   Asignaciones (`x = 10`).
*   Llamadas a funciones anidadas en expresiones (`print(total)`).
*   Correcta indentación (4 espacios dentro de funciones).
*   **Resultado**: El parser devuelve una estructura de tuplas que representa el árbol sintáctico (ej. `('func_def', 'suma', ...)`).

### Caso 2: Error Léxico (`lexico_error.py`)
Prueba la robustez del Lexer.
*   Contiene caracteres como `@` y `$`.
*   **Comportamiento**:
    1. El `t_error` en `lexer.py` atrapa el carácter ilegal.
    2. Imprime "Carácter ilegal".
    3. Salta el carácter (`skip(1)`).
    4. El parser probablemente falle después porque falta algo o la expresión quedó incompleta, generando errores en cascada (lo cual es normal en compiladores simples).

### Caso 3: Error Sintáctico (`sintactico_error.py`)
Prueba las reglas gramaticales.
*   `def sin_dos_puntos(a, b)` -> Falta `:`. El parser espera `COLON` y encuentra `NEWLINE`.
*   `print(a)` sin indentar dentro de una función -> Error de indentación lógica.
*   `x = 10 +` -> Expresión incompleta. El parser espera un número o variable después del `+` y encuentra `NEWLINE`.
*   **Resultado**: Se reportan múltiples errores sintácticos y el programa se marca como inválido.
