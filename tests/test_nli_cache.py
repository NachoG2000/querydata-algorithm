"""Cached inference must survive reordering but never a model revision change."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from nli_local import LocalNLI


class NLICacheTest(unittest.TestCase):
    def test_reordering_normalization_and_revision_isolation(self):
        inferred = []

        def infer(engine, missing, pairs, found):
            inferred.extend(pairs[key] for key in missing)
            for key in missing:
                premise, hypothesis = pairs[key]
                logits = (float(len(premise)), float(len(hypothesis)), -1.0)
                engine.db.execute("INSERT INTO nli_logits VALUES (?,?,?,?)", (key, *logits))
                found[key] = logits
            engine.db.commit()

        with TemporaryDirectory() as directory, patch.object(LocalNLI, "_infer", infer):
            cache = Path(directory)
            with LocalNLI(cache, "model", "revision-1") as engine:
                first = engine.logits(["  A\tB ", "C", "A B"], ["H", "Other", "H"])
            self.assertEqual(len(inferred), 2)
            with LocalNLI(cache, "model", "revision-1") as engine:
                second = engine.logits(["C", "A B"], ["Other", "H"])
            np.testing.assert_array_equal(first[[1, 0]], second)
            self.assertEqual(len(inferred), 2)
            with LocalNLI(cache, "model", "revision-2") as engine:
                engine.logits(["A B"], ["H"])
            self.assertEqual(len(inferred), 3)


if __name__ == "__main__":
    unittest.main()
