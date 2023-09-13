"""file for importing FHIR to neo4j"""

import glob
import json
import logging
import time

import click
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Timer:
    """helper class for runtime calculation"""

    def __init__(self):
        self._start = time.time()
        self._end = None
        self._runtime = None

    def end(self):
        """ends timer"""
        self._end = time.time()
        self._runtime = float(str(time.time() - self._start)[:5])
        return self._runtime


def cypher_transaction(cypher, uri: str, auth: tuple[str, str]) -> list:
    """helper function that runs cypher transaction on local db"""
    try:
        driver = GraphDatabase.driver(uri, auth=auth)
        values = []
        with driver.session() as session:
            res = session.run(cypher)
            for record in res:
                values.append(record.values())
        driver.close()
        return values
    except Exception as exception:
        logger.error(f"Error executing cypher: {exception}")
        raise exception


def run_timed_cypher_query(
    cypher, uri: str, auth: tuple[str, str]
) -> tuple[list, float]:
    """helper function wrapped around cypher_transaction() for timing"""
    timer = Timer()
    result = cypher_transaction(cypher=cypher, uri=uri, auth=auth)
    runtime = timer.end()
    return result, runtime


def format_bundle(bundle: dict) -> str:
    """formats json string to be valid neo4j json"""

    def escape_special_chars(json_str: str) -> str:
        json_str = json_str.replace("'", "\\'")
        json_str = json_str.replace('"', '\\"')
        json_str = json_str.replace("\n", "").replace("\\n", "")
        return json_str

    def bundle_to_str(bundle: dict) -> str:
        return json.dumps(bundle)

    def remove_display_text(bundle: dict) -> dict:
        for i, entry in enumerate(bundle["entry"]):
            text = entry["resource"].get("text")
            if not text:
                continue
            bundle["entry"][i]["resource"]["text"]["div"] = "Removed 'div' for Neo4j"
        return bundle

    bundle_no_display = remove_display_text(bundle)

    bundle_str = bundle_to_str(bundle_no_display)

    escaped_str = escape_special_chars(bundle_str)

    return f'"{escaped_str}"'


def read_bundle_json(filename: str) -> str:
    """reads json file containing fhir bundle and formats it"""
    with open(filename, encoding="utf-8") as json_file:
        bundle = json.load(json_file)
        bundle_str = format_bundle(bundle)
        return bundle_str


def load_bundles(fhir_bundles, uri: str, auth: tuple[str, str]):
    """loads fhir bundles from folder into neo4j"""

    total_time = 0.0

    for bundle_file in fhir_bundles:
        bundle_str = read_bundle_json(bundle_file)

        cypher = f"""
            CALL cyfhir.bundle.load({bundle_str}, {{validation: true, version: "r4"}})
        """

        result, runtime = (None, None)
        patient = " ".join(bundle_file.split("\\")[-1].split("_")[:2])

        try:
            result, runtime = run_timed_cypher_query(cypher=cypher, uri=uri, auth=auth)
            logging.info(f"--- Loaded patient '{patient}' in {runtime} seconds ---")
            total_time += runtime
        except Exception as exception:
            logging.error(
                f"""
                --- Failed to load patient '{patient}' ---"
                Exception: {exception}
                Result: {result}
                """
            )
    return round(total_time, 3)


@click.command()
@click.option(
    "--fhir_folder",
    required=True,
    type=click.Path(exists=True),
    prompt=True,
    help="Folder containing FHIR bundle json files",
)
@click.option(
    "--uri",
    required=True,
    type=str,
    prompt=True,
    help="Neo4j URI (e.g. bolt://localhost:7687)",
)
@click.option(
    "--user",
    required=True,
    type=str,
    prompt=True,
    help="Neo4j username",
)
@click.password_option(
    help="Neo4j password",
)
def main(fhir_folder: str, uri: str, user: str, password: str) -> None:
    """loads folder containing fhir bundles json files into neo4j"""
    logging.info("--- Looking for FHIR bundles ---")
    if fhir_folder[-1] != "/":
        fhir_folder += "/"
    fhir_bundles = glob.glob(f"{fhir_folder}*.json")
    logging.info(f"--- Found {len(fhir_bundles)} FHIR Bundles ---")

    total_time = load_bundles(fhir_bundles=fhir_bundles, uri=uri, auth=(user, password))

    output_str = f"""
    In {total_time} seconds...
    Loaded {len(fhir_bundles)} patients' medical history FHIR bundles from '{fhir_folder}'.
    """
    logging.info(output_str)


if __name__ == "__main__":
    main()
