"""Rules engine module.

Pure-Python, deterministic game simulator that validates legality,
applies effects, and emits next state. This module must not import
PyTorch or Ray to maintain fast simulation performance.
""" 