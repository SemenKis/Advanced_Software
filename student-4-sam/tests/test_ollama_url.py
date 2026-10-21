import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
RAG_SERVER = ROOT / "ai-services" / "rag-server"
if str(RAG_SERVER) not in sys.path:
    sys.path.insert(0, str(RAG_SERVER))

from rag_pipeline import resolve_ollama_generate_url


class TestOllamaUrlResolution(unittest.TestCase):
    def test_prefers_explicit_generate_url(self):
        with patch.dict(os.environ, {"OLLAMA_GENERATE_URL": "http://example.com:11434/api/generate"}, clear=True):
            self.assertEqual(resolve_ollama_generate_url(), "http://example.com:11434/api/generate")

    def test_falls_back_to_ollama_url(self):
        with patch.dict(os.environ, {"OLLAMA_URL": "http://localhost:11434"}, clear=True):
            self.assertEqual(resolve_ollama_generate_url(), "http://localhost:11434/api/generate")

    def test_default_uses_localhost(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_ollama_generate_url(), "http://127.0.0.1:11434/api/generate")


if __name__ == "__main__":
    unittest.main()
