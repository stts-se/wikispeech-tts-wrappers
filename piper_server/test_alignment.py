import pytest
import tools

class TestAlignment:
    
    def test_matching_token_count(self):
        tokens_processed = [
            {'orth': 'All', 'g2p_method': 'ssml', 'input': 'ˈOl', 'phonemes': 'ˈOl'},
            {'orth': 'Apologies', 'input': 'Apologies', 'phonemes': 'apɔlogˈIs', 'g2p_method': 'deep_phonemizer', 'postpunct': '"'},
            {'orth': 'hamnade', 'g2p_method': 'lexicon', 'input': 'h°amn`adə', 'phonemes': 'h°amn`adə'},
            {'orth': 'på', 'g2p_method': 'lexicon', 'input': 'pˈO', 'phonemes': 'pˈO'},
            {'orth': 'plats', 'g2p_method': 'lexicon', 'input': 'plˈats', 'phonemes': 'plˈats'},
            {'orth': 'sju', 'g2p_method': 'lexicon', 'input': 'ɧˈɄ', 'phonemes': 'ɧˈɄ'},
            {'orth': '.', 'input': '.', 'phonemes': '.', 'hidden': True, 'prepunct': ','}
        ]
        tokens_aligned = [
            {'phonemes': 'ˈOl', 'start_time': 0.023219954648526078, 'end_time': 0.4295691609977324},
            {'phonemes': 'apɔlogˈIs', 'start_time': 0.4295691609977324, 'end_time': 1.1609977324263039},
            {'phonemes': 'h°amn`adə', 'start_time': 1.1609977324263039, 'end_time': 1.5673469387755101},
            {'phonemes': 'pˈO', 'start_time': 1.5673469387755101, 'end_time': 1.7298866213151927},
            {'phonemes': 'plˈats', 'start_time': 1.7298866213151927, 'end_time': 2.1130158730158732},
            {'phonemes': 'ɧˈɄ', 'start_time': 2.1130158730158732, 'end_time': 2.6354648526077096},
            {'phonemes': '.', 'start_time': 2.6354648526077096, 'end_time': 2.716734693877551}
        ]
        result = tools.postmatch_alignments(tokens_processed, tokens_aligned)
        expect = [
            {'phonemes': 'ˈOl', 'start_time': 0.023219954648526078, 'end_time': 0.4295691609977324, 'orth': 'All', 'g2p_method': 'ssml', 'input': 'ˈOl'},
            {'phonemes': 'apɔlogˈIs', 'start_time': 0.4295691609977324, 'end_time': 1.1609977324263039, 'orth': 'Apologies', 'input': 'Apologies', 'g2p_method': 'deep_phonemizer', 'postpunct': '"'},
            {'phonemes': 'h°amn`adə', 'start_time': 1.1609977324263039, 'end_time': 1.5673469387755101, 'orth': 'hamnade', 'g2p_method': 'lexicon', 'input': 'h°amn`adə'},
            {'phonemes': 'pˈO', 'start_time': 1.5673469387755101, 'end_time': 1.7298866213151927, 'orth': 'på', 'g2p_method': 'lexicon', 'input': 'pˈO'},
            {'phonemes': 'plˈats', 'start_time': 1.7298866213151927, 'end_time': 2.1130158730158732, 'orth': 'plats', 'g2p_method': 'lexicon', 'input': 'plˈats'},
            {'phonemes': 'ɧˈɄ', 'start_time': 2.1130158730158732, 'end_time': 2.6354648526077096, 'orth': 'sju', 'g2p_method': 'lexicon', 'input': 'ɧˈɄ'},
            {'phonemes': '.', 'start_time': 2.6354648526077096, 'end_time': 2.716734693877551, 'orth': '.', 'input': '.', 'hidden': True, 'prepunct': ','}
        ]
        assert result == expect

    def test_complex1(self):
        tokens_processed = [
            {'orth': '', 'input': '', 'phonemes': '', 'g2p_method': 'deep_phonemizer', 'prepunct': '"'},
            {'orth': 'All', 'g2p_method': 'ssml', 'input': 'ˈOl', 'phonemes': 'ˈOl'},
            {'orth': 'Apologies', 'input': 'Apologies', 'phonemes': 'apɔlogˈIs', 'g2p_method': 'deep_phonemizer', 'postpunct': '"'},
            {'orth': 'hamnade', 'g2p_method': 'lexicon', 'input': 'h°amn`adə', 'phonemes': 'h°amn`adə'},
            {'orth': 'på', 'g2p_method': 'lexicon', 'input': 'pˈO', 'phonemes': 'pˈO'},
            {'orth': 'plats', 'g2p_method': 'lexicon', 'input': 'plˈats', 'phonemes': 'plˈats'},
            {'orth': 'sju', 'g2p_method': 'lexicon', 'input': 'ɧˈɄ', 'phonemes': 'ɧˈɄ'},
            {'orth': '.', 'input': '.', 'phonemes': '.', 'hidden': True, 'prepunct': ','}
        ]
        tokens_aligned = [
            {'phonemes': 'ˈOl', 'start_time': 0.023219954648526078, 'end_time': 0.4295691609977324},
            {'phonemes': 'apɔlogˈIs', 'start_time': 0.4295691609977324, 'end_time': 1.1609977324263039},
            {'phonemes': 'h°amn`adə', 'start_time': 1.1609977324263039, 'end_time': 1.5673469387755101},
            {'phonemes': 'pˈO', 'start_time': 1.5673469387755101, 'end_time': 1.7298866213151927},
            {'phonemes': 'plˈats', 'start_time': 1.7298866213151927, 'end_time': 2.1130158730158732},
            {'phonemes': 'ɧˈɄ', 'start_time': 2.1130158730158732, 'end_time': 2.6354648526077096},
            {'phonemes': '.', 'start_time': 2.6354648526077096, 'end_time': 2.716734693877551}
        ]
        result = tools.postmatch_alignments(tokens_processed, tokens_aligned)
        expect = [
            {'phonemes': 'ˈOl', 'start_time': 0.023219954648526078, 'end_time': 0.4295691609977324, 'orth': 'All', 'g2p_method': 'ssml', 'input': 'ˈOl'},
            {'phonemes': 'apɔlogˈIs', 'start_time': 0.4295691609977324, 'end_time': 1.1609977324263039, 'orth': 'Apologies', 'input': 'Apologies', 'g2p_method': 'deep_phonemizer', 'postpunct': '"'},
            {'phonemes': 'h°amn`adə', 'start_time': 1.1609977324263039, 'end_time': 1.5673469387755101, 'orth': 'hamnade', 'g2p_method': 'lexicon', 'input': 'h°amn`adə'},
            {'phonemes': 'pˈO', 'start_time': 1.5673469387755101, 'end_time': 1.7298866213151927, 'orth': 'på', 'g2p_method': 'lexicon', 'input': 'pˈO'},
            {'phonemes': 'plˈats', 'start_time': 1.7298866213151927, 'end_time': 2.1130158730158732, 'orth': 'plats', 'g2p_method': 'lexicon', 'input': 'plˈats'},
            {'phonemes': 'ɧˈɄ', 'start_time': 2.1130158730158732, 'end_time': 2.6354648526077096, 'orth': 'sju', 'g2p_method': 'lexicon', 'input': 'ɧˈɄ'},
            {'phonemes': '.', 'start_time': 2.6354648526077096, 'end_time': 2.716734693877551, 'orth': '.', 'input': '.', 'hidden': True, 'prepunct': ','}
        ]
        assert result == expect

