import apsync as aps

attribute_colors = [
        "grey", "blue", "purple", "green",
        "turk", "orange", "yellow", "red"]

def ensure_attribute(database: aps.Api, attribute_name: str) -> aps.Attribute:
    attribute = database.attributes.get_attribute(attribute_name)
    if not attribute:
        attribute = database.attributes.create_attribute(
            attribute_name, aps.AttributeType.multiple_choice_tag
        )
    return attribute

def replace_tag(tag: str, variants: list[list[str]]) -> str:
    if not variants:
        return tag
    for variant in variants:
        if tag in variant:
            return variant[0]

    return tag