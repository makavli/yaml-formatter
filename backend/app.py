from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yaml
import os
from io import StringIO

app = Flask(__name__, static_folder='static', static_url_path='/')
CORS(app)

class CustomYAMLLoader(yaml.SafeLoader):
    pass

class CustomYAMLDumper(yaml.SafeDumper):
    pass

def customize_dumper(dumper):
    def represent_none(dumper, _):
        return dumper.represent_scalar('tag:yaml.org,2002:null', '')
    
    dumper.add_representer(type(None), represent_none)

customize_dumper(CustomYAMLDumper)

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.exists(os.path.join('static', path)):
        return send_from_directory('static', path)
    return send_from_directory('static', 'index.html')

@app.route('/api/validate', methods=['POST'])
def validate_yaml():
    """Validate and format YAML content"""
    data = request.json
    yaml_content = data.get('content', '').strip()
    filename = data.get('filename', 'untitled.yaml')
    
    if not yaml_content:
        return jsonify({
            'valid': False,
            'error': 'Empty YAML content',
            'filename': filename,
            'formatted': ''
        }), 400
    
    try:
        # Parse YAML to validate
        parsed = yaml.load(yaml_content, Loader=CustomYAMLLoader)
        
        # Format YAML with proper indentation
        formatted = yaml.dump(
            parsed,
            Dumper=CustomYAMLDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120
        ).strip()
        
        # Get line count
        lines = len(formatted.split('\n'))
        
        return jsonify({
            'valid': True,
            'filename': filename,
            'formatted': formatted,
            'lines': lines,
            'error': None,
            'warnings': get_yaml_warnings(yaml_content, parsed)
        }), 200
        
    except yaml.YAMLError as e:
        # Parse error details
        error_msg = str(e)
        line_num = None
        col_num = None
        
        if hasattr(e, 'problem_mark'):
            mark = e.problem_mark
            line_num = mark.line + 1
            col_num = mark.column + 1
            error_msg = f"Line {line_num}, Column {col_num}: {e.problem}"
        
        return jsonify({
            'valid': False,
            'filename': filename,
            'formatted': '',
            'error': error_msg,
            'line': line_num,
            'column': col_num,
            'warnings': []
        }), 200
    
    except Exception as e:
        return jsonify({
            'valid': False,
            'filename': filename,
            'formatted': '',
            'error': f'Unexpected error: {str(e)}',
            'warnings': []
        }), 200

@app.route('/api/batch-validate', methods=['POST'])
def batch_validate():
    """Validate multiple YAML files"""
    data = request.json
    files = data.get('files', [])
    
    results = []
    for file_data in files:
        yaml_content = file_data.get('content', '').strip()
        filename = file_data.get('filename', 'untitled.yaml')
        
        try:
            parsed = yaml.load(yaml_content, Loader=CustomYAMLLoader)
            formatted = yaml.dump(
                parsed,
                Dumper=CustomYAMLDumper,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120
            ).strip()
            
            results.append({
                'filename': filename,
                'valid': True,
                'formatted': formatted,
                'lines': len(formatted.split('\n')),
                'error': None,
                'warnings': get_yaml_warnings(yaml_content, parsed)
            })
        except yaml.YAMLError as e:
            error_msg = str(e)
            line_num = None
            
            if hasattr(e, 'problem_mark'):
                mark = e.problem_mark
                line_num = mark.line + 1
                error_msg = f"Line {line_num}: {e.problem}"
            
            results.append({
                'filename': filename,
                'valid': False,
                'formatted': '',
                'error': error_msg,
                'line': line_num,
                'warnings': []
            })
        except Exception as e:
            results.append({
                'filename': filename,
                'valid': False,
                'formatted': '',
                'error': f'Error: {str(e)}',
                'warnings': []
            })
    
    return jsonify({'results': results}), 200

def get_yaml_warnings(content, parsed):
    """Check for common YAML issues"""
    warnings = []
    
    # Check for tabs
    if '\t' in content:
        tab_lines = [i + 1 for i, line in enumerate(content.split('\n')) if '\t' in line]
        warnings.append({
            'type': 'tab-found',
            'message': f'Tabs found on lines: {", ".join(map(str, tab_lines[:5]))}{" ..." if len(tab_lines) > 5 else ""}. Tabs should be replaced with spaces.',
            'severity': 'warning'
        })
    
    # Check for mixed indentation
    lines = content.split('\n')
    indent_chars = set()
    for line in lines:
        if line and line[0] in (' ', '\t'):
            indent_chars.add(line[0])
    
    if len(indent_chars) > 1:
        warnings.append({
            'type': 'mixed-indent',
            'message': 'Mixed indentation detected (spaces and tabs). Use only spaces.',
            'severity': 'warning'
        })
    
    # Check for duplicate keys
    if isinstance(parsed, dict):
        warnings.extend(check_duplicate_keys(parsed, 'root'))
    
    return warnings

def check_duplicate_keys(obj, path=''):
    """Recursively check for duplicate keys"""
    warnings = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                warnings.extend(check_duplicate_keys(value, new_path))
    
    return warnings

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
