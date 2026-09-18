# Fuentes jurídicas locales (corpus legal — Top 3)

Copias **oficiales en PDF** descargadas desde Internet para el MVP de análisis de contratos de arrendamiento inmobiliario en **Jalisco, México**. Sirven como respaldo documental y como insumo del **corpus CAG** (`cag-corpus-v1.md`) inyectado en análisis y chat; **no deben cargarse íntegras al contexto del LLM** — ver [Uso recomendado](#uso-recomendado-cag--rag).

| Campo | Valor |
|-------|--------|
| Descarga en repositorio | 16 de septiembre de 2026 |
| Carpeta | `docs/legal-sources/` |
| Requerimientos relacionados | RF-32′, RF-34′ en [requirements.md](../requirements.md) |

---

## 1. Código Civil del Estado de Jalisco

| | |
|--|--|
| **Archivo** | [`codigo-civil-jalisco.pdf`](./codigo-civil-jalisco.pdf) (~2,2 MB) |
| **Fuente** | [Congreso del Estado de Jalisco — Biblioteca Virtual](https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/busquedasleyes/ListadoCr3.cfm) |
| **URL directa** | `https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/legislacion/Códigos/Documentos_PDF-Códigos/Código Civil del Estado de Jalisco-240626.pdf` |
| **Última modificación (catálogo legislativo)** | 18/06/2026 (según índice del Congreso) |

### De qué se trata

Código **estatal** que regula, entre otras materias, el **contrato de arrendamiento** de bienes en Jalisco. Para inmuebles ubicados en la entidad, es la **norma sustantiva principal** que debe fundamentar hallazgos y chat cuando la jurisdicción detectada es Jalisco.

### Contenido relevante para arrendamiento (recorte CAG)

**Título VI — Del arrendamiento (artículos 1980–2146)**, en particular:

| Bloque | Artículos | Temas |
|--------|-----------|--------|
| Disposiciones generales | 1980–1994 | Definición, renta, formalidades |
| Obligaciones del arrendador | 1995–2004 | Entrega, conservación, reparaciones |
| Obligaciones del arrendatario | 2005–2022 | Pago, uso, desocupación, servicios |
| Inmuebles (general) | 2023–2037 | **Contenido mínimo del contrato**, plazo indefinido (2034–2035) |
| Habitación | 2038–2044 | Topes de renta y orden público (2041–2043), prórroga |
| Comercio / industria | 2045–2053+ | Plazos y renta en locales comerciales |
| Subarriendo | 2136–2139 | Subarrendamiento |
| Terminación | 2140–2146 | Rescisión y fin del contrato |

El PDF incluye **todo el código civil** (personas, familia, obligaciones, compraventa, etc.). Solo el título anterior interesa para el corpus de arrendamiento.

---

## 2. Código Civil Federal

| | |
|--|--|
| **Archivo** | [`codigo-civil-federal.pdf`](./codigo-civil-federal.pdf) (~3,3 MB) |
| **Fuente** | [Cámara de Diputados — LeyesBiblio](https://www.diputados.gob.mx/LeyesBiblio/ref/ccf.htm) |
| **URL directa** | `https://www.diputados.gob.mx/LeyesBiblio/pdf/CCF.pdf` |
| **Texto vigente (encabezado PDF)** | Última reforma DOF **14-11-2025** |

### De qué se trata

Código **federal** de aplicación supletoria y, en algunos supuestos, directa. Para **arrendamiento de inmuebles**, el artículo **13, fracción III** establece que rige el **derecho del lugar de ubicación** del inmueble (en la práctica del MVP: CC Jalisco). El CCF sigue siendo útil como **marco de conflicto de leyes** y referencia en **muebles**, plazos y estructura del título de arrendamiento federal.

### Contenido relevante para arrendamiento (recorte CAG)

| Bloque | Artículos | Temas |
|--------|-----------|--------|
| Disposiciones preliminares | **13** (fr. III), 12–14 | Qué ley aplica al arrendamiento de inmuebles |
| Título VI — Del arrendamiento | **2398–2496** | Contrato, obligaciones, habitación (2448–2452), subarriendo, terminación |

No usar el PDF completo en CAG: extraer solo los artículos indicados.

---

## 3. Código de Procedimientos Civiles del Estado de Jalisco

| | |
|--|--|
| **Archivo** | [`codigo-procedimientos-civiles-jalisco.pdf`](./codigo-procedimientos-civiles-jalisco.pdf) (~1,3 MB) |
| **Fuente** | [Congreso del Estado de Jalisco — Biblioteca Virtual](https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/busquedasleyes/ListadoCr3.cfm) |
| **URL directa** | `https://congresoweb.congresojal.gob.mx/BibliotecaVirtual/legislacion/Códigos/Documentos_PDF-Códigos/Código de Procedimientos Civiles del Estado de Jalisco-250424.pdf` |
| **Referencia legislativa (catálogo)** | A.I. 9/2022; actualización catalogada 05/09/2023 |

### De qué se trata

Código **procesal estatal**: reglas para llevar controversias civiles ante tribunales de Jalisco. Complementa el análisis sustantivo cuando el contrato o el chat abordan **desocupación, mora, vencimiento del plazo o recuperación del inmueble**.

### Contenido relevante para arrendamiento (recorte CAG)

| Bloque | Artículos (aprox.) | Temas |
|--------|-------------------|--------|
| Juicio sumario por **desocupación** | **683–692** (verificar **692 BIS** en el PDF vigente) | Causales (vencimiento, plazo legal, falta de pago), trámite y **plazo de desocupación** (p. ej. art. 688: 15 días naturales) |

El resto del código (ejecutivo mercantil, familia, medios preparatorios, etc.) queda fuera del corpus v1 de arrendamiento.

---

## Uso recomendado (CAG / RAG)

1. **Almacenamiento en repo:** estos PDF son la **fuente autorizada** offline; conviene re-descargar periódicamente desde las mismas URLs y actualizar esta nota.
2. **Pipeline de IA:** generar chunks solo de los **rangos de artículos** listados arriba (JSON/JSONL con `instrument`, `article`, `jurisdiction`, `source_url`).
3. **CAG:** precargar **recortes**, no los tres PDF completos (cientos de páginas).
4. **Citas en producto:** apuntar a artículo concreto + URL oficial; el path local es para desarrollo, no para usuarios finales.

## Corpus CAG (markdown)

| Archivo | Descripción |
|---------|-------------|
| [`cag-corpus-v1.md`](./cag-corpus-v1.md) | Artículos **curados** extraídos de los tres PDF para precarga CAG (~35 KB). |
| [`../../scripts/corpus/build_cag_corpus_markdown.py`](../../scripts/corpus/build_cag_corpus_markdown.py) | Regenera el markdown tras actualizar los PDF. |

```bash
python scripts/corpus/build_cag_corpus_markdown.py
```

## Integración en el backend (implementado)

El archivo [`cag-corpus-v1.md`](./cag-corpus-v1.md) se carga desde `backend/rag/cag_corpus.py` (ruta configurable `LEGAL_CAG_CORPUS_PATH`, default `docs/legal-sources/cag-corpus-v1.md` respecto a la raíz del repo). Se inyecta en prompts de **análisis** y **chat** vía `llm/prompts.py` y `llm/chat_provider.py`.

Regenerar el markdown tras actualizar PDFs:

```bash
python scripts/corpus/build_cag_corpus_markdown.py
```

**Próximo paso (producto):** índice vectorial RAG además del CAG estático; validación de citas contra PDF oficial en producción.
