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

    # 1. Análisis Léxico (opcional: mostrar tokens)
    print("\n[Fase 1: Análisis Léxico]")
    lexical_errors.clear()
    lexer.input(data)
    
    # Iterar sobre tokens para mostrar errores léxicos si los hay
    # Nota: El lexer ya imprime "Error léxico" en caso de problemas.
    token_list = []
    while True:
        tok = lexer.token()
        if not tok:
            break
        token_list.append(tok)
        print(tok)
    
    if lexical_errors:
        print(f"\n>>> Se encontraron {len(lexical_errors)} error(es) léxico(s). <<<")
        print(">>> El programa NO es válido. <<<")
        return
    
    # Reiniciar lexer para el parser
    lexer.input(data)

    # Limpiar errores previos del módulo parser (si los hubiera)
    import parser as parser_mod
    parser_mod.errors.clear()

    # 2. Análisis Sintáctico
    print("\n[Fase 2: Análisis Sintáctico]")
    result = parser.parse(data, lexer=lexer)
    
    if not parser_mod.errors:
        print("\nResultado del análisis (Estructura interna):")
        print(result)
        print("\n>>> El programa es léxica y sintácticamente CORRECTO. <<<")
    else:
        print(f"\n>>> Se encontraron {len(parser_mod.errors)} error(es) sintáctico(s). <<<")
        print(">>> El programa NO es válido. <<<")

if __name__ == '__main__':
    main()
