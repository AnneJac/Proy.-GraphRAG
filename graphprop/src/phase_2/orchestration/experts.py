import os
from google import genai


SYSTEM_BASE = """
Eres un consultor senior en tecnología, arquitectura empresarial y diseño de soluciones.
Responde de forma profesional, técnica, clara y bien estructurada.
No inventes información fuera del contexto proporcionado.
Si falta información, indícalo explícitamente.
Redacta en español formal.
"""


def call_llm(prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        return "ERROR: No se encontró GOOGLE_API_KEY."

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text if getattr(response, "text", None) else ""


def experto_empresarial(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Arquitecto Empresarial.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. alineación estratégica,
2. capacidades de negocio involucradas,
3. impacto organizacional,
4. valor esperado para la entidad.
"""
    return call_llm(prompt)


def experto_soluciones(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Arquitecto de Soluciones.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. arquitectura lógica,
2. componentes principales,
3. integraciones necesarias,
4. escalabilidad y modularidad de la solución.
"""
    return call_llm(prompt)


def experto_infraestructura(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Especialista en Infraestructura.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. enfoque cloud/on-premise/híbrido,
2. disponibilidad,
3. despliegue y operación,
4. red, capacidad y escalabilidad técnica.
"""
    return call_llm(prompt)


def experto_ciberseguridad(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Especialista en Ciberseguridad.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. riesgos de seguridad,
2. controles recomendados,
3. cumplimiento normativo,
4. protección de datos e identidad.
"""
    return call_llm(prompt)


def experto_desarrollo(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Líder Técnico de Desarrollo.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. frontend,
2. backend,
3. APIs e integraciones,
4. impacto en sistemas existentes o legacy,
5. consideraciones de implementación.
"""
    return call_llm(prompt)


def experto_qa(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Especialista QA.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. estrategia de pruebas,
2. validación funcional,
3. validación técnica,
4. criterios de aceptación y calidad.
"""
    return call_llm(prompt)


def experto_riesgos(context: str, requirement: str) -> str:
    prompt = f"""{SYSTEM_BASE}

Actúa como Analista de Riesgos Tecnológicos.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

Analiza de forma estructurada:
1. riesgos técnicos,
2. riesgos operativos,
3. dependencias críticas,
4. supuestos y restricciones relevantes.
"""
    return call_llm(prompt)

def experto_integrador(context, requirement, expertos_output):
    prompt = f"""
Eres un arquitecto senior encargado de consolidar una propuesta final.

REQUERIMIENTO:
{requirement}

CONTEXTO:
{context}

ANÁLISIS DE EXPERTOS:
{expertos_output}

Genera una propuesta final estructurada:

1. Resumen ejecutivo
2. Entendimiento del problema
3. Arquitectura propuesta
4. Recomendaciones clave
5. Riesgos principales
6. Conclusión

Debe ser clara, integrada y sin redundancias.
"""
    return call_llm(prompt)