class AbstractBasis:

    def sequence_order(self):
        raise Exception("No implementation provided for sequence_order()!")

    def creation_sequence(self):
        raise Exception("No implementation provided for creation_sequence()!")
