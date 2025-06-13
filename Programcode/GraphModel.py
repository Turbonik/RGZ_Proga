class GraphModel:
    def __init__(self):
        self.nodes = []
    def add_node(self, node):
        self.nodes.append(node)
    def remove_node(self, node):
        self.nodes.remove(node)
    def find_start(self):
        for n in self.nodes:
            if n.type == 'START': return n
        return None