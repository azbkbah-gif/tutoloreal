"""Le projet LookML doit passer le validateur sans erreur (équivalent de « Validate LookML »)."""

import subprocess
import sys


def test_lookml_valide():
    resultat = subprocess.run(
        [sys.executable, "scripts/valider_lookml.py"],
        capture_output=True,
        text=True,
    )
    assert resultat.returncode == 0, "\n" + resultat.stdout + resultat.stderr
