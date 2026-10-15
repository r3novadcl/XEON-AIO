from XEON.emojis import E as _E


import sys as _sys

class _Proxy(_sys.modules[__name__].__class__):
    def __getattr__(self, name: str) -> str:
        val = _E[name]
        if val != "❔" or name in _E:
            return val
        raise AttributeError(f"Emoji key '{name}' not found in emojis.json")

_sys.modules[__name__].__class__ = _Proxy

E = _E
