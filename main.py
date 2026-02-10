import sys
from lexer import lexer, lexical_errors
from parser import parser

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <archivo_fuente>")
        return

    filename = sys.argv[1]
    try:
        with open(filename, 'r') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{filename}'")
        return

    print(f"--- Iniciando Análisis de: {filename} ---")

    # [Fase 1: Análisis Léxico]
    # Primero convertimos el código fuente en una lista de tokens.
    # Esto nos permite ver si hay caracteres ilegales antes de intentar parsear la estructura.
    print("\n[Fase 1: Análisis Léxico]")
    lexical_errors.clear()
    lexer.input(data)
    
    # Iteramos sobre los tokens para imprimirlos y detectar errores léxicos.
    token_list = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        token_list.append(tok)
        print(tok)
    
    # Si hubo errores en la fase léxica, no tiene sentido continuar al parsing.
    if lexical_errors:
        print(f"\n>>> Se encontraron {len(lexical_errors)} error(es) léxico(s). <<<")
        print(">>> El programa NO es válido. <<<")
        return
    
    # [Fase 2: Análisis Sintáctico]
    # Reiniciamos el lexer (input) porque es un iterador y ya lo consumimos arriba.
    # Ahora el parser pedirá tokens al lexer uno a uno para validar la gramática.
    lexer.input(data)

    # Limpiamos errores previos del parser para esta nueva ejecución
    import parser as parser_mod
    parser_mod.errors.clear()

    print("\n[Fase 2: Análisis Sintáctico]")
    # parser.parse() ejecuta el análisis y devuelve el AST (tupla) si es exitoso.
    result = parser.parse(data, lexer=lexer)
    
    if not parser_mod.errors:
        print("\nResultado del análisis (Estructura interna):")
        # Imprimimos el Árbol de Sintaxis Abstracta (AST) generado.
        print(result)
        print("\n>>> El programa es léxica y sintácticamente CORRECTO. <<<")
    else:
        print(f"\n>>> Se encontraron {len(parser_mod.errors)} error(es) sintáctico(s). <<<")
        print(">>> El programa NO es válido. <<<")

if __name__ == '__main__':
    main()
