# -*- coding: utf-8 -*-

import os
import pprint
import re
import unicodedata
import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DEFAULT_EXCEL_FILE = os.path.join(BASE_DIR, "casos_prueba.xlsx")
# DEFAULT_EXCEL_FILE = os.path.join(BASE_DIR, "SIC-TP-ORD-266.xlsx")
DEFAULT_EXCEL_FILE = os.path.join(BASE_DIR, "casos_prueba_acumulados.xlsx")

# Los encabezados reales del Excel QA corporativo siempre estan en la fila
# visual 14 (las filas anteriores son metadata: DISEÑO DE PRUEBAS, GENERADO
# POR, ACTUALIZADO POR, etc).
HEADER_ROW = 13


MVP_FORMAT = "MVP_INICIAL"
REAL_QA_FORMAT = "QA_REAL"

MVP_COLUMNS = [
    "HU_NAME",
    "HU_DESCRIPTION",
    "CP_ID",
    "CP_SUMMARY",
    "PRECONDITIONS",
    "STEP_NUMBER",
    "STEP_ACTION",
    "EXPECTED_RESULT",
]

REAL_QA_COLUMNS = [
    "ID REQUERIMIENTO",
    "DESCRIPCIÓN",
    "PRECONDICIONES",
    "DATOS DE ENTRADA",
    "ID CASO DE PRUEBA",
    "DESCRIPCIÓN DE LA PRUEBA",
    "GUIÓN DE LA PRUEBA",
    "RESULTADO ESPERADO",
]

INVISIBLE_CHARACTERS = [
    "\ufeff",  # BOM
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\u2060",  # word joiner
]

CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

HEADER_ALIASES = {
    "ID REQUERIMIENTO": "ID REQUERIMIENTO",
    "DESCRIPCION": "DESCRIPCIÓN",
    "PRECONDICIONES": "PRECONDICIONES",
    "DATOS DE ENTRADA": "DATOS DE ENTRADA",
    "ID CASO DE PRUEBA": "ID CASO DE PRUEBA",
    "DESCRIPCION DE LA PRUEBA": "DESCRIPCIÓN DE LA PRUEBA",
    "GUION DE LA PRUEBA": "GUIÓN DE LA PRUEBA",
    "RESULTADO ESPERADO": "RESULTADO ESPERADO",
    "HU_NAME": "HU_NAME",
    "HU_DESCRIPTION": "HU_DESCRIPTION",
    "CP_ID": "CP_ID",
    "CP_SUMMARY": "CP_SUMMARY",
    "PRECONDITIONS": "PRECONDITIONS",
    "STEP_NUMBER": "STEP_NUMBER",
    "STEP_ACTION": "STEP_ACTION",
    "EXPECTED_RESULT": "EXPECTED_RESULT",
}


def sanitize_text(value):
    if pd.isna(value):
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")

    for character in INVISIBLE_CHARACTERS:
        text = text.replace(character, "")

    text = CONTROL_CHARACTER_PATTERN.sub("", text)
    text = unicodedata.normalize("NFC", text)
    return text


def clean_header(value):
    text = sanitize_text(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_header_key(value):
    text = clean_header(value).upper()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^#\s*", "", text)
    return text.strip()


def canonical_header(value):
    header = clean_header(value)
    header_key = normalize_header_key(header)
    return HEADER_ALIASES.get(header_key, header)


def is_unnamed_header(value):
    return normalize_header_key(value).startswith("UNNAMED")


def clean_value(value):
    if pd.isna(value):
        return ""

    return sanitize_text(value).strip()


def clean_multiline_value(value):
    text = clean_value(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def normalize_dataframe_columns(df):
    df = df.copy()
    df.columns = [canonical_header(column) for column in df.columns]
    df = df.loc[:, [not is_unnamed_header(column) for column in df.columns]]
    return df


def sanitize_dataframe_text(df):
    df = df.copy()

    for column in df.columns:
        df[column] = df[column].apply(
            lambda value: sanitize_text(value) if isinstance(value, str) else value
        )

    return df


def has_columns(df, expected_columns):
    for expected_column in expected_columns:
        if expected_column not in df.columns:
            return False

    return True


def detect_excel_format(df):
    if df is None:
        return None

    if has_columns(df, REAL_QA_COLUMNS):
        return REAL_QA_FORMAT

    if has_columns(df, MVP_COLUMNS):
        return MVP_FORMAT

    return None


def print_missing_columns(df, expected_columns, title):
    missing_columns = []

    for expected_column in expected_columns:
        if expected_column not in df.columns:
            missing_columns.append(expected_column)

    print(f"\nCOLUMNAS FALTANTES PARA {title}:")

    if not missing_columns:
        print("- Ninguna")
        return

    for column in missing_columns:
        print(f"- {column}")


def read_excel(file_path=DEFAULT_EXCEL_FILE):

    try:

        print("\nLeyendo archivo Excel...")
        print(f"Archivo: {file_path}")
        print(f"Fila de header usada (fija): {HEADER_ROW}")

        df = pd.read_excel(file_path, header=HEADER_ROW, engine="openpyxl")
        df = normalize_dataframe_columns(df)
        df = sanitize_dataframe_text(df)

        columns = list(df.columns)
        excel_format = detect_excel_format(df)

        print("\nCOLUMNAS DETECTADAS:")
        for column in columns:
            print(f"- {column}")

        print(f"\nFILAS ENCONTRADAS: {len(df)}")

        if excel_format:
            print(f"\nFORMATO DETECTADO: {excel_format}")
            print("Estructura basica del Excel OK")
        else:
            print("\nNo se pudo detectar un formato soportado.")
            print_missing_columns(df, REAL_QA_COLUMNS, REAL_QA_FORMAT)
            print_missing_columns(df, MVP_COLUMNS, MVP_FORMAT)

        print("\nPRIMERAS FILAS:")
        print(df.head().to_string(index=False))

        return df

    except FileNotFoundError:

        print("\nERROR LECTURA EXCEL:")
        print(f"No se encontro el archivo: {file_path}")
        return None

    except Exception as e:

        print("\nERROR LECTURA EXCEL:")
        print(e)
        return None


def read_excel_all_sheets(file_path=DEFAULT_EXCEL_FILE):

    try:

        print("\nLeyendo archivo Excel (todas las hojas)...")
        print(f"Archivo: {file_path}")
        print(f"Fila de header usada (fija): {HEADER_ROW}")

        excel_file = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_names = excel_file.sheet_names

        print("\n[INFO] Hojas detectadas:")
        for sheet_name in sheet_names:
            print(f"- {sheet_name}")

        sheets = {}

        for sheet_name in sheet_names:

            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=HEADER_ROW)
                df = normalize_dataframe_columns(df)
                df = sanitize_dataframe_text(df)
                sheets[sheet_name] = df

            except Exception as e:

                print(f"\nERROR LEYENDO HOJA '{sheet_name}':")
                print(e)
                sheets[sheet_name] = None

        return sheets

    except FileNotFoundError:

        print("\nERROR LECTURA EXCEL:")
        print(f"No se encontro el archivo: {file_path}")
        return {}

    except Exception as e:

        print("\nERROR LECTURA EXCEL:")
        print(e)
        return {}


def clean_step_number(value, fallback):
    if pd.isna(value):
        return fallback

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def first_value(df, column_name):
    values = df[column_name].dropna()

    if values.empty:
        return ""

    return clean_multiline_value(values.iloc[0])


def parse_numbered_steps(text):
    text = clean_multiline_value(text)

    if not text:
        return []

    matches = list(re.finditer(r"(?m)(?:^|\n)\s*(\d+)[.)]\s+", text))

    if not matches:
        return [text]

    steps = []

    for index, match in enumerate(matches):
        start = match.end()
        end = len(text)

        if index + 1 < len(matches):
            end = matches[index + 1].start()

        step_text = text[start:end].strip()

        if step_text:
            steps.append(step_text)

    return steps


def build_expected_results_for_steps(expected_result, step_count):
    expected_result = clean_multiline_value(expected_result)

    if step_count == 0:
        return []

    if not expected_result:
        return [""] * step_count

    expected_items = parse_numbered_steps(expected_result)

    if len(expected_items) == step_count:
        return expected_items

    if step_count == 1:
        return [expected_result]

    expected_results = [""] * step_count
    expected_results[-1] = expected_result
    return expected_results


def build_real_qa_steps(row, cp_id, start_step_number):
    raw_script = row["GUIÓN DE LA PRUEBA"]
    raw_expected_result = row["RESULTADO ESPERADO"]

    detected_steps = parse_numbered_steps(raw_script)
    expected_results = build_expected_results_for_steps(raw_expected_result, len(detected_steps))

    print("\nSTEPS DETECTADOS:")
    print(f"CP: {cp_id}")
    print(f"Steps detectados en GUIÓN DE LA PRUEBA: {len(detected_steps)}")

    parsed_steps = []

    for index, action in enumerate(detected_steps):
        step_number = start_step_number + index
        expected_result = expected_results[index]

        step_item = {
            "step_number": step_number,
            "actions": action,
            "expected_results": expected_result,
        }

        parsed_steps.append(step_item)

        print(f"- Step {step_number}: {action}")
        print(f"  Expected: {expected_result}")

    return parsed_steps


def validate_columns(df):
    excel_format = detect_excel_format(df)

    if excel_format:
        return True

    print("\nERROR ESTRUCTURA EXCEL:")
    print("El archivo no tiene las columnas obligatorias de un formato soportado.")
    print_missing_columns(df, REAL_QA_COLUMNS, REAL_QA_FORMAT)
    print_missing_columns(df, MVP_COLUMNS, MVP_FORMAT)
    return False


def build_mvp_structure(df):
    testlink_structure = []

    for hu_name, hu_df in df.groupby("HU_NAME", sort=False):
        hu_item = {
            "hu_name": clean_value(hu_name),
            "hu_description": first_value(hu_df, "HU_DESCRIPTION"),
            "test_cases": [],
        }

        for cp_id, cp_df in hu_df.groupby("CP_ID", sort=False):
            cp_item = {
                "cp_id": clean_value(cp_id),
                "summary": first_value(cp_df, "CP_SUMMARY"),
                "preconditions": first_value(cp_df, "PRECONDITIONS"),
                "input_data": "",
                "steps": [],
            }

            sorted_steps = cp_df.copy()
            sorted_steps["_STEP_ORDER"] = pd.to_numeric(sorted_steps["STEP_NUMBER"], errors="coerce")
            sorted_steps = sorted_steps.sort_values("_STEP_ORDER")

            for index, row in enumerate(sorted_steps.to_dict("records"), start=1):
                step_item = {
                    "step_number": clean_step_number(row["STEP_NUMBER"], index),
                    "actions": clean_multiline_value(row["STEP_ACTION"]),
                    "expected_results": clean_multiline_value(row["EXPECTED_RESULT"]),
                }

                cp_item["steps"].append(step_item)

            hu_item["test_cases"].append(cp_item)

        testlink_structure.append(hu_item)

    return testlink_structure


def build_real_qa_structure(df):
    df = df.copy()
    df["ID REQUERIMIENTO"] = df["ID REQUERIMIENTO"].ffill()
    df["DESCRIPCIÓN"] = df["DESCRIPCIÓN"].ffill()

    testlink_structure = []

    for hu_id, hu_df in df.groupby("ID REQUERIMIENTO", sort=False):
        hu_item = {
            "hu_name": clean_value(hu_id),
            "hu_description": first_value(hu_df, "DESCRIPCIÓN"),
            "test_cases": [],
        }

        for cp_id, cp_df in hu_df.groupby("ID CASO DE PRUEBA", sort=False):
            cp_id = clean_value(cp_id)

            cp_item = {
                "cp_id": cp_id,
                "summary": first_value(cp_df, "DESCRIPCIÓN DE LA PRUEBA"),
                "preconditions": first_value(cp_df, "PRECONDICIONES"),
                "input_data": first_value(cp_df, "DATOS DE ENTRADA"),
                "steps": [],
            }

            next_step_number = 1

            for row in cp_df.to_dict("records"):
                parsed_steps = build_real_qa_steps(row, cp_id, next_step_number)
                cp_item["steps"].extend(parsed_steps)
                next_step_number += len(parsed_steps)

            print("\nCP PARSEADO:")
            print(f"CP: {cp_item['cp_id']}")
            print(f"Summary: {cp_item['summary']}")
            print(f"Preconditions: {cp_item['preconditions']}")
            print(f"Input Data: {cp_item['input_data']}")
            print(f"Steps parseados: {len(cp_item['steps'])}")

            hu_item["test_cases"].append(cp_item)

        testlink_structure.append(hu_item)

    return testlink_structure


def build_testlink_structure(df):
    if df is None:
        print("\nNo hay datos para transformar.")
        return []

    df = normalize_dataframe_columns(df)

    if not validate_columns(df):
        return []

    excel_format = detect_excel_format(df)

    if excel_format == REAL_QA_FORMAT:
        return build_real_qa_structure(df)

    return build_mvp_structure(df)


def print_testlink_structure(testlink_structure):
    print("\nESTRUCTURA FINAL AGRUPADA:")
    pprint.pprint(testlink_structure, width=140)

    hu_count = len(testlink_structure)
    cp_count = 0
    step_count = 0

    for hu_item in testlink_structure:
        cp_count += len(hu_item["test_cases"])

        for cp_item in hu_item["test_cases"]:
            step_count += len(cp_item["steps"])

    print("\nRESUMEN AGRUPACION:")
    print(f"HUs detectadas: {hu_count}")
    print(f"CPs detectados: {cp_count}")
    print(f"Steps detectados: {step_count}")
