import deepl
import logging
from os import getenv

logging.basicConfig(level=logging.INFO)

CLIENT = deepl.Translator(getenv("DEEPL_API_KEY", ""))

def translate(text: str) -> tuple[str, str]:
	"""
	Uses the DeepL API to translate text into English or a source_lang if given.

	:param text: The text to translate
	:type text: str
	:return: The translated text and the source language.
	:rtype: tuple[str, str]
	"""
	result: deepl.TextResult | list[deepl.TextResult] = CLIENT.translate_text(text, target_lang="EN-GB")
	if isinstance(result, list):
		result = result[0]
	source_lang = result.detected_source_lang
	text = " ".join(str(result.text).encode('utf-8').decode('utf-8').split("\x01"))
	logging.info(f"Successfully translated text '{text[0:10]}...'")
	return (text, source_lang)
