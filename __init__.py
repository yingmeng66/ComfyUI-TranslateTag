from .nodes import TranslateTag
from . import routes

NODE_CLASS_MAPPINGS = {"TranslateTagText": TranslateTag}
NODE_DISPLAY_NAME_MAPPINGS = {"TranslateTagText": "TranslateTag · Translate Text / 标签翻译"}
WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
