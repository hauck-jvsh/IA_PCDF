"""Diagnóstico da JVM em processo separado. Não abre um caso IPED."""
from pathlib import Path
import os
import struct

home = Path(os.environ["JAVA_HOME"])
handles = []
if os.name == "nt":
    handles = [os.add_dll_directory(str(p)) for p in [home / "bin", home / "bin" / "server"]]
import jnius_config
jnius_config.add_options("-Xmx256m")
from jnius import autoclass
System = autoclass("java.lang.System")
print("Python:", 8 * struct.calcsize("P"), "bits")
print("Java:", System.getProperty("java.version"))
print("Arquitetura Java:", System.getProperty("os.arch"))
