"""Bootstrap Overture-convention Pydantic models from a data file.

Writes the first draft of a model from the data and the metadata shipped with it. Anything
it cannot find a source for is left as a TODO for a person to fill in.
"""

from .bootstrap import bootstrap, inspect_source
from .column import Column

__all__ = ["Column", "bootstrap", "inspect_source"]
