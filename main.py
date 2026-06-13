# -*- coding: utf-8 -*-

import os
import pprint

from excel_reader import (
    DEFAULT_EXCEL_FILE,
    build_testlink_structure,
    print_testlink_structure,
    read_excel_all_sheets,
)
from testlink_api import (
    DEFAULT_PARENT_TESTSUITE_NAME,
    build_steps,
    clean_xmlrpc_text,
    create_test_case,
    create_test_suite,
    extract_id_from_response,
    extract_suite_id,
    find_child_suite_by_name,
    get_existing_test_case_names,
    get_testsuite_by_name,
    set_test_case_input_data,
    test_connection,
)


SEPARATOR = "=" * 50

# Estructuras de tracking estructurado, preparadas para una futura UI con
# 3 cuadros: creados, omitidos/duplicados y errores. Se llenan en paralelo
# a los prints existentes, sin reemplazarlos.
created_items = []
skipped_items = []
error_items = []


def process_hu(hu_item, parent_suite_id, stats, created_items, skipped_items, error_items):
    hu_name = hu_item["hu_name"]
    test_cases = hu_item["test_cases"]

    stats["hus_procesadas"] += 1

    print("\nHU A PROCESAR:")
    print(f"Nombre real (Excel): {hu_name}")
    print(f"Cantidad total de CPs a procesar: {len(test_cases)}")

    print("\nVERIFICANDO SI LA HU YA EXISTE DENTRO DE LA SUITE PADRE (MVM):")
    existing_hu_suite = find_child_suite_by_name(parent_suite_id, hu_name)

    if existing_hu_suite:
        test_suite_id = extract_suite_id(existing_hu_suite)
        stats["hus_reutilizadas"] += 1
        print("[SKIP] HU ya existe:")
        print(hu_name)
        print(f"Usando Suite ID existente: {test_suite_id}")
        skipped_items.append({
            "type": "HU",
            "status": "SKIPPED",
            "hu_name": hu_name,
            "testsuite_id": test_suite_id,
            "reason": "HU already exists",
        })
    else:
        suite_response = create_test_suite(
            testsuite_name=hu_name,
            details=hu_item["hu_description"],
            parentid=parent_suite_id,
        )

        test_suite_id = extract_id_from_response(suite_response)

        if test_suite_id:
            stats["hus_creadas"] += 1
            print("[OK] HU creada:")
            print(hu_name)
            created_items.append({
                "type": "HU",
                "status": "CREATED",
                "hu_name": hu_name,
                "testsuite_id": test_suite_id,
            })

    if not test_suite_id:
        print("[ERROR] No se pudo obtener el ID de la Test Suite para HU:")
        print(hu_name)
        error_items.append({
            "type": "HU",
            "status": "ERROR",
            "hu_name": hu_name,
            "testsuite_id": test_suite_id,
            "error": "No se pudo obtener el ID de la Test Suite",
        })
        return

    if not test_cases:
        print("[SKIP] La HU no tiene casos de prueba asociados:")
        print(hu_name)
        skipped_items.append({
            "type": "HU",
            "status": "SKIPPED",
            "hu_name": hu_name,
            "testsuite_id": test_suite_id,
            "reason": "HU has no test cases",
        })
        return

    print("\nVERIFICANDO CPs EXISTENTES EN LA SUITE ACTUAL:")
    existing_cp_names = get_existing_test_case_names(test_suite_id)
    print(f"CPs existentes encontrados: {len(existing_cp_names)}")

    for index, test_case in enumerate(test_cases, start=1):
        steps = build_steps(*test_case["steps"])
        test_case_name = test_case["cp_id"]
        preconditions = test_case["preconditions"]

        stats["cps_procesados"] += 1

        print("\nCREANDO TEST CASE DESDE EXCEL:")
        print(f"CP {index} de {len(test_cases)}")
        print(f"Test Suite ID: {test_suite_id}")
        print(f"HU: {hu_name}")
        print(f"CP: {test_case_name}")
        print(f"Cantidad de steps: {len(steps)}")

        if clean_xmlrpc_text(test_case_name) in existing_cp_names:
            print("[SKIP] CP ya existe:")
            print(test_case_name)
            stats["cps_omitidos"] += 1
            skipped_items.append({
                "type": "CP",
                "status": "SKIPPED",
                "hu_name": hu_name,
                "cp_id": test_case_name,
                "testsuite_id": test_suite_id,
                "reason": "CP already exists",
            })
            continue

        if not steps:
            print("[SKIP] CP omitido porque no tiene steps parseados:")
            print(test_case_name)
            stats["cps_omitidos"] += 1
            skipped_items.append({
                "type": "CP",
                "status": "SKIPPED",
                "hu_name": hu_name,
                "cp_id": test_case_name,
                "testsuite_id": test_suite_id,
                "reason": "CP has no parsed steps",
            })
            continue

        test_case_response = create_test_case(
            test_suite_id=test_suite_id,
            test_case_name=test_case_name,
            summary=test_case["summary"],
            preconditions=preconditions,
            steps=steps,
        )

        if test_case_response:
            print("[OK] CP creado:")
            print(test_case_name)
            stats["cps_creados"] += 1
            stats["steps_creados"] += len(steps)
            created_items.append({
                "type": "CP",
                "status": "CREATED",
                "hu_name": hu_name,
                "cp_id": test_case_name,
                "testcase_id": extract_id_from_response(test_case_response),
                "testsuite_id": test_suite_id,
            })
        else:
            print("[ERROR] No se pudo crear el CP:")
            print(test_case_name)
            error_items.append({
                "type": "CP",
                "status": "ERROR",
                "hu_name": hu_name,
                "cp_id": test_case_name,
                "testsuite_id": test_suite_id,
                "error": "create_test_case devolvio una respuesta vacia",
            })

        if test_case.get("input_data"):
            set_test_case_input_data(test_case_response, test_case["input_data"])


print("INICIANDO CARGA MASIVA EXCEL -> TESTLINK...\n")

test_connection()

print("\n[INFO] Archivo Excel detectado:")
print(os.path.basename(DEFAULT_EXCEL_FILE))

sheets = read_excel_all_sheets()

if not sheets:
    print("\n[ERROR] No se pudo leer el archivo Excel. Se detiene la ejecucion.")
else:
    parent_suite = get_testsuite_by_name(DEFAULT_PARENT_TESTSUITE_NAME)

    if not parent_suite:
        print("\n[ERROR] No se encontro la suite padre. Se detiene la ejecucion.")
    else:
        parent_suite_id = extract_suite_id(parent_suite)

        print("\nSUITE PADRE QUE SE USARA:")
        print(f"Nombre: {DEFAULT_PARENT_TESTSUITE_NAME}")
        print(f"ID real: {parent_suite_id}")

        stats = {
            "hus_procesadas": 0,
            "hus_creadas": 0,
            "hus_reutilizadas": 0,
            "cps_procesados": 0,
            "cps_creados": 0,
            "cps_omitidos": 0,
            "steps_creados": 0,
        }

        for sheet_name, sheet_df in sheets.items():
            print(f"\n{SEPARATOR}")
            print("[INFO] Procesando hoja:")
            print(sheet_name)
            print(SEPARATOR)

            try:
                if sheet_df is None:
                    print("[ERROR] Hoja invalida:")
                    print(sheet_name)
                    error_items.append({
                        "type": "SHEET",
                        "status": "ERROR",
                        "sheet_name": sheet_name,
                        "error": "No se pudo leer la hoja",
                    })
                    continue

                testlink_structure = build_testlink_structure(sheet_df)
                print_testlink_structure(testlink_structure)

                if not testlink_structure:
                    print("[ERROR] Hoja invalida:")
                    print(sheet_name)
                    error_items.append({
                        "type": "SHEET",
                        "status": "ERROR",
                        "sheet_name": sheet_name,
                        "error": "La hoja no tiene una estructura QA_REAL valida o no contiene datos",
                    })
                    continue

                for hu_item in testlink_structure:
                    process_hu(hu_item, parent_suite_id, stats, created_items, skipped_items, error_items)

            except Exception as e:

                print("[ERROR] Fallo procesando hoja:")
                print(sheet_name)
                print(e)
                error_items.append({
                    "type": "SHEET",
                    "status": "ERROR",
                    "sheet_name": sheet_name,
                    "error": str(e),
                })
                continue

        print(f"\n{SEPARATOR}")
        print("RESUMEN FINAL")
        print(SEPARATOR)

        print(f"\nHUs procesadas: {stats['hus_procesadas']}")
        print(f"HUs creadas: {stats['hus_creadas']}")
        print(f"HUs reutilizadas: {stats['hus_reutilizadas']}")

        print(f"\nCPs procesados: {stats['cps_procesados']}")
        print(f"CPs creados: {stats['cps_creados']}")
        print(f"CPs omitidos: {stats['cps_omitidos']}")

        print(f"\nSteps creados: {stats['steps_creados']}")

        print("\nCREADOS:")
        print(len(created_items))

        print("\nOMITIDOS:")
        print(len(skipped_items))

        print("\nERRORES:")
        print(len(error_items))

        print("\nCREATED_ITEMS:")
        pprint.pprint(created_items, width=120)

        print("\nSKIPPED_ITEMS:")
        pprint.pprint(skipped_items, width=120)

        print("\nERROR_ITEMS:")
        pprint.pprint(error_items, width=120)
