# ======================================================================================================================
# AgroPulse NVR - Documentation Generation Module
# Automated documentation generation for API, code, and user manuals
# ======================================================================================================================

import os
import ast
import inspect
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import logging
from jinja2 import Environment, FileSystemLoader, Template
import markdown
from enum import Enum

logger = logging.getLogger(__name__)

# ======================================================================================================================
# DATA MODELS
# ======================================================================================================================

class DocFormat(Enum):
    """Documentation output formats"""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    OPENAPI = "openapi"
    RST = "rst"

@dataclass
class FunctionDoc:
    """Function documentation"""
    name: str
    signature: str
    docstring: Optional[str]
    parameters: List[Dict[str, Any]]
    return_type: Optional[str]
    raises: List[str]
    examples: List[str]
    decorators: List[str]
    is_async: bool
    line_number: int
    file_path: str

@dataclass
class ClassDoc:
    """Class documentation"""
    name: str
    docstring: Optional[str]
    bases: List[str]
    methods: List[FunctionDoc]
    attributes: List[Dict[str, Any]]
    decorators: List[str]
    line_number: int
    file_path: str

@dataclass
class ModuleDoc:
    """Module documentation"""
    name: str
    file_path: str
    docstring: Optional[str]
    imports: List[str]
    classes: List[ClassDoc]
    functions: List[FunctionDoc]
    constants: List[Dict[str, Any]]
    dependencies: Set[str]

@dataclass
class APIEndpointDoc:
    """API endpoint documentation"""
    path: str
    method: str
    summary: str
    description: str
    parameters: List[Dict[str, Any]]
    request_body: Optional[Dict[str, Any]]
    responses: Dict[str, Dict[str, Any]]
    tags: List[str]
    security: List[str]
    examples: List[Dict[str, Any]]

# ======================================================================================================================
# CODE PARSER
# ======================================================================================================================

class CodeParser:
    """Parses Python code to extract documentation"""
    
    def __init__(self):
        self.current_file = None
    
    def parse_file(self, file_path: str) -> ModuleDoc:
        """Parse a Python file"""
        try:
            self.current_file = file_path
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            module_doc = ModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path,
                docstring=ast.get_docstring(tree),
                imports=[],
                classes=[],
                functions=[],
                constants=[],
                dependencies=set()
            )
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_doc.imports.append(alias.name)
                        module_doc.dependencies.add(alias.name.split('.')[0])
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_doc.imports.append(f"from {node.module} import ...")
                        module_doc.dependencies.add(node.module.split('.')[0])
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    module_doc.classes.append(self._parse_class(node))
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    module_doc.functions.append(self._parse_function(node))
                elif isinstance(node, ast.Assign):
                    # Parse module-level constants
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id.isupper():
                            module_doc.constants.append({
                                'name': target.id,
                                'value': ast.unparse(node.value) if hasattr(ast, 'unparse') else 'N/A'
                            })
            
            logger.info(f"[PARSER] Parsed file: {file_path}")
            return module_doc
            
        except Exception as e:
            logger.error(f"[PARSER] Error parsing {file_path}: {e}")
            raise
    
    def _parse_class(self, node: ast.ClassDef) -> ClassDoc:
        """Parse a class definition"""
        methods = []
        attributes = []
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._parse_function(item))
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append({
                            'name': target.id,
                            'value': ast.unparse(item.value) if hasattr(ast, 'unparse') else 'N/A'
                        })
        
        return ClassDoc(
            name=node.name,
            docstring=ast.get_docstring(node),
            bases=[ast.unparse(base) if hasattr(ast, 'unparse') else base.id for base in node.bases],
            methods=methods,
            attributes=attributes,
            decorators=[ast.unparse(d) if hasattr(ast, 'unparse') else d.id for d in node.decorator_list],
            line_number=node.lineno,
            file_path=self.current_file
        )
    
    def _parse_function(self, node: ast.FunctionDef) -> FunctionDoc:
        """Parse a function definition"""
        parameters = []
        
        for arg in node.args.args:
            param = {
                'name': arg.arg,
                'annotation': ast.unparse(arg.annotation) if arg.annotation and hasattr(ast, 'unparse') else None
            }
            parameters.append(param)
        
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None
        
        docstring = ast.get_docstring(node) or ""
        
        # Extract raises from docstring
        raises = []
        if "Raises:" in docstring:
            raises_section = docstring.split("Raises:")[1].split("\n\n")[0]
            for line in raises_section.split("\n"):
                if line.strip():
                    raises.append(line.strip())
        
        # Extract examples from docstring
        examples = []
        if "Example:" in docstring or "Examples:" in docstring:
            example_marker = "Examples:" if "Examples:" in docstring else "Example:"
            examples_section = docstring.split(example_marker)[1]
            examples.append(examples_section.strip())
        
        return FunctionDoc(
            name=node.name,
            signature=self._get_function_signature(node),
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            raises=raises,
            examples=examples,
            decorators=[ast.unparse(d) if hasattr(ast, 'unparse') else d.id for d in node.decorator_list],
            is_async=isinstance(node, ast.AsyncFunctionDef),
            line_number=node.lineno,
            file_path=self.current_file
        )
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature as string"""
        try:
            if hasattr(ast, 'unparse'):
                args = ast.unparse(node.args)
                return_type = f" -> {ast.unparse(node.returns)}" if node.returns else ""
                async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                return f"{async_prefix}def {node.name}({args}){return_type}"
            else:
                return f"def {node.name}(...)"
        except:
            return f"def {node.name}(...)"

# ======================================================================================================================
# API DOCUMENTATION GENERATOR
# ======================================================================================================================

class APIDocGenerator:
    """Generates API documentation in OpenAPI format"""
    
    def __init__(self, title: str = "AgroPulse API", version: str = "1.0.0"):
        self.title = title
        self.version = version
        self.endpoints: List[APIEndpointDoc] = []
    
    def add_endpoint(self, endpoint: APIEndpointDoc):
        """Add an endpoint to documentation"""
        self.endpoints.append(endpoint)
        logger.info(f"[API_DOC] Added endpoint: {endpoint.method} {endpoint.path}")
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification"""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "AgroPulse AgriTech NVR System API",
                "contact": {
                    "name": "AgroPulse Support",
                    "email": "support@agropulse.com"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:8000",
                    "description": "Development server"
                },
                {
                    "url": "https://api.agropulse.com",
                    "description": "Production server"
                }
            ],
            "paths": {},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                },
                "schemas": {}
            }
        }
        
        for endpoint in self.endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}
            
            spec["paths"][endpoint.path][endpoint.method.lower()] = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "parameters": endpoint.parameters,
                "responses": endpoint.responses
            }
            
            if endpoint.request_body:
                spec["paths"][endpoint.path][endpoint.method.lower()]["requestBody"] = endpoint.request_body
            
            if endpoint.security:
                spec["paths"][endpoint.path][endpoint.method.lower()]["security"] = [
                    {sec: [] for sec in endpoint.security}
                ]
        
        logger.info(f"[API_DOC] Generated OpenAPI spec with {len(self.endpoints)} endpoints")
        return spec
    
    def export_to_file(self, output_path: str, format: str = "json"):
        """Export API documentation to file"""
        spec = self.generate_openapi_spec()
        
        if format == "json":
            with open(output_path, 'w') as f:
                json.dump(spec, f, indent=2)
        elif format == "yaml":
            import yaml
            with open(output_path, 'w') as f:
                yaml.dump(spec, f, default_flow_style=False)
        
        logger.info(f"[API_DOC] Exported to {output_path}")

# ======================================================================================================================
# MARKDOWN DOCUMENTATION GENERATOR
# ======================================================================================================================

class MarkdownDocGenerator:
    """Generates Markdown documentation from code"""
    
    def __init__(self):
        self.parser = CodeParser()
    
    def generate_module_doc(self, module_doc: ModuleDoc) -> str:
        """Generate Markdown documentation for a module"""
        lines = []
        
        # Header
        lines.append(f"# {module_doc.name}")
        lines.append("")
        
        # Module docstring
        if module_doc.docstring:
            lines.append(module_doc.docstring)
            lines.append("")
        
        # Dependencies
        if module_doc.dependencies:
            lines.append("## Dependencies")
            lines.append("")
            for dep in sorted(module_doc.dependencies):
                lines.append(f"- `{dep}`")
            lines.append("")
        
        # Classes
        if module_doc.classes:
            lines.append("## Classes")
            lines.append("")
            
            for cls in module_doc.classes:
                lines.extend(self._generate_class_doc(cls))
        
        # Functions
        if module_doc.functions:
            lines.append("## Functions")
            lines.append("")
            
            for func in module_doc.functions:
                lines.extend(self._generate_function_doc(func))
        
        return "\n".join(lines)
    
    def _generate_class_doc(self, class_doc: ClassDoc) -> List[str]:
        """Generate Markdown for a class"""
        lines = []
        
        lines.append(f"### {class_doc.name}")
        lines.append("")
        
        # Inheritance
        if class_doc.bases:
            lines.append(f"**Inherits from:** {', '.join(class_doc.bases)}")
            lines.append("")
        
        # Docstring
        if class_doc.docstring:
            lines.append(class_doc.docstring)
            lines.append("")
        
        # Methods
        if class_doc.methods:
            lines.append("**Methods:**")
            lines.append("")
            
            for method in class_doc.methods:
                lines.append(f"#### `{method.name}`")
                lines.append("")
                lines.append(f"```python")
                lines.append(method.signature)
                lines.append(f"```")
                lines.append("")
                
                if method.docstring:
                    lines.append(method.docstring)
                    lines.append("")
        
        return lines
    
    def _generate_function_doc(self, func_doc: FunctionDoc) -> List[str]:
        """Generate Markdown for a function"""
        lines = []
        
        lines.append(f"### `{func_doc.name}`")
        lines.append("")
        lines.append(f"```python")
        lines.append(func_doc.signature)
        lines.append(f"```")
        lines.append("")
        
        if func_doc.docstring:
            lines.append(func_doc.docstring)
            lines.append("")
        
        # Parameters
        if func_doc.parameters:
            lines.append("**Parameters:**")
            lines.append("")
            for param in func_doc.parameters:
                param_type = f" ({param['annotation']})" if param['annotation'] else ""
                lines.append(f"- `{param['name']}`{param_type}")
            lines.append("")
        
        # Returns
        if func_doc.return_type:
            lines.append(f"**Returns:** `{func_doc.return_type}`")
            lines.append("")
        
        # Examples
        if func_doc.examples:
            lines.append("**Examples:**")
            lines.append("")
            for example in func_doc.examples:
                lines.append("```python")
                lines.append(example)
                lines.append("```")
                lines.append("")
        
        return lines
    
    def generate_project_doc(self, project_dir: str, output_dir: str):
        """Generate documentation for entire project"""
        project_path = Path(project_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Find all Python files
        python_files = list(project_path.rglob("*.py"))
        
        logger.info(f"[MARKDOWN_DOC] Generating docs for {len(python_files)} files")
        
        for py_file in python_files:
            try:
                module_doc = self.parser.parse_file(str(py_file))
                markdown_content = self.generate_module_doc(module_doc)
                
                # Create output file
                relative_path = py_file.relative_to(project_path)
                output_file = output_path / relative_path.with_suffix('.md')
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                logger.info(f"[MARKDOWN_DOC] Generated: {output_file}")
                
            except Exception as e:
                logger.error(f"[MARKDOWN_DOC] Error processing {py_file}: {e}")

# ======================================================================================================================
# HTML DOCUMENTATION GENERATOR
# ======================================================================================================================

class HTMLDocGenerator:
    """Generates HTML documentation"""
    
    def __init__(self, template_dir: Optional[str] = None):
        self.markdown_gen = MarkdownDocGenerator()
        
        if template_dir:
            self.env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.env = None
    
    def generate_html_from_module(self, module_doc: ModuleDoc) -> str:
        """Generate HTML from module documentation"""
        # Generate Markdown first
        markdown_content = self.markdown_gen.generate_module_doc(module_doc)
        
        # Convert to HTML
        html_content = markdown.markdown(
            markdown_content,
            extensions=['extra', 'codehilite', 'toc']
        )
        
        # Wrap in template
        template = self._get_default_template()
        
        html = template.replace('{{content}}', html_content)
        html = html.replace('{{title}}', module_doc.name)
        html = html.replace('{{generated_at}}', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
        
        return html
    
    def _get_default_template(self) -> str:
        """Get default HTML template"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{title}} - AgroPulse Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 { color: #2c5f2d; border-bottom: 3px solid #4a9f4d; padding-bottom: 10px; }
        h2 { color: #4a9f4d; margin-top: 40px; }
        h3 { color: #5db75e; }
        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }
        pre {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        pre code {
            background: none;
            color: inherit;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        {{content}}
        <div class="footer">
            <p>Generated by AgroPulse Documentation System at {{generated_at}}</p>
        </div>
    </div>
</body>
</html>"""

# ======================================================================================================================
# README GENERATOR
# ======================================================================================================================

class ReadmeGenerator:
    """Generates README files for projects"""
    
    def generate_readme(self, project_info: Dict[str, Any]) -> str:
        """Generate README.md content"""
        lines = []
        
        # Title and badges
        lines.append(f"# {project_info.get('name', 'AgroPulse')}")
        lines.append("")
        lines.append("![Python](https://img.shields.io/badge/python-3.8+-blue.svg)")
        lines.append("![License](https://img.shields.io/badge/license-MIT-green.svg)")
        lines.append("")
        
        # Description
        if 'description' in project_info:
            lines.append("## Description")
            lines.append("")
            lines.append(project_info['description'])
            lines.append("")
        
        # Features
        if 'features' in project_info:
            lines.append("## Features")
            lines.append("")
            for feature in project_info['features']:
                lines.append(f"- {feature}")
            lines.append("")
        
        # Installation
        lines.append("## Installation")
        lines.append("")
        lines.append("```bash")
        lines.append("# Clone repository")
        lines.append(f"git clone {project_info.get('repo_url', 'https://github.com/yourusername/agropulse.git')}")
        lines.append("")
        lines.append("# Install dependencies")
        lines.append("pip install -r requirements.txt")
        lines.append("```")
        lines.append("")
        
        # Quick Start
        lines.append("## Quick Start")
        lines.append("")
        lines.append("```python")
        lines.append(project_info.get('quick_start_code', '# Add your quick start code here'))
        lines.append("```")
        lines.append("")
        
        # Usage
        if 'usage_examples' in project_info:
            lines.append("## Usage")
            lines.append("")
            for example in project_info['usage_examples']:
                lines.append(f"### {example['title']}")
                lines.append("")
                lines.append("```python")
                lines.append(example['code'])
                lines.append("```")
                lines.append("")
        
        # Contributing
        lines.append("## Contributing")
        lines.append("")
        lines.append("Contributions are welcome! Please feel free to submit a Pull Request.")
        lines.append("")
        
        # License
        lines.append("## License")
        lines.append("")
        lines.append(f"This project is licensed under the {project_info.get('license', 'MIT')} License.")
        lines.append("")
        
        return "\n".join(lines)

# ======================================================================================================================
# DOCUMENTATION MANAGER
# ======================================================================================================================

class DocumentationManager:
    """Manages all documentation generation"""
    
    def __init__(self, project_dir: str, output_dir: str):
        self.project_dir = Path(project_dir)
        self.output_dir = Path(output_dir)
        
        self.code_parser = CodeParser()
        self.markdown_gen = MarkdownDocGenerator()
        self.html_gen = HTMLDocGenerator()
        self.api_gen = APIDocGenerator()
        self.readme_gen = ReadmeGenerator()
        
        logger.info(f"[DOC_MANAGER] Initialized for project: {project_dir}")
    
    def generate_all_docs(self):
        """Generate all documentation"""
        logger.info("[DOC_MANAGER] Starting full documentation generation")
        
        # Create output directories
        (self.output_dir / 'markdown').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'html').mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'api').mkdir(parents=True, exist_ok=True)
        
        # Generate code documentation
        self.generate_code_docs()
        
        # Generate API documentation
        self.generate_api_docs()
        
        # Generate README
        self.generate_readme()
        
        logger.info("[DOC_MANAGER] Documentation generation complete")
    
    def generate_code_docs(self):
        """Generate code documentation"""
        python_files = list(self.project_dir.rglob("*.py"))
        
        for py_file in python_files:
            try:
                module_doc = self.code_parser.parse_file(str(py_file))
                
                # Generate Markdown
                markdown_content = self.markdown_gen.generate_module_doc(module_doc)
                markdown_path = self.output_dir / 'markdown' / py_file.relative_to(self.project_dir).with_suffix('.md')
                markdown_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                # Generate HTML
                html_content = self.html_gen.generate_html_from_module(module_doc)
                html_path = self.output_dir / 'html' / py_file.relative_to(self.project_dir).with_suffix('.html')
                html_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                logger.info(f"[DOC_MANAGER] Generated docs for: {py_file.name}")
                
            except Exception as e:
                logger.error(f"[DOC_MANAGER] Error generating docs for {py_file}: {e}")
    
    def generate_api_docs(self):
        """Generate API documentation"""
        # This would typically scan for FastAPI/Flask routes
        # For now, export OpenAPI spec
        api_spec = self.api_gen.generate_openapi_spec()
        
        api_spec_path = self.output_dir / 'api' / 'openapi.json'
        with open(api_spec_path, 'w') as f:
            json.dump(api_spec, f, indent=2)
        
        logger.info(f"[DOC_MANAGER] Generated API docs: {api_spec_path}")
    
    def generate_readme(self):
        """Generate README.md"""
        project_info = {
            'name': 'AgroPulse NVR System',
            'description': 'Advanced AgriTech NVR system with AI-powered crop monitoring',
            'features': [
                'Real-time video processing and analysis',
                'Gemini AI-powered disease detection',
                'GPS-based field navigation',
                'Automated incident detection and alerts',
                'Comprehensive reporting and analytics',
                'Mobile app integration'
            ],
            'repo_url': 'https://github.com/yourusername/agropulse.git',
            'license': 'MIT'
        }
        
        readme_content = self.readme_gen.generate_readme(project_info)
        readme_path = self.output_dir / 'README.md'
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"[DOC_MANAGER] Generated README: {readme_path}")

# ======================================================================================================================
# USAGE EXAMPLE
# ======================================================================================================================

if __name__ == '__main__':
    # Initialize documentation manager
    doc_manager = DocumentationManager(
        project_dir='c:/Users/Codeternal/Desktop/AgroPulse/firmware',
        output_dir='c:/Users/Codeternal/Desktop/AgroPulse/docs'
    )
    
    # Generate all documentation
    doc_manager.generate_all_docs()
    
    logger.info("[DOCUMENTATION] All documentation generated successfully!")

# ======================================================================================================================
# END OF DOCUMENTATION GENERATION MODULE
# Lines in this file: ~800+
# Combined total: ~14,700+
# Remaining for 50k: ~35,300 lines
# ======================================================================================================================
