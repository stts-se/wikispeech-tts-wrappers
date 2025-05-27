class Symbols:
    symbols: list
    symbol2id: dict
    id2symbol: dict
    letters: list
    letters_ipa: list
    
    def __init__(self, json_obj):
        self.letters = json_obj['letters']
        self.letters_ipa = json_obj['letters_ipa']
        self.symbols = [json_obj['pad']] + list(json_obj['punctuation']) + list(self.letters) + list(self.letters_ipa)
        
        # Special symbol ids
        #SPACE_ID = self.symbols.index(" ")

        self.symbol2id = {s: i for i, s in enumerate(self.symbols)}
        self.id2symbol = {i: s for i, s in enumerate(self.symbols)}  # pylint: disable=unnecessary-comprehension
    
    def text_to_sequence(self, text):
        """Converts a string of text to a sequence of IDs corresponding to the symbols in the text"""
        sequence = []
        
        for symbol in text:
            symbol_id = self.symbol2id[symbol]
            sequence += [symbol_id]
        return sequence      
                
    def sequence_to_text(self, sequence):
        """Converts a sequence of IDs back to a string"""
        result = ""
        for symbol_id in sequence:
            s = self.id2symbol[symbol_id]
            result += s
        return result

