GraphProp: Synthetic Document Factory + GraphRAG Multimodal para Preventa Técnica
Descripción general
GraphProp es un proyecto de tesis orientado a la generación de propuestas técnicas a partir de documentación empresarial, especialmente RFPs, anexos técnicos, actas y documentos de arquitectura. El sistema combina dos capacidades complementarias:

Synthetic Document Factory (SDF): módulo auxiliar para generar corpus documentales sintéticos consistentes y trazables.
GraphRAG multimodal: pipeline principal que ingesta documentos, construye un grafo de conocimiento en Neo4j, recupera contexto textual y multimodal, y genera propuestas técnicas contextualizadas.
La idea central es que el sistema no solo lea texto, sino que también aproveche relaciones de negocio, metadatos documentales, diagramas, tablas e imágenes presentes en los PDFs para producir respuestas y propuestas más coherentes.

Objetivo del proyecto
Desarrollar un sistema basado en GraphRAG multimodal que permita generar propuestas técnicas coherentes, trazables y contextualizadas a partir de documentación organizacional, integrando:

conocimiento estructurado de negocio,
conocimiento documental fragmentado en chunks,
contexto multimodal derivado de páginas, diagramas y tablas,
y una interfaz de usuario para carga documental y generación de propuestas.
Cómo se combinan SDF y GraphRAG
El repositorio integra dos capas funcionales:

1. Synthetic Document Factory (SDF)
SDF no es el núcleo de inferencia, sino una herramienta auxiliar de generación de datos sintéticos. Su propósito es poblar el sistema con un universo documental consistente cuando no se dispone de suficientes documentos reales.

SDF genera, entre otros:

RFPs,
RFP_QA,
actas o meeting minutes,
anexos técnicos AS-IS / TO-BE,
historiales de proyectos y documentación relacionada.
Su enfoque es Entity-First: primero define entidades en una base semilla, luego genera documentos consistentes alrededor de esas entidades. Esto evita contradicciones entre documentos relacionados.

2. GraphRAG multimodal
Una vez que los documentos existen —ya sean sintéticos o cargados manualmente— el pipeline GraphRAG:

los clasifica,
extrae texto,
los divide en chunks,
genera embeddings,
crea MultiModalChunk para enriquecer el retrieval,
los inserta en Neo4j,
construye workspaces de consulta,
y genera propuestas técnicas contextualizadas.
En otras palabras:

SDF genera el corpus → GraphRAG lo estructura, recupera y explota para inferencia.

Arquitectura conceptual
El sistema puede entenderse en cinco capas:

1. Capa semilla / datos sintéticos
Base SQLite con entidades base.
Generación de documentos consistentes para poblar el ecosistema.
2. Capa documental
PDFs originales almacenados en output/Banco/Proyecto/RFP/.
Archivos XMP asociados para trazabilidad documental.
3. Capa GraphRAG documental
SourceDocument
Chunk
MultiModalChunk
Page
Esta capa representa el conocimiento documental fragmentado y enriquecido.

4. Capa Master KG / negocio
Representa entidades de negocio como:

BankEntity
ProjectEntity
PersonnelEntity
RegulationEntity
BankProfile
Esto permite pasar de un RAG puramente textual a un GraphRAG contextualizado por banco y proyecto.

5. Capa Workspace / consulta
El workspace funciona como una vista dinámica de consulta que:

recibe un requerimiento,
recupera chunks textuales y multimodales relevantes,
los vincula al workspace,
y sirve como contexto inmediato para la generación de propuestas.
Flujo end-to-end
A. Generación de documentos sintéticos
Se inicializa la base de datos semilla.
Se generan documentos sintéticos coherentes por banco/proyecto.
Se renderizan PDFs corporativos y sus metadatos.
B. Ingesta GraphRAG
Carga de PDFs.
Extracción de texto.
Chunking.
Generación de embeddings.
Generación de MultiModalChunk.
Inserción en Neo4j.
Relación con banco y proyecto.
C. Generación de propuestas
Selección de banco y proyecto.
Construcción o reutilización de Workspace.
Retrieval híbrido textual + multimodal.
Construcción de prompt estructurado.
Generación de propuesta técnica.
Visualización en Streamlit.
Exportación en TXT y PDF.
Estructura del repositorio
La estructura general del proyecto incluye componentes de UI, API, scripts de pipeline y módulos de dominio. El repositorio contiene archivos como app_streamlit_preventa.py, graph_pipeline.py, scripts/phase_1/*, scripts/phase_2/*, además de carpetas src/, api/, config/, data/ y output/. La carpeta output guarda documentos organizados por banco y proyecto, y también directorios como rendered_pages y reports. fileciteturn14file3turn14file2

Resumen de carpetas principales:

graphprop/
├── api/                    # API FastAPI opcional
├── config/                 # Configuración y estilos
├── data/                   # seed.db y datos auxiliares
├── output/                 # Documentos organizados por Banco/Proyecto/RFP
├── scripts/
│   ├── phase_0/            # Carga de seed data
│   ├── phase_1/            # Construcción del grafo documental y master KG
│   └── phase_2/            # Workspaces y generación de propuesta
├── src/
│   ├── phase_0/            # SDF, modelos, rendering, llm y workflow
│   ├── phase_1/            # Ingesta documental y KG
│   └── phase_2/            # Retrieval, workspace y orquestación
├── app_streamlit_preventa.py
├── graph_pipeline.py
├── README.md
└── requirements.txt
Componentes funcionales clave
Synthetic Document Factory
Base semilla en SQLite.
Generación de esqueletos estructurados.
Expansión narrativa con LLM.
Renderizado a PDF.
Metadatos XMP para trazabilidad.
Ingesta documental
Lectura de PDFs.
Clasificación por tipo documental.
Extracción y limpieza de texto.
Chunking textual.
Representación multimodal por página.
Knowledge Graph
Construcción de Document KG.
Construcción de Master KG.
Relaciones entre documentos, bancos y proyectos.
Retrieval híbrido
Recuperación de chunks textuales.
Recuperación de chunks multimodales.
Filtros por banco, tipo documental y estado arquitectónico.
Generación de propuestas
Construcción de workspace.
Ensamblaje de contexto.
Prompt estructurado.
Generación de propuesta final.
Interfaz Streamlit
Carga documental por banco y proyecto.
Validación de archivos.
Ejecución de pipeline.
Generación y descarga de propuestas.
Requisitos previos
Requisitos de sistema
Según el flujo de renderizado de documentos sintéticos, el proyecto requiere dependencias de sistema para renderizar PDFs como pandoc y pango. El README previo del módulo SDF ya lo indicaba. fileciteturn13file0

Ubuntu / Debian
sudo apt-get update
sudo apt-get install pandoc libpango-1.0-0 libpangoft2-1.0-0
macOS
brew install pandoc pango
Windows
Instalar Pandoc.
Instalar dependencias necesarias para WeasyPrint según su documentación.
Tener Neo4j Desktop o una instancia Neo4j/Aura accesible.
Instalación
1. Clonar el repositorio
git clone <url-del-repositorio>
cd graphprop
2. Crear entorno virtual
python -m venv venv
Activación en Windows PowerShell
.\venv\Scripts\Activate.ps1
Activación en CMD
venv\Scripts\activate
3. Instalar dependencias
pip install -r requirements.txt
4. Configurar variables de entorno
Crea o completa .env con al menos:

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=tu_password
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
Ajusta las variables según el proveedor LLM que uses realmente.

Inicialización de datos sintéticos
Para poblar la base semilla:

python scripts/phase_0/seed_db.py
Esto crea el universo ficticio base de bancos, proyectos y entidades relacionadas, que luego sirve como fuente para la generación de documentos sintéticos. El README previo de SDF ya documentaba este flujo de inicialización y su propósito de mantener la consistencia entre documentos. fileciteturn13file0

Ejecución del pipeline GraphRAG
1. Construcción del grafo documental
python -m scripts.phase_1.build_general_kg
2. Construcción del master graph
python -m scripts.phase_1.build_master_kg
3. Construcción de workspace
python -m scripts.phase_2.build_workspace --workspace-id "Banco_X_Proyecto_Y" --requirement-text "Generar propuesta técnica..." --bank-name "Banco X"
4. Generación de propuesta
python -m scripts.phase_2.generate_proposal --workspace-id "Banco_X_Proyecto_Y"
El resumen técnico del proyecto confirma que el flujo actual incluye ingesta, construcción de grafo, retrieval contextual, workspace y generación automática de propuestas, además de una interfaz Streamlit funcional. fileciteturn14file0turn14file1

Ejecución de la interfaz Streamlit
streamlit run app_streamlit_preventa.py
La app incluye dos módulos principales:

Subir archivos: define banco y proyecto, guarda documentos y ejecuta el pipeline.
Generar propuesta: selecciona banco/proyecto o usa prompt, construye contexto y genera la propuesta. Esto está alineado con el resumen funcional del sistema GraphRAG multimodal. fileciteturn14file0turn14file1
Convención de almacenamiento documental
Los documentos se almacenan con estructura:

output/
└── Banco/
    └── Proyecto/
        └── RFP/
            ├── *_RFP_*.pdf
            ├── *_RFP_QA_*.pdf
            ├── *_MEETING_MINUTES_*.pdf
            ├── *_TECHNICAL_ANNEX_*_Arquitectura_AS-IS.pdf
            └── *_TECHNICAL_ANNEX_*_Arquitectura_TO-BE.pdf
La carpeta rendered_pages guarda representaciones por página generadas durante el procesamiento multimodal, mientras que reports puede utilizarse para salidas auxiliares o reportes del pipeline. La estructura cargada en el proyecto muestra ambos directorios dentro de output. fileciteturn14file3turn14file2

Tipos documentales manejados
RFP
RFP_QA
MEETING
TECHNICAL_ANNEX_AS_IS
TECHNICAL_ANNEX_TO_BE
Stack tecnológico
Lenguaje y framework
Python 3.12+
Streamlit
FastAPI
IA / LLM / Orquestación
LangGraph
PydanticAI
DSPy
OpenAI
Anthropic
Google Generative AI / Gemini
Knowledge Graph
Neo4j
Base de datos auxiliar
SQLite
SQLAlchemy
Renderizado documental
Pandoc
WeasyPrint
ReportLab
Markdown
XHTML2PDF
Testing
Pytest
Pytest-asyncio
La versión previa del README de SDF ya documentaba gran parte de este stack, especialmente LangGraph, PydanticAI, OpenAI, Anthropic, SQLite, Pandoc y WeasyPrint. fileciteturn13file0

Estado actual del sistema
El sistema se encuentra funcional end-to-end en los siguientes componentes:

ingesta documental,
construcción del grafo,
enriquecimiento multimodal,
retrieval contextual,
generación automática de propuestas,
e interfaz funcional.
Ese estado quedó resumido explícitamente en el resumen detallado del proyecto. fileciteturn14file1

Limitaciones actuales
La calidad de la propuesta depende de la calidad del corpus y del retrieval.
El renderizado PDF de propuestas puede requerir postprocesamiento adicional del formato generado por LLM.
El pipeline multimodal depende de configuración correcta de modelo, rutas y proveedor.
La consistencia del entorno Python y Neo4j es crítica para que la app funcione sin errores.
Próximos pasos sugeridos
Exportación más robusta de propuestas a PDF.
Mejora del postprocesamiento del texto generado.
Evaluación formal del modelo.
Comparación automática AS-IS vs TO-BE.
Integración con fuentes documentales empresariales reales.
Estos próximos pasos también aparecen alineados con el resumen funcional del proyecto. fileciteturn14file1

Seguridad
No subir .env al repositorio.
El entorno sintético evita exponer información real sensible.
Si se integran documentos reales, deben aplicarse controles adicionales de seguridad, anonimización y cumplimiento.
Licencia
Definir según el esquema institucional o académico del proyecto.
