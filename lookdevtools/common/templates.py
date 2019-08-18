from lookdevtools.external import lucidity
from lookdevtools.common.constants import TEXTURESET_ELEMENT_PATTERN
from lookdevtools.common.constants import TEXTURESET_MATCHING_RATIO
from lookdevtools.common.constants import TEXTURESET_ELEMENT_MATCHING_RATIO

textureset_element_template = lucidity.Template(
    'textureset_element',
    TEXTURESET_ELEMENT_PATTERN,
    anchor=lucidity.Template.ANCHOR_END
    # Add STRICT?
    )