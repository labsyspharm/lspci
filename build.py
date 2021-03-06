"""Build the LSP Compound site."""

from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Optional

import bioregistry
import click
import jinja2
import pandas as pd
import pystow
import synapseclient
from more_click import verbose_option

HERE = Path(__file__).parent.resolve()

#: The /templates folder contains the Jinja2 templates for the compound pages and home page.
TEMPLATES = HERE.joinpath("templates")

#: The :mod:`jinja2` environment used for loading templates and formatting data into them
ENVIRONMENT = jinja2.Environment(
    autoescape=True, loader=jinja2.FileSystemLoader(TEMPLATES), trim_blocks=False
)
INDEX_TEMPLATE = ENVIRONMENT.get_template("index.html")
ABOUT_TEMPLATE = ENVIRONMENT.get_template("about.html")
COMPOUND_TEMPLATE = ENVIRONMENT.get_template("compound.html")

#: The /docs folder in the root of the repository into which the formatted templates are dumped,
#: from which GitHub Pages is served
DOCS = HERE.joinpath("docs")

#: This entry contains the ID->Names mapping
#: .. seealso:: https://www.synapse.org/#!Synapse:syn24874056
SYNAPSE_NAMES_ID = "syn24874056"
SYNAPSE_NAMES_NAME = "lsp_compound_names.csv.gz"
SYNAPSE_NAMES_COLUMNS = ["lspci_id", "source", "priority", "name"]

#: This entry contains the full compound information table
#: .. seealso:: https://www.synapse.org/#!Synapse:syn24874054
#: .. seealso:: https://dbdocs.io/clemenshug/sms_db?table=lsp_compound_dictionary&schema=public&view=table_structure
SYNAPSE_DICTIONARY_ID = "syn24874054"
SYNAPSE_DICTIONARY_NAME = "lsp_compound_dictionary.csv.gz"
SYNAPSE_DICTIONARY_COLUMNS = [
    "lspci_id",
    "hmsl_id",
    "chembl_id",
    "emolecules_id",
    "pref_name",
    "inchi",
    "commercially_available",
    "max_phase",
]

MODULE = pystow.module("lsp", "lspci")


@lru_cache
def get_synapse_client(
    email: Optional[str] = None,
    password: Optional[str] = None,
) -> synapseclient.Synapse:
    """Get a pre-logged synapse client."""
    syn = synapseclient.Synapse()
    syn.login(
        email=pystow.get_config("synapse", "username", passthrough=email),
        password=pystow.get_config("synapse", "password", passthrough=password),
    )
    return syn


def ensure(synapse_id: str, name: str, force: bool = False) -> Path:
    """Ensure a file from Synapse."""
    path = MODULE.join(name=name)
    if path.is_file() and not force:
        return path
    entity: synapseclient.Entity = get_synapse_client().get(
        entity=synapse_id,
        downloadLocation=MODULE.base,
    )
    return Path(entity.path).resolve()


@click.command()
@verbose_option
def main():
    """Build the LSP Compound website."""
    names_path = ensure(SYNAPSE_NAMES_ID, SYNAPSE_NAMES_NAME)

    synonyms = defaultdict(list)
    for chunk in pd.read_csv(names_path, chunksize=300, dtype=str):
        for lspci_id, sdf in chunk.groupby("lspci_id"):
            synonyms[lspci_id].extend(sdf[["source", "priority", "name"]].values)
        break

    counter = 0

    dictionary_path = ensure(SYNAPSE_DICTIONARY_ID, SYNAPSE_DICTIONARY_NAME)
    for chunk in pd.read_csv(dictionary_path, chunksize=5, dtype=str):
        print(chunk.head())
        counter += len(chunk.index)
        for _, row in chunk.iterrows():
            row = clean(row)
            identifier = row["lspci_id"]
            compound_html = COMPOUND_TEMPLATE.render(
                identifier=identifier,
                name=row.get("pref_name", identifier),
                inchi=row["inchi"],
                xrefs=extract_xrefs(row),
                row=row,
                synonyms=synonyms.get(identifier),
            )
            directory = DOCS.joinpath(str(row["lspci_id"]))
            directory.mkdir(exist_ok=True, parents=True)
            with directory.joinpath("index.html").open("w") as file:
                print(compound_html, file=file)
        break

    index_html = INDEX_TEMPLATE.render(counter=counter)
    with DOCS.joinpath("index.html").open("w") as file:
        print(index_html, file=file)

    about_html = ABOUT_TEMPLATE.render()
    with DOCS.joinpath("about.html").open("w") as file:
        print(about_html, file=file)


def clean(d):
    return {k: v for k, v in d.items() if pd.notna(v)}


def extract_xrefs(row) -> list[tuple[str, str, str]]:
    rows = []
    for key in ["hmsl_id", "chembl_id", "emolecules_id"]:
        if key not in row or pd.isna(row[key]):
            continue
        identifier = row[key]
        prefix = key.removesuffix("_id")
        rows.append(
            (
                prefix,
                bioregistry.get_name(prefix),
                bioregistry.get_homepage(prefix),
                identifier,
            )
        )
    return rows


if __name__ == "__main__":
    main()
