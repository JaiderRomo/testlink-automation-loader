# -*- coding: utf-8 -*-

import os
import pprint
import re
import unicodedata
import xmlrpc.client
from dotenv import load_dotenv


INVISIBLE_CHARACTERS = [
    "\ufeff",
    "\u200b",
    "\u200c",
    "\u200d",
    "\u2060",
]

CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_xmlrpc_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")

    for character in INVISIBLE_CHARACTERS:
        text = text.replace(character, "")

    text = CONTROL_CHARACTER_PATTERN.sub("", text)
    text = unicodedata.normalize("NFC", text)
    return text.strip()


load_dotenv(encoding="utf-8")

URL = os.getenv("TESTLINK_URL")
DEVKEY = os.getenv("TESTLINK_DEVKEY")
AUTHOR_LOGIN = os.getenv("TESTLINK_AUTHOR_LOGIN", "admin")
DEFAULT_PARENT_TESTSUITE_NAME = os.getenv(
    "TESTLINK_PARENT_TESTSUITE_NAME",
    "Inventario casos de prueba personalizaciones (MVM)"
)

# Nombre INTERNO real (campo "name" en TestLink, Admin > Custom Fields) del
# custom field que alimenta el campo visual "Datos de entrada" del Test
# Case. Confirmado via tl.getTestCaseCustomFieldDesignValue(details="full")
# sobre QAEMC-437: name="Datos de entrada", enable_on_design=1,
# show_on_design=1.
INPUT_DATA_CUSTOM_FIELD_NAME = os.getenv(
    "TESTLINK_CUSTOMFIELD_DATOS_ENTRADA",
    "Datos de entrada"
)

server = xmlrpc.client.ServerProxy(URL, encoding="utf-8", allow_none=True) if URL else None

PROJECT_ID = int(os.getenv("TESTLINK_PROJECT_ID", "1"))
MANUAL_EXECUTION_TYPE = 1
MEDIUM_IMPORTANCE = 2


def validate_config():
    if not URL:
        raise ValueError("Falta TESTLINK_URL en el archivo .env")

    if not DEVKEY:
        raise ValueError("Falta TESTLINK_DEVKEY en el archivo .env")


def configure_connection(testlink_url=None, devkey=None):
    global URL, DEVKEY, server

    if testlink_url:
        URL = testlink_url
        server = xmlrpc.client.ServerProxy(URL, encoding="utf-8", allow_none=True)

    if devkey:
        DEVKEY = devkey


def print_response(title, response):
    print(title)
    pprint.pprint(response, width=120)


def print_xmlrpc_error(title, error):
    print(title)

    if isinstance(error, xmlrpc.client.Fault):
        print(f"Fault code: {error.faultCode}")
        print(f"Fault string: {error.faultString}")
        return

    if isinstance(error, xmlrpc.client.ProtocolError):
        print(f"URL: {error.url}")
        print(f"HTTP code: {error.errcode}")
        print(f"HTTP message: {error.errmsg}")
        print(f"Headers: {error.headers}")
        return

    print(error)


def extract_id_from_response(response):
    if isinstance(response, list) and response:
        first_item = response[0]

        if isinstance(first_item, dict):
            return first_item.get("id")

    if isinstance(response, dict):
        return response.get("id")

    return None


def extract_test_case_external_id_and_version(response):
    if not isinstance(response, list) or not response:
        return None, None

    first_item = response[0]

    if not isinstance(first_item, dict):
        return None, None

    additional_info = first_item.get("additionalInfo")

    if not isinstance(additional_info, dict):
        return None, None

    return additional_info.get("external_id"), additional_info.get("version_number")


def normalize_suite_response(response):
    if response is None:
        return []

    if isinstance(response, list):
        items = response
    elif isinstance(response, dict):
        if "id" in response or "name" in response:
            items = [response]
        else:
            items = list(response.values())
    else:
        return []

    suites = []

    for item in items:
        if isinstance(item, dict):
            suites.append(item)

    return suites


def extract_suite_id(suite):
    for key in ["id", "testsuiteid", "test_suite_id", "node_id"]:
        if key in suite and suite[key]:
            return suite[key]

    return None


def extract_suite_name(suite):
    for key in ["name", "testsuitename", "test_suite_name", "text"]:
        if key in suite and suite[key]:
            return str(suite[key]).strip()

    return ""


def get_child_test_suites(parent_suite, level=0, parent_path=""):
    parent_id = extract_suite_id(parent_suite)
    parent_name = extract_suite_name(parent_suite)

    if not parent_id:
        return []

    current_path = parent_name

    if parent_path:
        current_path = f"{parent_path} / {parent_name}"

    current_suite = parent_suite.copy()
    current_suite["_level"] = level
    current_suite["_path"] = current_path

    suites = [current_suite]

    response = server.tl.getTestSuitesForTestSuite({
        "devKey": DEVKEY,
        "testsuiteid": int(parent_id),
    })

    child_suites = normalize_suite_response(response)

    for child_suite in child_suites:
        child_suite["_parentid"] = int(parent_id)
        suites.extend(get_child_test_suites(child_suite, level + 1, current_path))

    return suites


def print_test_suites(suites):
    print("\nTEST SUITES ENCONTRADAS:")

    if not suites:
        print("No se encontraron Test Suites.")
        return

    for suite in suites:
        suite_id = extract_suite_id(suite)
        suite_name = extract_suite_name(suite)
        suite_level = suite.get("_level", 0)
        suite_path = suite.get("_path", suite_name)
        indent = "  " * suite_level

        print(f"{indent}- ID: {suite_id} | Nombre: {suite_name} | Ruta: {suite_path}")


def get_project_test_suites(project_id=PROJECT_ID):

    try:

        validate_config()

        payload = {
            "devKey": DEVKEY,
            "testprojectid": int(project_id),
        }

        debug_payload = payload.copy()
        debug_payload["devKey"] = "***"

        print("\nPAYLOAD GET FIRST LEVEL TEST SUITES:")
        pprint.pprint(debug_payload, width=120)

        response = server.tl.getFirstLevelTestSuitesForTestProject(payload)
        first_level_suites = normalize_suite_response(response)

        all_suites = []

        for suite in first_level_suites:
            all_suites.extend(get_child_test_suites(suite))

        print_test_suites(all_suites)
        return all_suites

    except Exception as e:

        print_xmlrpc_error("ERROR GET PROJECT TEST SUITES:", e)
        return []


def get_testsuite_by_name(testsuite_name, project_id=PROJECT_ID):

    try:

        print("\nBUSCANDO TEST SUITE POR NOMBRE:")
        print(f"Nombre buscado: {testsuite_name}")

        suites = get_project_test_suites(project_id)

        exact_matches = []
        case_insensitive_matches = []
        target_name = testsuite_name.strip()
        target_name_lower = target_name.lower()

        for suite in suites:
            suite_name = extract_suite_name(suite)

            if suite_name == target_name:
                exact_matches.append(suite)

            if suite_name.lower() == target_name_lower:
                case_insensitive_matches.append(suite)

        matches = exact_matches or case_insensitive_matches

        if not matches:
            print("\nNo se encontro la Test Suite padre.")
            return None

        if len(matches) > 1:
            print("\nADVERTENCIA: se encontraron varias suites con el mismo nombre. Se usara la primera.")

        suite = matches[0]
        suite_id = extract_suite_id(suite)

        print("\nSUITE PADRE ENCONTRADA:")
        print(f"ID real: {suite_id}")
        print(f"Nombre: {extract_suite_name(suite)}")
        print(f"Ruta: {suite.get('_path', extract_suite_name(suite))}")

        return suite

    except Exception as e:

        print_xmlrpc_error("ERROR GET TESTSUITE BY NAME:", e)
        return None


def find_child_suite_by_name(parent_suite_id, suite_name):

    try:

        validate_config()

        payload = {
            "devKey": DEVKEY,
            "testsuiteid": int(parent_suite_id),
        }

        debug_payload = payload.copy()
        debug_payload["devKey"] = "***"

        print("\nPAYLOAD GET TEST SUITES FOR TEST SUITE (BUSQUEDA HU DUPLICADA):")
        pprint.pprint(debug_payload, width=120)

        response = server.tl.getTestSuitesForTestSuite(payload)

        print_response("\nRESPUESTA GET TEST SUITES FOR TEST SUITE (BUSQUEDA HU DUPLICADA):", response)

        child_suites = normalize_suite_response(response)
        target_name = clean_xmlrpc_text(suite_name)

        for suite in child_suites:
            if clean_xmlrpc_text(extract_suite_name(suite)) == target_name:
                return suite

        return None

    except Exception as e:

        print_xmlrpc_error("ERROR BUSCAR HU DUPLICADA (TEST SUITE):", e)
        return None


def build_steps(*steps):
    formatted_steps = []

    for index, step in enumerate(steps, start=1):
        formatted_steps.append({
            "step_number": step.get("step_number", index),
            "actions": clean_xmlrpc_text(step.get("actions", "")),
            "expected_results": clean_xmlrpc_text(step.get("expected_results", "")),
            "execution_type": step.get("execution_type", MANUAL_EXECUTION_TYPE),
        })

    return formatted_steps


def test_connection():

    try:

        validate_config()

        print("Probando conexion...\n")

        response = server.tl.getProjects({
            "devKey": DEVKEY
        })

        print("Conexion exitosa")
        print_response("RESPUESTA GET PROJECTS:", response)
        return response

    except Exception as e:

        print_xmlrpc_error("ERROR TEST CONNECTION:", e)
        return None


def get_test_project_prefix(project_id=PROJECT_ID):

    try:

        validate_config()

        response = server.tl.getProjects({"devKey": DEVKEY})

        if not isinstance(response, list):
            return None

        for project in response:
            if isinstance(project, dict) and str(project.get("id")) == str(project_id):
                return project.get("prefix")

        return None

    except Exception as e:

        print_xmlrpc_error("ERROR GET TEST PROJECT PREFIX:", e)
        return None


def create_test_suite(
    testsuite_name="HU_AUTOMATICA_PYTHON",
    details="Suite creada automaticamente desde Python",
    parentid=None
):

    try:

        validate_config()

        print("\nCreando Test Suite...\n")

        payload = {
            "devKey": DEVKEY,
            "testprojectid": PROJECT_ID,
            "testsuitename": clean_xmlrpc_text(testsuite_name),
            "details": clean_xmlrpc_text(details)
        }

        if parentid:
            payload["parentid"] = int(parentid)

        debug_payload = payload.copy()
        debug_payload["devKey"] = "***"

        print("PAYLOAD CREATE TEST SUITE:")
        pprint.pprint(debug_payload, width=120)
        print(f"ParentID usado: {parentid if parentid else 'Sin parentid - raiz del proyecto'}")

        response = server.tl.createTestSuite(payload)

        print_response("RESPUESTA CREATE SUITE:", response)
        return response

    except Exception as e:

        print_xmlrpc_error("ERROR CREATE SUITE:", e)
        return None


def get_test_cases_for_suite(testsuite_id):

    try:

        validate_config()

        payload = {
            "devKey": DEVKEY,
            "testsuiteid": int(testsuite_id),
            "deep": False,
            "details": "simple",
        }

        debug_payload = payload.copy()
        debug_payload["devKey"] = "***"

        print("\nPAYLOAD GET TEST CASES FOR SUITE:")
        pprint.pprint(debug_payload, width=120)

        response = server.tl.getTestCasesForTestSuite(payload)

        print_response("\nRESPUESTA GET TEST CASES FOR SUITE:", response)

        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            if "id" in response or "name" in response:
                return [response]

            return list(response.values())

        return []

    except Exception as e:

        print_xmlrpc_error("ERROR GET TEST CASES FOR SUITE:", e)
        return []


def get_existing_test_case_names(testsuite_id):
    test_cases = get_test_cases_for_suite(testsuite_id)
    existing_names = set()

    for test_case in test_cases:
        if not isinstance(test_case, dict):
            continue

        name = clean_xmlrpc_text(test_case.get("name", ""))

        if name:
            existing_names.add(name)

    return existing_names


def create_test_case(
    test_suite_id,
    test_case_name,
    summary,
    preconditions,
    steps,
    author_login=AUTHOR_LOGIN,
    project_id=PROJECT_ID
):

    try:

        validate_config()

        if not test_suite_id:
            raise ValueError("test_suite_id es obligatorio")

        if not test_case_name:
            raise ValueError("test_case_name es obligatorio")

        if not steps:
            raise ValueError("steps debe tener al menos un paso")

        payload = {
            "devKey": DEVKEY,
            "testcasename": clean_xmlrpc_text(test_case_name),
            "testsuiteid": int(test_suite_id),
            "testprojectid": int(project_id),
            "authorlogin": clean_xmlrpc_text(author_login),
            "summary": clean_xmlrpc_text(summary),
            "preconditions": clean_xmlrpc_text(preconditions),
            "steps": steps,
            "importance": MEDIUM_IMPORTANCE,
            "executiontype": MANUAL_EXECUTION_TYPE,
            "checkduplicatedname": 1,
            "actiononduplicatedname": "generate_new",
        }

        debug_payload = payload.copy()
        debug_payload["devKey"] = "***"

        print("\nPAYLOAD CREATE TEST CASE:")
        pprint.pprint(debug_payload, width=120)

        response = server.tl.createTestCase(payload)

        print_response("\nRESPUESTA CREATE TEST CASE:", response)
        return response

    except Exception as e:

        print_xmlrpc_error("ERROR CREATE TEST CASE:", e)
        return None


def set_test_case_input_data(test_case_response, input_data, project_id=PROJECT_ID):

    input_data = clean_xmlrpc_text(input_data)

    if not input_data:
        return None

    try:

        validate_config()

        external_id, version = extract_test_case_external_id_and_version(test_case_response)

        if not external_id:
            print("\nNo se pudo obtener el external_id del Test Case creado.")
            print("Se omite el envio de 'Datos de entrada'.")
            return None

        prefix = get_test_project_prefix(project_id)

        if not prefix:
            print("\nNo se pudo obtener el prefijo del proyecto.")
            print("Se omite el envio de 'Datos de entrada'.")
            return None

        testcaseexternalid = f"{prefix}-{external_id}"

        payload = {
            "devKey": DEVKEY,
            "testcaseexternalid": testcaseexternalid,
            "version": int(version) if version else 1,
            "testprojectid": int(project_id),
            "customfields": {
                INPUT_DATA_CUSTOM_FIELD_NAME: input_data,
            },
        }

        debug_payload = payload.copy()
        debug_payload["devKey"] = "***"

        print("\nPAYLOAD UPDATE CUSTOM FIELD 'DATOS DE ENTRADA':")
        pprint.pprint(debug_payload, width=120)

        response = server.tl.updateTestCaseCustomFieldDesignValue(payload)

        print_response("\nRESPUESTA UPDATE CUSTOM FIELD 'DATOS DE ENTRADA':", response)
        return response

    except Exception as e:

        print_xmlrpc_error("ERROR SET CUSTOM FIELD 'DATOS DE ENTRADA':", e)
        return None
