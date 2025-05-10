import pytest
from src.subtitle import frame_to_timestamp, timestamp_to_seconds, remove_tags

def test_frame_to_timestamp_invalid():
    """Testa casos inválidos de conversão de frame para timestamp"""
    # img_fps não numérico
    assert frame_to_timestamp("abc", 3) is None
    # current_frame não inteiro
    assert frame_to_timestamp(30, "frame") is None
    # divisão por zero
    assert frame_to_timestamp(0, 10) is None

def test_timestamp_to_seconds_invalid():
    """Testa casos inválidos de conversão de timestamp para segundos"""
    # formato inválido
    with pytest.raises(ValueError):
        timestamp_to_seconds("invalid timestamp")
    
    with pytest.raises(ValueError):
        timestamp_to_seconds("00:00:00")  # falta dos milissegundos
    
    with pytest.raises(ValueError):
        timestamp_to_seconds("00:00:00:00")  # dois pontos extras

def test_remove_tags_edge_cases():
    """Testa casos especiais de remoção de tags"""
    # Múltiplas tags grudadas
    assert remove_tags(r"{\i1}{\b1}{\fs20}Bold Italic") == "Bold Italic"

    # Quebras de linha repetidas
    assert remove_tags(r"Line1\N\NLine2") == "Line1 Line2"

    # Tags + texto colado
    assert remove_tags(r"{\i1}Test{\i0}ing") == "Test ing"

    # Sequência longa de tags
    assert remove_tags(r"{\i1}{\an8}{\fs20}{\c&HFFFFFF&}Hello") == "Hello"
