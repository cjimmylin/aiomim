"""`python -m aiomim.openai_study ...` (see cli.py).

String hashing is fixed (PYTHONHASHSEED=0) by re-executing once: every wave must rebuild
exactly the prompts of the previous one, so nothing that orders a set of strings may
vary between processes.
"""

import os
import sys

if os.environ.get("PYTHONHASHSEED") != "0":
    os.environ["PYTHONHASHSEED"] = "0"
    os.execv(sys.executable, [sys.executable, "-m", "aiomim.openai_study", *sys.argv[1:]])

from .cli import main

sys.exit(main())
