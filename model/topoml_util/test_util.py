import unittest
import pandas
from util import Tokenize

TOPOLOGY_TRAINING_CSV = '../../files/example.csv'
training_data = pandas.read_csv(TOPOLOGY_TRAINING_CSV)
raw_training_set = training_data['brt_wkt'] + ' ' + training_data['osm_wkt']
raw_target_set = training_data['intersection_wkt']


class TestUtil(unittest.TestCase):
    def test_tokenize(self):
        test_strings = ['A test string']
        tokenizer = Tokenize(test_strings)
        tokenized = tokenizer.char_level_tokenize(test_strings)
        self.assertEqual((tokenizer.word_index, tokenized),
                         ({' ': 2, 'A': 4, 'e': 5, 'g': 9, 'i': 7, 'n': 8, 'r': 6, 's': 3, 't': 1},
                          [[4, 2, 1, 5, 3, 1, 2, 3, 1, 6, 7, 8, 9]]))

    def test_tokenize_example(self):
        test_strings = training_data
        word_index = {'5': 1, '4': 2, '1': 3, '.': 4, '2': 5, '8': 6, ' ': 7, ',': 8, '3': 9, '7': 10, '6': 11,
                      '9': 12, '0': 13, 'O': 14, '(': 15, ')': 16, 'L': 17, 'Y': 18, 'P': 19, 'G': 20, 'N': 21,
                      'T': 22, 'E': 23, 'M': 24, 'I': 25, 'C': 26, 'U': 27, 'R': 28}
        tokenizer = Tokenize(test_strings['brt_wkt'] + test_strings['osm_wkt'] + test_strings['intersection_wkt'])
        tokenized = tokenizer.char_level_tokenize(test_strings['brt_wkt'])
        self.assertEqual((tokenizer.word_index, tokenized[0][0:15]),
                         (word_index,
                          [19, 14, 17, 18, 20, 14, 21, 15, 15, 2, 4]))

    def test_one_hot(self):
        test_strings = training_data['brt_wkt'] + training_data['osm_wkt']
        max_len = 0
        for sentence in test_strings:
            if len(sentence) > max_len:
                max_len = len(sentence)

        tokenizer = Tokenize(test_strings)
        matrix = tokenizer.one_hot(test_strings, max_len)
        self.assertEqual(matrix[0][0][18], True)  # 'P' for POLYGON

    def test_detokenize(self):
        test_strings = ['A test string']
        tokenizer = Tokenize(test_strings)
        tokenized = tokenizer.char_level_tokenize(test_strings)
        detokenized = tokenizer.detokenize(tokenized)
        self.assertEqual(detokenized, test_strings)
