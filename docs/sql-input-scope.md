# SQL input scope / Alcance del SQL de entrada

SqlToViz takes SQL text and results already returned by your database. It
does not connect to a database, execute SQL, or validate statements for a
particular database engine. Get the column names and rows from your database
driver and keep their order when supplying a positional schema.

SqlToViz recibe el texto SQL y los resultados que ya devolvió tu base de datos.
No se conecta a una base, no ejecuta SQL y no valida las consultas para un motor
específico. Obtén las columnas y las filas de tu controlador y conserva su orden
cuando uses un esquema posicional.

| Syntax / Sintaxis | Python experimental engine / Motor experimental de Python |
| --- | --- |
| Standard-style `SELECT`, aliases, aggregates | Extracts lexical features / Extrae características léxicas |
| Double-quoted, backtick, or bracket identifiers | Recognizes quoted identifiers / Reconoce identificadores delimitados |
| `--` lines and non-nested `/* ... */` blocks | Skips comments / Omite comentarios |
| SQL Server `TOP n` | Recognizes the prefix in projection scanning / Reconoce el prefijo al recorrer la proyección |
| Dialect-specific grammar, catalog resolution, batch parsing | No compatibility guarantee / Sin garantía de compatibilidad |

For example, the lexer recognizes `"Total"`, `[Total]`, and `\`Total\``
as quoted identifier forms. This describes token recognition, not equivalent
query semantics across PostgreSQL, SQL Server, MySQL, or SQLite. Nested block
comments, PostgreSQL dollar quoting and escaped closing brackets are outside
the documented lexical subset. Unclosed quotes and block comments raise
`FeatureError` in the experimental Python lexer.

Por ejemplo, las comillas dobles, los corchetes y los acentos graves se reconocen
como delimitadores de identificadores. Eso describe el reconocimiento léxico.
La interpretación de una consulta depende de PostgreSQL, SQL Server, MySQL o
SQLite. Los comentarios de bloque anidados, las comillas con signo de dólar de
PostgreSQL y los corchetes de cierre escapados quedan fuera del subconjunto
documentado. Las comillas y comentarios de bloque sin cerrar generan
`FeatureError` en el analizador léxico experimental de Python.

The deterministic SDK preview uses a smaller input path. Treat it as a
visualization heuristic for supplied results. The versioned mathematical
requirements are in the [SqlVizSpec feature contract](../spec/sqlvizspec-v1-features.md).

La vista previa determinista de los SDK usa un procesamiento de entrada más
simple. Es una heurística de visualización para los resultados que le entregas.
El [contrato de características SqlVizSpec](../spec/sqlvizspec-v1-features.md)
define los requisitos matemáticos versionados.
