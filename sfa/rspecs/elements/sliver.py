from sfa.rspecs.elements.element import Element

class Sliver(Element):
    fields = {
        'sliver_id': None,
        'component_id': None,
        'client_id': None,
        'name': None,
        'type': None,
        'tags': [],
    }
