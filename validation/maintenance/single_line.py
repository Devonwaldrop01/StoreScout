"""Lossless single-line transport for the previously validated Python sources."""
import ast
import hashlib
import json
from pathlib import Path
import shlex

EXPECTED = {
    "web": "9a99f6ecb6bb35cdbd5dca63fa6b0c8f72e8c3642c895dbffc1929907e136ea3",
    "idle": "2e437294afd29f0459df82a18cc50cc1a94e62a7eac81b67c6f5f7b87d29745a",
}


def encode(source):
    # json.dumps produces a Python-compatible ASCII string literal for these
    # sources. Decode and compare before returning anything executable.
    literal = json.dumps(source, ensure_ascii=True)
    assert ast.literal_eval(literal) == source
    wrapper = "exec(" + literal + ")"
    argv = ["python", "-I", "-S", "-B", "-u", "-c", wrapper]
    command = shlex.join(argv)
    assert not any(c in command for c in "\r\n\t\x00")
    assert shlex.split(command) == argv
    expression = ast.parse(wrapper).body[0].value
    assert isinstance(expression, ast.Call) and expression.func.id == "exec"
    assert len(expression.args) == 1 and not expression.keywords
    assert ast.literal_eval(expression.args[0]) == source
    return argv, command


def build(root=None):
    root = Path(root) if root else Path(__file__).resolve().parent
    commands = {}
    for mode, expected in EXPECTED.items():
        source = (root / (mode + ".py")).read_text(encoding="utf-8")
        digest = hashlib.sha256(source.encode()).hexdigest()
        assert digest == expected, (mode, "previously validated source changed", digest)
        imports = []
        for n in ast.walk(ast.parse(source)):
            if isinstance(n, ast.Import):
                imports.extend(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom):
                imports.append(n.module)
        assert set(imports) <= {"os", "signal", "threading", "http.server"}
        argv, command = encode(source)
        commands[mode] = {"argv": argv, "linux_command": command,
                          "source_sha256": digest, "imports": imports,
                          "multiline_argv": argv[:-1] + [source],
                          "command_sha256": hashlib.sha256(command.encode()).hexdigest(),
                          "characters": len(command)}
    return commands


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
