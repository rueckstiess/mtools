#!/usr/bin/env python3

from enum import Enum

class LogFormat(Enum):
    LEGACY  = 1  # MongoDB <4.2
    LOGV2   = 2  # MongoDB 4.4+
    PROFILE = 3  # system.profile document (experimental)