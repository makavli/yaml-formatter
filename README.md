# YAML Formatter 📋

A containerized web application for validating and formatting YAML files. Perfect for fixing indentation issues in Azure DevOps pipelines, Kubernetes manifests, Docker Compose files, and any other YAML-based configuration.

## Features

- ✅ **Validate YAML Syntax** - Instantly check for parsing errors
- 🎯 **Auto-Format** - Fix indentation and structure automatically
- 📁 **Drag & Drop** - Upload multiple YAML files at once
- 📝 **Paste Content** - Or paste YAML directly from clipboard
- 🔎 **Multiple File Support** - Process several files without reloading
- 🎨 **Visual Feedback** - Clear indicators of valid/invalid files
- ⚠️ **Warnings** - Detect tabs, mixed indentation, and other issues
- 📋 **Easy Copy** - One-click copy formatted YAML to clipboard
- 🐳 **Fully Containerized** - Docker & Docker Compose ready

## Tech Stack

- **Backend:** Python Flask + PyYAML
- **Frontend:** Vanilla HTML5, CSS3, JavaScript
- **Containerization:** Docker & Docker Compose

## Quick Start

### Using Docker Compose (Recommended)

```bash
cd yaml-formatter
docker-compose up -d
# Open http://localhost:5001
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python backend/app.py
# Open http://localhost:5001
```

## Usage

### Web Interface

1. **Upload Files:**
   - Drag YAML files onto the upload area, or
   - Click to browse and select files, or
   - Paste YAML content in the textarea

2. **Validate & Format:**
   - Click "Validate & Format" button
   - View formatted output in the right panel
   - Check validation results for errors/warnings

3. **Manage Multiple Files:**
   - Files list shows all loaded files
   - Click any file to view/validate it
   - Status badges show valid/invalid state

4. **Export Results:**
   - Click "Copy to Clipboard" to copy formatted YAML
   - Use formatted output in your pipelines/configs

### Supported YAML Types

- Azure DevOps Pipelines (`azure-pipelines.yml`)
- Kubernetes Manifests (`deployment.yaml`, `service.yaml`)
- Docker Compose (`docker-compose.yml`)
- GitHub Actions (`.github/workflows/*.yml`)
- Ansible Playbooks
- CI/CD Configuration
- Any standard YAML file

### API Endpoints

- `POST /api/validate` - Validate and format a single YAML file
  ```bash
  curl -X POST http://localhost:5001/api/validate \
    -H "Content-Type: application/json" \
    -d '{
      "content": "key: value\n  nested: data",
      "filename": "config.yaml"
    }'
  ```

- `POST /api/batch-validate` - Validate multiple files at once
- `GET /health` - Health check endpoint

## Features in Detail

### Validation
- Checks YAML syntax correctness
- Reports line and column numbers for errors
- Shows descriptive error messages

### Formatting
- Normalizes indentation (2 spaces, configurable)
- Sorts keys consistently
- Handles Unicode properly
- Respects YAML structure

### Warnings
- **Tab Detection** - Alerts when tabs are used instead of spaces
- **Mixed Indentation** - Detects inconsistent spacing
- **Structure Issues** - Warns about potential YAML problems

## Example Conversions

### Input (bad indentation)
```yaml
name: My Pipeline
trigger:
  - main
    branches:
      include:
  - develop
      exclude: []
jobs:
    - job: Build
      steps:
      - script: echo Hello
```

### Output (fixed)
```yaml
name: My Pipeline
trigger:
  - main
  - develop
jobs:
  - job: Build
    steps:
      - script: echo Hello
```

## Project Structure

```
yaml-formatter/
├── backend/
│   └── app.py              # Flask API and YAML processing
├── frontend/
│   └── index.html          # Web interface with drag-and-drop
├── Dockerfile              # Container build definition
├── docker-compose.yml      # Multi-container orchestration
├── requirements.txt        # Python dependencies
├── .dockerignore            # Files excluded from build
├── .gitignore               # Git ignore patterns
└── README.md               # This file
```

## Development Tips

### Adding Custom YAML Rules
Edit the `backend/app.py` to add custom validation rules in the `get_yaml_warnings()` function.

### Customizing Formatting
Modify the `yaml.dump()` parameters in `app.py` to change formatting style (indentation, flow style, etc.)

### Extended Error Reporting
The API can be extended to provide more detailed error information including:
- Suggested fixes
- Context around errors
- Comparison with fixed version

## Troubleshooting

### Port 5001 already in use
Change port in `docker-compose.yml`:
```yaml
ports:
  - "8001:5001"  # Access at http://localhost:8001
```

### Container won't start
Check logs:
```bash
docker-compose logs -f yaml-formatter
```

### YAML not formatting correctly
Some YAML anchors, aliases, and custom tags may not be preserved. This is a limitation of the PyYAML library.

## Limitations

- Custom YAML tags are not preserved
- Anchors and aliases are resolved
- Comments in YAML are not preserved during formatting
- Very large files (>10MB) may timeout

## Performance

- Single file validation: < 100ms
- Batch validation (10 files): < 500ms
- Formatting preserves logical structure

## Contributing

Feel free to extend with:
- YAML to JSON/TOML conversion
- Schema validation
- Linting rules
- UI improvements
- Additional export formats

## License

MIT License - Use freely for personal and commercial projects.

---

**YAML Formatter** - Fix your YAML, fix your pipeline! 📋
