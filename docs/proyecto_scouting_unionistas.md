# Proyecto Scouting Unionistas

## Estado del proyecto

Documento de trabajo vivo para registrar el contexto, decisiones y avances del proyecto de scouting orientado al mercado de verano de Unionistas.

Fecha de arranque: 2026-06-09

## Inventario inicial del workspace

### Datos disponibles

Los datos actuales están en `data/` y proceden de Wyscout en formato CSV:

- `1RFEF_2025-26.csv`
- `2RFEF_2025-26.csv`
- `LaLiga2_2025-26.csv`
- `National1_2025-26.csv`
- `National2_2025-26.csv`
- `Portugal2_2025-26.csv`
- `Portugal3_2025-26.csv`
- `Portugal4_2025-26.csv`

### Volumen por fichero

| Fichero | Jugadores |
|---|---:|
| `1RFEF_2025-26.csv` | 1176 |
| `2RFEF_2025-26.csv` | 2449 |
| `LaLiga2_2025-26.csv` | 685 |
| `National1_2025-26.csv` | 499 |
| `National2_2025-26.csv` | 1096 |
| `Portugal2_2025-26.csv` | 595 |
| `Portugal3_2025-26.csv` | 616 |
| `Portugal4_2025-26.csv` | 1622 |

### Activos visuales disponibles

- Logos de competiciones en `assets/competiciones/`
- Escudos de Unionistas en `assets/escudo/`
- Marca MCode en `assets/mcode/`

## Primera lectura de los datos

### Observaciones relevantes

- La estructura de columnas es amplia y cubre métricas ofensivas, defensivas, de pase, progresión y portería.
- Hay columnas duplicadas o repetidas al final de los CSV.
- Aparecen jugadores de equipos de cantera o juveniles (`U17`, `U19`, `U20`, `U21`) mezclados con el pool principal.
- Hay registros con `domestic_competition_name` vacío.
- El dataset parece pensado para scouting amplio, pero necesita una capa previa de limpieza para ser útil en mercado real de verano.

### Señales iniciales de calidad de dato

| Fichero | Registros con competición informada | Registros con equipo cantera |
|---|---:|---:|
| `1RFEF_2025-26.csv` | 1133 | 39 |
| `2RFEF_2025-26.csv` | 2354 | 51 |
| `LaLiga2_2025-26.csv` | 669 | 9 |
| `National1_2025-26.csv` | 481 | 14 |
| `National2_2025-26.csv` | 1073 | 14 |
| `Portugal2_2025-26.csv` | 587 | 16 |
| `Portugal3_2025-26.csv` | 612 | 10 |
| `Portugal4_2025-26.csv` | 1604 | 12 |

## Roles del documento de referencia

El PDF `Roles Deportivo Cuenca.pdf` define los perfiles a modelar:

- Portero bueno con los pies
- Portero con muchas paradas
- Lateral defensivo
- Lateral ofensivo
- Central ganador de duelos
- Central rápido
- Central técnico
- Mediocentro defensivo
- Mediocentro creador
- Mediocentro box to box
- Extremo regateador
- Extremo centrador
- Extremo goleador
- Delantero cabeceador
- Delantero killer
- Delantero asociativo

## Enfoque de trabajo acordado

Antes de construir la plataforma, conviene completar estas fases:

1. Documentar y auditar lo que ya existe.
2. Definir el universo real de competiciones y jugadores objetivo para Unionistas.
3. Traducir los roles del PDF a variables Wyscout disponibles.
4. Limpiar el dato y fijar reglas de exclusión.
5. Diseñar la primera versión de la plataforma de scouting.

## Alcance confirmado para la primera versión

### Universo de jugadores

- Se incluirán jugadores senior, sub-23 y cantera.
- Siempre trabajaremos solo con jugadores para los que ya existan datos disponibles en los CSV actuales.

### Competiciones incluidas

- `1RFEF`
- `2RFEF`

La app ya queda preparada para ampliar la comparación con:

- `LaLiga2`
- `National1`
- `National2`
- `Portugal2`
- `Portugal3`
- `Portugal4`

El filtro de competiciones pasa a ser multiselección. Por defecto arranca con `1RFEF` y no se filtra por grupos desde sidebar; los grupos quedan visibles como contexto en tablas, ranking y fichas.

### Nota específica sobre National 2

- `National 2` se separa por grupos reales (`Grupo A`, `Grupo B`, `Grupo C`).
- Esta separación se apoya en una tabla de referencia específica para evitar errores de lectura por equipo.

### Caso de uso principal

- Objetivo principal: búsqueda de fichajes para Unionistas.
- Objetivo secundario a futuro: comparar candidatos con jugadores actuales de Unionistas.

### Prioridad deportiva inicial

- Primera posición prioritaria: porteros.
- La estructura debe quedar preparada para reutilizarse después con el resto de roles y posiciones.

## Iteración visual de la app

### Dirección adoptada

- La app mantiene `Streamlit` como base.
- La ficha rápida ha pasado a un lenguaje visual oscuro, más cercano a una scouting card que a un dashboard genérico.
- La lectura principal se organiza en:
  - cabecera editorial del jugador
  - dos tarjetas-radar superiores
  - tarjetas KPI de detalle
  - fortalezas y puntos a vigilar
  - bloque de contexto
  - visual específica de distribución

### Cambios ya integrados

- Cabecera del jugador con foto o silueta, nombre, posición, club, competición, grupo y KPIs circulares.
- KPI global grande en la cabecera y KPIs de `pies` y `paradas` en tamaño menor como lectura secundaria.
- Inclusión de escudo del equipo y país cuando el CSV lo trae.
- Dos perfiles visuales superiores:
  - `Portero con los pies`
  - `Portero de paradas`
- Radar con valores visibles junto a cada eje y encaje visible en la propia tarjeta.
- Reemplazo de la paleta marrón por una gama oscura con acentos azul, verde, amarillo y rojo.
- Tarjetas de métricas rápidas con jerarquía visual más fuerte.
- Sección de `Fortalezas` y `Puntos a vigilar`.
- Visual de distribución reinterpretada en planta de medio campo con:
  - pase corto/medio
  - pase largo
  - pase lateral

### Contexto técnico añadido al dato

- Se ha enriquecido la carga de porteros con:
  - `team_logo_url`
  - `birth_country_name`
  - `passport_country_names`

Esto permite que la ficha tenga más contexto visual sin depender de recursos externos añadidos manualmente.

### Nota abierta de modelado

- El CSV no trae una columna explícita de pases laterales.
- La visual calcula `pases laterales estimados/90` como:
  - `passes_avg - forward_passes_avg - back_passes_avg`
- La precisión lateral estimada se obtiene restando al total de pases acertados los pases acertados hacia delante y hacia atrás.
- Esta derivación es coherente con las categorías direccionales disponibles y se identifica como estimada para no presentarla como un dato original de Wyscout.

### Métricas utilizadas en el medio campograma

Datos directos del CSV:

| Lectura visual | Métrica de volumen | Métrica complementaria |
|---|---|---|
| Pase corto/medio | `short_medium_pass_avg` | `accurate_short_medium_pass_percent` |
| Pase largo | `long_passes_avg` | `successful_long_passes_percent` |
| Pases recibidos | `received_pass_avg` | `received_long_pass_avg` como contexto adicional |
| Longitud del estilo de pase | `average_pass_length` | `average_long_pass_length` |

Dato derivado:

| Lectura visual | Fórmula |
|---|---|
| Pases laterales estimados/90 | `passes_avg - forward_passes_avg - back_passes_avg` |
| Precisión lateral estimada | pases acertados totales menos acertados hacia delante y hacia atrás, dividido entre pases laterales estimados |

Las métricas `vertical_passes_avg`, `progressive_pass_avg` y sus porcentajes de éxito pueden aportar una capa adicional sobre progresión, pero se solapan conceptualmente con otras categorías y no deben sumarse como si fueran partes independientes del total.

El medio campograma es una representación conceptual de volumen relativo al máximo del grupo visible. Sin datos de eventos con coordenadas no puede mostrar la trayectoria, el origen, el destino exacto ni el lado real de cada pase.

### Contribución ofensiva del portero

La ficha incluye una sección descriptiva para identificar acciones ofensivas poco frecuentes:

| Lectura | Métrica |
|---|---|
| Asistencias | `assists` |
| xA total | `xg_assist` |
| Asistencias de tiro/90 | `shot_assists_avg` |
| Pases clave/90 | `key_passes_avg` |
| Preasistencias/90 | `pre_assist_avg` |
| Pre-preasistencias/90 | `pre_pre_assist_avg` |

Estas métricas no forman parte del scoring principal de `Juego de pies` porque tienen una distribución muy dispersa y dominada por ceros. En el universo inicial:

- Solo 9 de 288 porteros registran alguna asistencia.
- Aproximadamente entre el 5% y el 10% registra valores positivos en preasistencias, pre-preasistencias, pases clave o asistencias de tiro.
- Incluso entre porteros con al menos el 40% de minutos, la mayoría continúa con valor cero.

Un percentil general sería engañoso: una única acción podría colocar automáticamente a un portero cerca del percentil máximo. Por ello se muestran:

- valor absoluto o valor por 90;
- número de porteros visibles con registro positivo;
- posición del jugador únicamente entre los porteros con valor positivo.

Estas señales deben interpretarse como posibles evidencias de capacidad creativa o de inicio de ataques, siempre acompañadas por revisión de vídeo y contexto de minutos.

## Metodología de scoring de porteros

### Enfoque general

La app no utiliza una única nota construida a partir de métricas sueltas. El modelo actual trabaja en tres niveles:

1. `Macro`
   - `Juego de pies`
   - `Paradas`
2. `Meso`
   - bloques temáticos dentro de cada macro-área
3. `Micro`
   - métricas concretas que alimentan cada bloque

Esta estructura se eligió porque refleja mejor cómo piensa un staff de scouting o de entrenadores: no se evalúa a un portero por un número aislado, sino por comportamientos reconocibles.

### Cómo se calcula cada nota

Para cada portero:

1. Se toma cada métrica usada en el modelo.
2. Se compara su valor con el resto de porteros visibles bajo los filtros actuales.
3. Esa comparación se transforma en una posición relativa tipo percentil.
4. Los percentiles se combinan dentro de cada bloque según su peso interno.
5. Cada bloque genera una nota propia en escala `0-100`.
6. Las notas de bloque se combinan después con pesos de bloque para obtener:
   - `footwork_score`
   - `shotstop_score`

### Naturaleza de los pesos

Los pesos actuales son `criterio experto explícito`, no pesos estadísticos aprendidos por modelo.

Esto es intencionado y metodológicamente defendible:

- permite que la estructura refleje lógica futbolística real
- hace visible qué aspectos consideramos más importantes
- facilita revisar el modelo con staff técnico
- evita vender la nota como una “verdad matemática” cuando en realidad es una herramienta de apoyo al scouting

Por tanto:

- los pesos son revisables
- los pesos deben entenderse como una decisión metodológica
- cualquier cambio futuro debe quedar documentado

### Justificación del enfoque

Esta metodología es la base principal del proyecto porque, frente a alternativas más simples, aporta tres ventajas fuertes:

- la estructura por bloques refleja cómo analistas y entrenadores piensan sobre porteros
- los pesos diferenciales reconocen que no todas las dimensiones valen lo mismo
- el percentil relativo al grupo visible permite comparar al jugador en el contexto real de liga, grupo y filtros activos

## Macro-score: Juego de pies

### Bloques y pesos

| Bloque | Peso | Qué intenta medir | Justificación |
|---|---:|---|---|
| Participación | 1.00 | Cuánto entra el portero en el circuito de pase del equipo | No basta con pasar bien; primero tiene que participar y ser utilizado |
| Precisión global | 1.10 | Limpieza general del pase | La seguridad técnica es una base importante del juego con pies |
| Progresión | 1.20 | Capacidad para activar juego hacia delante | Se prioriza porque el valor real no es solo conservar, sino también ayudar a avanzar |
| Juego corto/medio | 1.00 | Uso y precisión del pase corto/medio | Es una dimensión estructural de la salida, pero no debe dominar por encima de la progresión |
| Juego largo | 1.15 | Frecuencia, precisión y alcance del pase largo | Tiene bastante peso porque puede cambiar la forma de jugar del equipo |
| Estilo | 0.50 | Tendencia a jugar más corto o más directo | Se usa como contexto de perfil, no como factor principal de calidad |

### Métricas por bloque

| Bloque | Métricas |
|---|---|
| Participación | `received_pass_avg`, `passes_avg` |
| Precisión global | `accurate_passes_percent` |
| Progresión | `forward_passes_avg`, `successful_forward_passes_percent` |
| Juego corto/medio | `short_medium_pass_avg`, `accurate_short_medium_pass_percent` |
| Juego largo | `long_passes_avg`, `successful_long_passes_percent`, `average_long_pass_length` |
| Estilo | `average_pass_length` |

### Lectura metodológica

- `Participación` nos dice si el portero forma parte del juego.
- `Precisión global` nos dice si la base técnica es limpia.
- `Progresión` nos dice si ayuda a avanzar, no solo a conservar.
- `Juego corto/medio` mide seguridad y continuidad.
- `Juego largo` mide si puede ofrecer una salida más directa y útil.
- `Estilo` no intenta decir si un portero es mejor o peor, sino cómo reparte.

## Macro-score: Paradas

### Bloques y pesos

| Bloque | Peso | Qué intenta medir | Justificación |
|---|---:|---|---|
| Carga defensiva | 0.95 | Exigencia de remates que soporta | Da contexto al portero: no es lo mismo ser exigido poco que mucho |
| Parada | 1.50 | Calidad pura de respuesta bajo remate | Es el núcleo del perfil y por eso recibe el mayor peso |
| Dominio de área | 0.85 | Intervención fuera de línea y respuesta aérea | Importa, pero menos que la parada pura |
| Resultado | 0.60 | Efecto final visible en goles recibidos y porterías a cero | Útil como capa de lectura, pero más contaminada por el contexto del equipo |

### Métricas por bloque

| Bloque | Métricas |
|---|---|
| Carga defensiva | `shots_against_avg` |
| Parada | `save_percent`, `prevented_goals_avg`, `xg_save_avg` |
| Dominio de área | `goalkeeper_exits_avg`, `gk_aerial_duels_avg` |
| Resultado | `conceded_goals_avg`, `clean_sheets` |

### Nota metodológica importante sobre `Resultado`

El bloque `Resultado` tiene una limitación conocida:

- `conceded_goals_avg` y `clean_sheets` no dependen solo del portero
- también reflejan el nivel defensivo del equipo, la calidad de los centrales, el contexto competitivo y el estilo colectivo

Por eso:

- este bloque debe interpretarse más como `resultado visible + contexto de equipo` que como habilidad individual pura
- no debe leerse de forma aislada
- la parte más representativa del talento individual en portería está en:
  - `Parada`
  - `Dominio de área`

### Recomendación abierta

En una siguiente iteración, este bloque puede revisarse de dos maneras:

1. bajar su peso de `0.80` a `0.60`
2. mantenerlo con advertencia metodológica explícita

En la versión actual del modelo, ya se ha aplicado la primera opción: el peso del bloque `Resultado` se ha bajado a `0.60`.

## Qué significa la nota y qué no significa

### Sí significa

- cómo se comporta un portero respecto al grupo visible
- si destaca más en juego con pies, en portería o en ambos
- qué tipo de perfil aparece cuando se cruza con los filtros activos

### No significa

- que sea “el mejor portero” en términos absolutos
- que la nota sea independiente del contexto
- que los pesos sean una verdad estadística cerrada

## Decisiones metodológicas clave

| Decisión | Motivo |
|---|---|
| Usar percentiles relativos al grupo visible | Permite scouting contextual según liga, grupo y filtros |
| Trabajar por bloques en vez de métricas sueltas | Reduce ruido y hace la lectura más futbolística |
| Mantener pesos explícitos | Hace el modelo transparente y revisable |
| Separar `Juego de pies` y `Paradas` | Evita esconder perfiles distintos detrás de una sola nota |
| Tratar `Estilo` como contexto y no como núcleo | Un estilo más largo o más corto no es automáticamente mejor |
| Mantener advertencia sobre `Resultado` | Evita confundir contexto colectivo con calidad individual |

## Paso a paso del proceso de puntuación

### Resumen simple

Cada nota sale en cuatro pasos:

1. miramos el dato bruto del portero
2. vemos en qué posición queda frente al resto del grupo visible
3. convertimos esa posición en una nota relativa `0-100`
4. combinamos esas notas por bloques y luego combinamos los bloques

### Paso 1. Tomamos los datos brutos del portero

Ejemplo real: `J. Ruiz` (`Atlético Malagueño`, `2RFEF`, `Grupo IV`)

#### Datos de juego de pies

| Métrica | Valor |
|---|---:|
| `received_pass_avg` | 32.76 |
| `passes_avg` | 47.45 |
| `accurate_passes_percent` | 90.48 |
| `forward_passes_avg` | 24.85 |
| `successful_forward_passes_percent` | 83.33 |
| `short_medium_pass_avg` | 30.88 |
| `accurate_short_medium_pass_percent` | 98.78 |
| `long_passes_avg` | 16.57 |
| `successful_long_passes_percent` | 75.00 |
| `average_pass_length` | 30.44 |
| `average_long_pass_length` | 43.80 |

#### Datos de paradas

| Métrica | Valor |
|---|---:|
| `shots_against_avg` | 5.27 |
| `save_percent` | 71.43 |
| `prevented_goals_avg` | 0.215 |
| `xg_save_avg` | 1.72 |
| `goalkeeper_exits_avg` | 2.26 |
| `gk_aerial_duels_avg` | 1.13 |
| `conceded_goals_avg` | 1.51 |
| `clean_sheets` | 0.00 |

### Paso 2. Comparamos cada métrica con el resto de porteros visibles

La app no dice solo “J. Ruiz da 47.45 pases”.

Hace una pregunta mejor:

- “¿47.45 pases es mucho o poco comparado con los demás porteros que estoy viendo ahora mismo?”

Eso convierte el dato bruto en una posición relativa.

Ejemplo:

- si casi nadie da tantos pases como él, esa métrica se va cerca de `100`
- si está en la mitad, se acerca a `50`
- si está abajo, se acerca a `0`

### Paso 3. Creamos la nota de cada bloque

#### Juego de pies

Con esa comparación relativa, J. Ruiz obtiene estas notas por bloque:

| Bloque | Nota del bloque |
|---|---:|
| Participación | 100.00 |
| Precisión global | 91.07 |
| Progresión | 95.97 |
| Juego corto/medio | 87.04 |
| Juego largo | 80.75 |
| Estilo | 27.72 |

Cómo leerlo:

- `Participación = 100.00`
  - participa muchísimo con balón frente al grupo visible
- `Precisión global = 91.07`
  - además pasa muy limpio
- `Progresión = 95.97`
  - también destaca mucho al jugar hacia delante
- `Estilo = 27.72`
  - su longitud media de pase no lo coloca entre los más directos del grupo; su estilo tiende más a otra forma de repartir

#### Paradas

Sus notas de portería salen así:

| Bloque | Nota del bloque |
|---|---:|
| Carga defensiva | 86.79 |
| Parada | 77.11 |
| Dominio de área | 93.80 |
| Resultado | 16.58 |

Cómo leerlo:

- `Carga defensiva = 86.79`
  - vive bastante exigencia
- `Parada = 77.11`
  - responde bien bajo remate
- `Dominio de área = 93.80`
  - sale fuerte y compite bien por arriba
- `Resultado = 16.58`
  - aquí sale bajo, probablemente porque encaja bastante y no suma porterías a cero; este bloque está más contaminado por contexto de equipo

### Paso 4. Combinamos los bloques con sus pesos

#### Fórmula de `Juego de pies`

Se hace una media ponderada:

`(Participación × 1.00 + Precisión global × 1.10 + Progresión × 1.20 + Juego corto/medio × 1.00 + Juego largo × 1.15 + Estilo × 0.50) / (1.00 + 1.10 + 1.20 + 1.00 + 1.15 + 0.50)`

Aplicado a J. Ruiz:

`(100.00×1.00 + 91.07×1.10 + 95.97×1.20 + 87.04×1.00 + 80.75×1.15 + 27.72×0.50) / 5.95 = 85.56`

Resultado final:

- `Juego de pies = 85.56`

#### Fórmula de `Paradas`

`(Carga defensiva × 0.95 + Parada × 1.50 + Dominio de área × 0.85 + Resultado × 0.60) / (0.95 + 1.50 + 0.85 + 0.60)`

Aplicado a J. Ruiz:

`(86.79×0.95 + 77.11×1.50 + 93.80×0.85 + 16.58×0.60) / 3.90 = 73.79`

Resultado final:

- `Paradas = 73.79`

## Cómo interpretar el ejemplo

En el caso de `J. Ruiz`, la lectura final sería:

- es un portero muy fuerte en `juego de pies`
- también da una nota buena en `paradas`
- su gran punto débil no está tanto en la parada o el área, sino en el bloque `Resultado`, que está muy afectado por goles recibidos y porterías a cero

Traducido a lenguaje de scouting:

- con balón destaca claramente
- en portería responde bien
- el contexto del equipo le castiga más en el resultado final que en la respuesta individual

### Producto objetivo

- Primera meta funcional: dashboard visual de situación de mercado.
- Segunda meta funcional: informes individuales de jugadores seleccionados.
- Stack recomendado para esta fase: `Streamlit`.

## Criterios funcionales confirmados para porteros

- No se excluirá a nadie de inicio por minutos, edad, cesión o cantera.
- La primera versión incluirá filtros para poder aislar después los perfiles que interesen.
- Se incluirá un filtro de partidos mínimos.
- Se incluirá un filtro de `% total de minutos disputados`.
- La primera pantalla combinará:
  - vista general del mercado
  - ranking operativo de porteros
- La visual principal debe mostrar la distribución de porteros por edad frente a minutos disputados.
- Debe existir filtro por:
  - `1RFEF`: total, Grupo I, Grupo II
  - `2RFEF`: total, Grupo I, Grupo II, Grupo III, Grupo IV, Grupo V

## Próximas decisiones pendientes

- Fijar reglas de limpieza para cantera, duplicados y registros incompletos.
- Definir filtros mínimos para scouting de porteros: minutos, edad, valor y cesión.
- Decidir si la primera visualización debe priorizar ranking, mapa del mercado o fichas comparativas.
- Confirmar si queremos etiquetar perfiles de portero desde el inicio o arrancar solo con métricas descriptivas.

## Hallazgos útiles para la primera fase

### 1RFEF y 2RFEF

- `1RFEF_2025-26.csv`: 1176 jugadores
- `2RFEF_2025-26.csv`: 2449 jugadores
- Porteros por posición principal:
  - `1RFEF`: 94
  - `2RFEF`: 194

### Unionistas en el dataset actual

- Unionistas aparece ya en `1RFEF`.
- Hay 25 registros asociados al club en ese fichero.
- Esto permite plantear más adelante comparativas internas con jugadores actuales usando el mismo origen de datos.

### Riesgos de calidad detectados

- Hay jugadores de cantera mezclados con el pool principal.
- Existen algunos registros duplicados o muy parecidos.
- Hay filas con competición vacía o con muestras muy pequeñas de minutos.

## Primera entrega operativa

### Artefactos creados

- App principal: `app.py`
- Script de construcción: `scripts/build_goalkeeper_market_dashboard.py`

### Qué hace esta primera versión

- Extrae porteros de `1RFEF` y `2RFEF`.
- Deduplica registros repetidos cuando un mismo portero aparece varias veces con el mismo contexto.
- Mantiene dentro del universo a cantera, cedidos y casos fuera de la liga objetivo, pero los marca para poder filtrarlos.
- Enriquece el dato con grupo de competición cuando el equipo puede mapearse.
- Muestra una visual de `edad vs minutos disputados` en una app de Streamlit.
- Incluye ranking visible con filtros operativos.
- Incluye una ficha rápida del portero seleccionado.
- Permite descargar la selección filtrada en CSV.
- Incluye perfiles de portero para ordenar el ranking por ajuste al perfil.

### Perfiles de portero ya montados

- `Portero con los pies`
  - Basado en el rol del documento.
  - Usa las métricas de pase realmente disponibles en el dataset.

- `Portero de paradas`
  - Basado en el rol del documento.
  - Usa métricas de paradas, goles evitados, volumen defensivo y dominio del área.

- `Libre`
  - Permite construir un perfil propio seleccionando métricas de portero.
  - Cada métrica puede ponderarse manualmente.
  - El usuario puede indicar también si quiere premiar valores altos o bajos.

### Lógica actual del scoring de perfiles

- El ajuste al perfil se calcula con percentiles por métrica dentro del conjunto visible.
- Después se agregan según el peso definido para cada métrica.
- Esto permite adaptar el ranking al filtro actual y al perfil elegido.
- Es una primera aproximación útil para scouting exploratorio, no un modelo final cerrado.

### Filtros incluidos

- Competición: total, `1RFEF`, `2RFEF`
- Grupo: según la competición elegida
- Búsqueda por jugador o equipo
- Partidos mínimos
- `% mínimo de minutos`
- Solo equipos de la competición objetivo
- Incluir o excluir cantera
- Incluir o excluir cedidos
- Incluir o excluir casos `Sin grupo`

### Estado actual del universo de porteros

- Total porteros exportados tras deduplicación: `285`
- `1RFEF`: `94`
- `2RFEF`: `191`

### Cobertura actual del mapeo de grupos

- `1RFEF`: 89 de 94 porteros con grupo asignado
- `2RFEF`: 177 de 191 porteros con grupo asignado

Los casos sin grupo suelen corresponder a:

- equipos de cantera o juveniles
- equipos fuera de la competición objetivo
- nombres de club no homogéneos en origen

### Criterio actual para el porcentaje de minutos

- Se calcula usando 90 minutos por partido como base teórica.
- `1RFEF`: 38 partidos
- `2RFEF`: 34 partidos
- El valor se limita a `100%` para evitar que el tiempo añadido distorsione la escala.

### Referencias usadas para reconstruir grupos

Fuentes consultadas el `2026-06-09`:

- Primera Federación 2025-26: https://es.wikipedia.org/wiki/Primera_Federaci%C3%B3n_2025-26
- Segunda Federación 2025-26: https://es.wikipedia.org/wiki/Segunda_Federaci%C3%B3n_2025-26
- Resumen de grupos de Segunda Federación 2025-26: https://amp.marca.com/futbol/segunda-rfef/2025/06/27/son-grupos-segunda-federacion-2025-26.html

### Reutilización de trabajo previo

Se ha revisado también el proyecto `Unionistas` en:

- `/Users/macmontxinho/Desktop/Teams/Unionistas/scouting/src/scouting_app/calendar_data.py`

Hallazgo útil:

- Allí no aparece una tabla fija de grupos para el scouting Wyscout.
- El grupo se obtiene desde el calendario de SofaScore.
- Sí existe una capa muy útil de alias y normalización de nombres de equipo para `1RFEF` y `2RFEF`.
- Esa lógica de alias se ha reutilizado parcialmente en nuestro script para reducir ruido en nombres de club.

## Registro de avances

### 2026-06-12

- Corregido el campograma cuando una métrica no existe en el conjunto filtrado.
- Los máximos visibles de corto/medio, largo, lateral, pases recibidos y longitud media ahora gestionan de forma segura columnas ausentes, muestras vacías, valores `NaN` y máximos iguales a cero.
- Aplicada la misma protección a la sección de contribución ofensiva para evitar errores con descargas que no incluyan alguna de sus métricas.
- El pase lateral no existe como columna directa en los CSV de Wyscout disponibles. Se mantiene como estimación transparente: `pases totales - pases hacia delante - pases hacia atrás`.
- La estimación lateral puede calcularse para 280 de 285 porteros y es positiva para 279; se recalcula dentro de la app para evitar que una caché antigua muestre ceros falsos.
- El campograma muestra el valor `/90` del jugador dentro de cada tarjeta, el máximo visible sobre la trayectoria de fondo y los percentiles en la leyenda inferior.
- La contribución ofensiva se coloca en una columna junto al campograma, sin pases clave, y el contexto contractual/físico se integra en la cabecera del jugador.
- Las nacionalidades se muestran en castellano con bandera y se conservan las dobles nacionalidades disponibles en pasaporte.

### 2026-06-09

- Revisada la estructura inicial de carpetas del workspace.
- Inventariados los CSV disponibles y los activos visuales.
- Detectadas primeras señales de ruido en los datos.
- Leído el documento de roles adjunto para convertirlo más adelante en lógica de scouting.
- Confirmado el alcance inicial con foco en `1RFEF` y `2RFEF`.
- Confirmada la prioridad inicial en porteros y el objetivo final de dashboard más informes individuales.
- Reorientada la primera maqueta hacia una app en `Streamlit`, que pasa a ser la base del producto.
- Montada una primera app de porteros con filtros por competición, grupo, minutos y contexto.
