"""Tests for Portuguese phonetic encoder."""
import pytest
from app.services.similarity_engine import pt_phonetic_code


class TestPTPhoneticCode:
    def test_cao(self):
        assert pt_phonetic_code("ção") == "cao"

    def test_filo(self):
        assert pt_phonetic_code("filho") == "filo"

    def test_bano(self):
        assert pt_phonetic_code("banho") == "bano"

    def test_caca(self):
        assert pt_phonetic_code("caça") == "caca"

    def test_paso(self):
        assert pt_phonetic_code("passo") == "paso"

    def test_maria(self):
        assert pt_phonetic_code("Maria") == "maria"

    def test_empty(self):
        assert pt_phonetic_code("") == ""

    def test_accented(self):
        assert pt_phonetic_code("áéíóú") == "aeiou"
