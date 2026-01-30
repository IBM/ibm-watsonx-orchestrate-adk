
import os
from pathlib import Path

def get_migrations_root():
  return Path(os.path.abspath(__file__)).parent