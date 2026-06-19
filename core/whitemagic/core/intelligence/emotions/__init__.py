"""Emotions Package
Provides emotional synthesis for the Heart Engine.
"""

import logging

logger = logging.getLogger(__name__)

# Lazy imports — emotion submodules may not all be present
_emotion_names = [
    ("beauty", "BeautyEmotion", "get_beauty"),
    ("courage", "CourageEmotion", "get_courage"),
    ("gratitude", "GratitudeEmotion", "get_gratitude"),
    ("joy", "JoyEmotion", "get_joy"),
    ("love", "LoveEmotion", "get_love"),
    ("stillness", "StillnessEmotion", "get_stillness"),
    ("truth", "TruthEmotion", "get_truth"),
    ("wisdom", "WisdomEmotion", "get_wisdom"),
    ("wonder", "WonderEmotion", "get_wonder"),
]

__all__: list[str] = []
for _mod, _cls, _fn in _emotion_names:
    try:
        _m = __import__(f".{_mod}", package=__name__, fromlist=[_cls, _fn])  # type: ignore[call-arg]
        globals()[_cls] = getattr(_m, _cls)
        globals()[_fn] = getattr(_m, _fn)
        __all__.extend([_fn, _cls])
    except ImportError:
        logger.debug("Emotion submodule %s not available", _mod)
