"""Offline checks for lossless command transport, without application imports."""
import ast
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

from single_line import EXPECTED, build, encode


class SingleLineTests(unittest.TestCase):
    def test_frozen_sources_and_html_input_compatibility(self):
        for mode, spec in build().items():
            with self.subTest(mode=mode):
                command = spec["linux_command"]
                self.assertEqual(command.replace("\n", "").replace("\r", ""), command)
                self.assertEqual(shlex.split(command), spec["argv"])
                self.assertEqual(spec["source_sha256"], EXPECTED[mode])
                literal = ast.parse(spec["argv"][-1]).body[0].value.args[0]
                self.assertEqual(ast.literal_eval(literal), spec["multiline_argv"][-1])
                self.assertEqual(spec["argv"][:6], ["python", "-I", "-S", "-B", "-u", "-c"])

    def test_literal_edge_cases_execute_without_expansion(self):
        values = ["'\"", "$HOME ${PORT} $(false) `false`", "; & | > < #",
                  "\\n\n\r\t\\", "unicode \u2603", "null\x00"]
        for value in values:
            with self.subTest(value=value):
                source = "import json;print(json.dumps(" + repr(value) + "))"
                argv, command = encode(source)
                decoded = shlex.split(command)
                self.assertEqual(argv, decoded)
                result = subprocess.run([sys.executable, *decoded[1:]], capture_output=True,
                                        text=True, timeout=5, env={})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), value)

    def test_modified_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for mode in EXPECTED:
                (root / (mode + ".py")).write_text("pass\n")
            with self.assertRaises(AssertionError):
                build(root)


if __name__ == "__main__":
    unittest.main()
