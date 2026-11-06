import os
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory

HERE = Path(__file__).resolve().parent
# In the Docker image the frontend is copied to ./static next to app.py;
# when running from a checkout it lives in ../frontend.
STATIC_DIR = HERE / "static" if (HERE / "static").is_dir() else HERE.parent / "frontend"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/")
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 2 * 1024 * 1024))


class DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that records duplicate mapping keys instead of silently
    keeping the last one (which is what PyYAML normally does)."""

    def __init__(self, stream):
        super().__init__(stream)
        self.duplicates = []

    def construct_mapping(self, node, deep=False):
        seen = {}
        for key_node, _ in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = self.construct_object(key_node, deep=True)
            try:
                first_line = seen.get(key)
            except TypeError:  # unhashable key (e.g. a list); PyYAML reports this itself
                continue
            line = key_node.start_mark.line + 1
            if first_line is not None:
                self.duplicates.append((key, line, first_line))
            else:
                seen[key] = line
        return super().construct_mapping(node, deep)


class CustomYAMLDumper(yaml.SafeDumper):
    pass


def _represent_none(dumper, _):
    return dumper.represent_scalar("tag:yaml.org,2002:null", "")


CustomYAMLDumper.add_representer(type(None), _represent_none)


def parse_documents(text):
    """Parse every document in a (possibly multi-document) YAML stream.
    Returns (documents, duplicate_keys)."""
    loader = DuplicateKeyLoader(text)
    try:
        documents = []
        while loader.check_data():
            documents.append(loader.get_data())
        return documents, loader.duplicates
    finally:
        loader.dispose()


def format_documents(documents):
    options = dict(Dumper=CustomYAMLDumper, default_flow_style=False, sort_keys=False,
                   allow_unicode=True, width=120)
    if len(documents) <= 1:
        return yaml.dump(documents[0] if documents else None, **options).strip()
    return yaml.dump_all(documents, explicit_start=True, **options).strip()


def process(content, filename):
    """Validate and format one file. Always returns the same response shape."""
    content = content.strip()
    result = {"filename": filename, "valid": False, "formatted": "", "error": None, "warnings": []}
    if not content:
        result["error"] = "Empty YAML content"
        return result
    try:
        documents, duplicates = parse_documents(content)
        formatted = format_documents(documents)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        if mark is not None:
            result["line"], result["column"] = mark.line + 1, mark.column + 1
            result["error"] = f"Line {mark.line + 1}, Column {mark.column + 1}: {getattr(e, 'problem', e)}"
        else:
            result["error"] = str(e)
        return result
    result.update(valid=True, formatted=formatted, lines=len(formatted.splitlines()),
                  documents=len(documents), warnings=get_yaml_warnings(content, duplicates))
    return result


def get_yaml_warnings(content, duplicates=()):
    """Check for common YAML issues."""
    warnings = []
    lines = content.split("\n")

    tab_lines = [i + 1 for i, line in enumerate(lines) if "\t" in line]
    if tab_lines:
        more = " ..." if len(tab_lines) > 5 else ""
        warnings.append({
            "type": "tab-found",
            "message": f"Tabs found on lines: {', '.join(map(str, tab_lines[:5]))}{more}. "
                       "Tabs should be replaced with spaces.",
            "severity": "warning",
        })

    indent_chars = {line[0] for line in lines if line and line[0] in (" ", "\t")}
    if len(indent_chars) > 1:
        warnings.append({
            "type": "mixed-indent",
            "message": "Mixed indentation detected (spaces and tabs). Use only spaces.",
            "severity": "warning",
        })

    for key, line, first_line in duplicates:
        warnings.append({
            "type": "duplicate-key",
            "message": f"Duplicate key '{key}' on line {line} (first defined on line {first_line}). "
                       "Only the last value is kept.",
            "severity": "warning",
        })
    return warnings


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    if (STATIC_DIR / path).is_file():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/validate", methods=["POST"])
def validate_yaml():
    """Validate and format YAML content."""
    data = _json_body()
    if data is None:
        return jsonify({"valid": False, "error": "Request body must be a JSON object"}), 400
    result = process(str(data.get("content", "")), str(data.get("filename", "untitled.yaml")))
    status = 400 if result["error"] == "Empty YAML content" else 200
    return jsonify(result), status


@app.route("/api/batch-validate", methods=["POST"])
def batch_validate():
    """Validate multiple YAML files."""
    data = _json_body()
    files = data.get("files") if data else None
    if not isinstance(files, list):
        return jsonify({"error": "Request body must be a JSON object with a 'files' list"}), 400
    results = [process(str(f.get("content", "")), str(f.get("filename", "untitled.yaml")))
               for f in files if isinstance(f, dict)]
    return jsonify({"results": results}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    # Development server only. The Docker image runs gunicorn instead.
    # Never enable debug mode on a reachable host: the Werkzeug debugger allows code execution.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5001)), debug=debug)
