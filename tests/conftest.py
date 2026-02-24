"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
import sys

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))
