# TestLink Automation

Herramienta desktop en Python para automatizar el cargue masivo de casos de prueba desde Excel hacia TestLink.

## Funcionalidades

* Carga masiva de HUs/Test Suites.
* Carga masiva de casos de prueba.
* Carga de pasos y resultados esperados.
* Carga de precondiciones.
* Carga de Datos de Entrada.
* Procesamiento de múltiples hojas de Excel.
* Detección y control de duplicados.
* Registro visual de elementos creados, omitidos y con errores.
* Soporte para caracteres especiales, tildes y `ñ`.

## Requisitos

* Python 3.12 o compatible.
* Acceso al proyecto correspondiente en TestLink.
* DEVKEY propia de TestLink.

## Instalación

Clonar el repositorio y ejecutar:

```bash
pip install -r requirements.txt
```

Se recomienda utilizar un entorno virtual.

## Ejecución

Desde la raíz del proyecto:

```bash
python ui.py
```

Se abrirá la aplicación desktop.

## Uso

1. Ingresar la **DEVKEY propia de TestLink**.
2. Seleccionar el archivo Excel con el diseño de pruebas.
3. Pulsar **Cargar a TestLink**.
4. Revisar los resultados en:

   * **CREADOS**
   * **OMITIDOS**
   * **ERRORES**

No es necesario modificar el código para realizar una carga.

## Excel

El archivo debe conservar el formato de diseño de pruebas utilizado actualmente por el proyecto, incluyendo la estructura y fila de encabezados esperada por el parser.

La aplicación detecta automáticamente las hojas y procesa las HUs y casos de prueba encontrados.

## DEVKEY

Cada usuario debe utilizar su propia DEVKEY.

**No compartir DEVKEYs entre usuarios ni subirlas al repositorio.**

## Configuración del servidor

La URL del endpoint XML-RPC de TestLink está configurada internamente en la aplicación. El usuario únicamente necesita proporcionar su DEVKEY.

## Estado

Versión funcional para uso interno.

Actualmente se ejecuta mediante Python. La generación de una versión `.exe` queda como siguiente etapa.
