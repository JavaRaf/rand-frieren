import unittest
from src.subtitle import frame_to_timestamp, timestamp_to_seconds, remove_tags


class TestSubtitle(unittest.TestCase):
    def test_frame_to_timestamp_invalid(self):
        # img_fps não numérico
        self.assertIsNone(frame_to_timestamp("abc", 3))
        # current_frame não inteiro
        self.assertIsNone(frame_to_timestamp(30, "frame"))
        # divisão por zero
        self.assertIsNone(frame_to_timestamp(0, 10))

    def test_timestamp_to_seconds_invalid(self):
        # formato inválido
        with self.assertRaises(ValueError):
            timestamp_to_seconds("invalid timestamp")
        
        with self.assertRaises(ValueError):
            timestamp_to_seconds("00:00:00")  # falta dos milissegundos
        
        with self.assertRaises(ValueError):
            timestamp_to_seconds("00:00:00:00")  # dois pontos extras

    def test_remove_tags_edge_cases(self):
        # Múltiplas tags grudadas
        self.assertEqual(remove_tags(r"{\i1}{\b1}{\fs20}Bold Italic"), "Bold Italic")

        # Quebras de linha repetidas
        self.assertEqual(remove_tags(r"Line1\N\NLine2"), "Line1 Line2")

        # Tags + texto colado
        self.assertEqual(remove_tags(r"{\i1}Test{\i0}ing"), "Test ing")

        # Sequência longa de tags
        self.assertEqual(remove_tags(r"{\i1}{\an8}{\fs20}{\c&HFFFFFF&}Hello"), "Hello")




if __name__ == '__main__':
    unittest.main()
