from ibm_watsonx_orchestrate.utils.file_manager import FileManager, safe_open
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest

class MockEncodingGuess:
    def __init__(self, encoding, score):
        self.encoding = encoding
        self.score = score

class MockEncodingGuesses:
    def __init__(self, guesses):
        self.guesses = guesses
    
    def best(self):
        guess = None
        for g in self.guesses:
            if guess is None or g.score > guess.score:
                guess = g
        return guess

class TestFileManagerGetEncoding:
    def test_file_manager_get_encoding(self):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.Path.exists") as mock_path_exists, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.from_path") as mock_from_path, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.Config.read") as mock_config_read:
            
            mock_path = Path("test_file.yaml")
            mock_path_exists.return_value = True
            mock_config_read.return_value = None
            
            mock_encoding = "test_encoding"
            mock_encoding_guess = MockEncodingGuess(encoding=mock_encoding, score=1)
            mock_encoding_guesses = MockEncodingGuesses(guesses=[mock_encoding_guess])
            mock_from_path.return_value = mock_encoding_guesses

            fm = FileManager()
            encoding = fm.get_encoding(mock_path)

            mock_path_exists.assert_called_once_with()
            mock_from_path.assert_called_once_with(mock_path)
            mock_config_read.assert_called_once_with("settings", "file_encoding")
            assert encoding == mock_encoding
    
    def test_file_manager_get_encoding_no_guess(self):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.Path.exists") as mock_path_exists, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.from_path") as mock_from_path, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.Config.read") as mock_config_read:
            
            mock_path = Path("test_file.yaml")
            mock_path_exists.return_value = True
            mock_config_read.return_value = None
            
            mock_encoding_guesses = MockEncodingGuesses(guesses=[])
            mock_from_path.return_value = mock_encoding_guesses

            fm = FileManager()
            encoding = fm.get_encoding(mock_path)

            mock_path_exists.assert_called_once_with()
            mock_from_path.assert_called_once_with(mock_path)
            mock_config_read.assert_called_once_with("settings", "file_encoding")
            assert encoding == fm.DEFAULT_ENCODING
    
    def test_file_manager_get_encoding_non_existent(self):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.Path.exists") as mock_path_exists, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.from_path") as mock_from_path, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.Config.read") as mock_config_read:
            
            mock_path = Path("test_file.yaml")
            mock_path_exists.return_value = False
            mock_config_read.return_value = None


            fm = FileManager()
            encoding = fm.get_encoding(mock_path)

            mock_path_exists.assert_called_once_with()
            mock_from_path.assert_not_called()
            mock_config_read.assert_called_once_with("settings", "file_encoding")
            assert encoding == fm.DEFAULT_ENCODING
    
    def test_file_manager_get_encoding_config_set(self):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.Path.exists") as mock_path_exists, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.from_path") as mock_from_path, \
            patch("ibm_watsonx_orchestrate.utils.file_manager.Config.read") as mock_config_read:
            
            mock_encoding = "test_encoding"
            mock_path = Path("test_file.yaml")
            mock_path_exists.return_value = False
            mock_config_read.return_value = mock_encoding

            fm = FileManager()
            encoding = fm.get_encoding(mock_path)

            mock_path_exists.assert_not_called()
            mock_from_path.assert_not_called()
            mock_config_read.assert_called_once_with("settings", "file_encoding")
            assert encoding == mock_encoding

class TestFileManagerOpenFileEncoded:
    @pytest.mark.parametrize(
            ("file_path"),
            [
               "test_file.yaml",
               "test_file.txt",
               "test_file.csv",
               "test_file.json",
               "test_file.xml",
               "test_file.js",
               "test_file.py",
               "test_file.html",
               Path("test_file.yaml"),
               Path("test_file.txt"),
               Path("test_file.csv"),
            ]
    )
    def test_file_manager_open_file_encoded(self, file_path):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.FileManager") as mock_file_manager, \
            patch("builtins.open", mock_open()) as mock_file_open:
            mock_encoding = "test_encoding"
            mock_get_encoding = MagicMock()
            mock_get_encoding.return_value = mock_encoding


            fm = FileManager()
            fm.get_encoding = mock_get_encoding
            fm.open_file_encoded(file_path, 'r')

            
            assert mock_file_open.call_args.kwargs.get("encoding") == mock_encoding
    
    def test_file_manager_open_file_encoded_with_encoding(self):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.FileManager") as mock_file_manager, \
            patch("builtins.open", mock_open()) as mock_file_open:
            mock_encoding_1 = "test_encoding"
            mock_encoding_2 = "test_encoding_2"
            mock_get_encoding = MagicMock()
            mock_get_encoding.return_value = mock_encoding_1


            fm = FileManager()
            fm.get_encoding = mock_get_encoding
            fm.open_file_encoded("test.yaml", 'r', encoding=mock_encoding_2)

            
            assert mock_file_open.call_args.kwargs.get("encoding") == mock_encoding_2
    
    @pytest.mark.parametrize(
            ("file_path"),
            [
               "test_file.pdf",
               "test_file.xlsx",
               "test_file.docx",
               "test_file.exe",
               Path("test_file.pdf"),
               Path("test_file.xlsx"),
               Path("test_file.exe"),
            ]
    )
    def test_file_manager_open_file_encoded_non_text(self, file_path):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.FileManager") as mock_file_manager, \
            patch("builtins.open", mock_open()) as mock_file_open:
            mock_encoding = "test_encoding"
            mock_get_encoding = MagicMock()
            mock_get_encoding.return_value = mock_encoding


            fm = FileManager()
            fm.get_encoding = mock_get_encoding
            fm.open_file_encoded(file_path, 'r')

            
            assert mock_file_open.call_args.kwargs.get("encoding") is None
    

class TestSafeOpen:
    @pytest.mark.parametrize(
            ("open_args", "open_kwargs"),
            [
               (["test.yaml", "r"], {}),
               ([], {"encoding": "test_encoding"}),
               (["test.yaml", "r"], {"encoding": "test_encoding"})
            ]
    )
    def test_safe_open(self, open_args, open_kwargs):
        with patch("ibm_watsonx_orchestrate.utils.file_manager.FileManager") as mock_file_manager:
            mock_instance = mock_file_manager.return_value

            safe_open(*open_args, **open_kwargs)

            mock_instance.open_file_encoded.assert_called_with(*open_args, **open_kwargs)




