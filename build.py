from functools import lru_cache
from typing import Optional
from jinja2 import Environment, FileSystemLoader
import pystow
import jinja2
import synapseclient
import pathlib

HERE = pathlib.Path(__file__).parent.resolve()
TEMPLATES = HERE.joinpath('templates')
#: This entry contains the ID->Names mapping
#: .. seealso:: https://www.synapse.org/#!Synapse:syn24874056
SYNAPSE_NAMES_ID = 'syn24874056'

#: This entry contains the full compound information table
#: .. seealso:: https://www.synapse.org/#!Synapse:syn24874054
#: .. seealso:: https://dbdocs.io/clemenshug/sms_db?table=lsp_compound_dictionary&schema=public&view=table_structure
SYNAPSE_SOMETHING_ID = ''

#: The :mod:`jinja2` environment used for loading templates and formatting data into them
ENVIRONMENT = jinja2.Environment(
    autoescape=True, loader=jinja2.FileSystemLoader(TEMPLATES), trim_blocks=False
)
COMPOUND_TEMPALTE = ENVIRONMENT.get_template('')



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
