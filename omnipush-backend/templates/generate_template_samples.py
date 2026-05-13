#!/usr/bin/env python3
"""
Template Sample Generator

This script generates sample HTML files with small, medium, and large content
for all templates in the _templates/ directory. It creates variations to test
how templates handle different content lengths and sizes.
"""

import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import json

class TemplateSampleGenerator:
    def __init__(self, templates_dir: str = "_templates", output_dir: str = "sample_outputs"):
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Sample data for different content sizes
        self.sample_data = {
            "small": {
                "content": "Breaking News Update",
                "category": "NEWS",
                "source": "Reuters",
                "date": "2024-01-15",
                "channel_name": "News Channel",
                "lang": "en",
                "image_url": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1080&h=1080&fit=crop"
            },
            "medium": {
                "content": "Major Economic Policy Changes Announced by Government Officials Today",
                "category": "POLITICS",
                "source": "BBC News",
                "date": "2024-01-15",
                "channel_name": "Global News",
                "lang": "en",
                "image_url": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1080&h=1080&fit=crop"
            },
            "large": {
                "content": "Revolutionary Breakthrough in Artificial Intelligence Research Promises to Transform Healthcare Industry with Advanced Machine Learning Algorithms",
                "category": "TECHNOLOGY",
                "source": "TechCrunch International",
                "date": "2024-01-15",
                "channel_name": "Tech News Network",
                "lang": "en",
                "image_url": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1080&h=1080&fit=crop"
            }
        }
        
        # Tamil sample data
        self.tamil_sample_data = {
            "small": {
                "content": "முக்கிய செய்தி",
                "category": "செய்தி",
                "source": "தினமணி",
                "date": "2024-01-15",
                "channel_name": "தமிழ் செய்தி",
                "lang": "ta",
                "image_url": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1080&h=1080&fit=crop"
            },
            "medium": {
                "content": "அரசாங்கம் இன்று முக்கிய பொருளாதார கொள்கை மாற்றங்களை அறிவித்தது",
                "category": "அரசியல்",
                "source": "தி இந்து",
                "date": "2024-01-15",
                "channel_name": "தமிழ் செய்தி",
                "lang": "ta",
                "image_url": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1080&h=1080&fit=crop"
            },
            "large": {
                "content": "கணினி மற்றும் செயற்கை நுண்ணறிவு துறையில் புரட்சிகரமான முன்னேற்றம் மருத்துவத் துறையை மாற்றும் வகையில் மேம்பட்ட இயந்திர கற்றல் வழிமுறைகளை வழங்குகிறது",
                "category": "தொழில்நுட்பம்",
                "source": "தொழில்நுட்ப செய்திகள்",
                "date": "2024-01-15",
                "channel_name": "தமிழ் செய்தி",
                "lang": "ta",
                "image_url": "https://images.unsplash.com/photo-1586339949916-3e9457bef6d3?w=1080&h=1080&fit=crop"
            }
        }

    def find_template_files(self) -> List[Path]:
        """Find all HTML template files in the templates directory."""
        template_files = []
        
        # Find all HTML files recursively
        for html_file in self.templates_dir.rglob("*.html"):
            # Skip base templates and other non-newscard templates
            if html_file.name in ["base.html", "home.html", "post.html", "screenshots.html"]:
                continue
            template_files.append(html_file)
        
        return sorted(template_files)

    def extract_template_variables(self, template_content: str) -> List[str]:
        """Extract template variables from the content using regex."""
        # Find all {{variable}} patterns
        variables = re.findall(r'\{\{([^}]+)\}\}', template_content)
        return list(set(variables))  # Remove duplicates

    def render_template(self, template_content: str, data: Dict[str, Any]) -> str:
        """Render template with provided data."""
        rendered = template_content
        
        # Replace all template variables
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered

    def generate_sample_file(self, template_path: Path, size: str, language: str = "en") -> Path:
        """Generate a sample HTML file for a specific template, size, and language."""
        # Read template content
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Choose appropriate sample data
        if language == "ta":
            sample_data = self.tamil_sample_data[size]
        else:
            sample_data = self.sample_data[size]
        
        # Render template
        rendered_content = self.render_template(template_content, sample_data)
        
        # Create output directory structure
        relative_path = template_path.relative_to(self.templates_dir)
        output_subdir = self.output_dir / relative_path.parent
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        template_name = template_path.stem
        output_filename = f"{template_name}_{size}_{language}.html"
        output_path = output_subdir / output_filename
        
        # Write rendered content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_content)
        
        return output_path

    def generate_all_samples(self):
        """Generate sample files for all templates with all size and language combinations."""
        template_files = self.find_template_files()
        
        print(f"Found {len(template_files)} template files")
        print("Generating samples...")
        
        generated_files = []
        
        for template_path in template_files:
            print(f"\nProcessing: {template_path}")
            
            # Read template to check for language-specific variables
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Check if template has Tamil-specific content
            has_tamil = "lang-ta" in template_content or "TAMIL-UNI013" in template_content
            
            # Generate samples for each size
            for size in ["small", "medium", "large"]:
                # Generate English version
                output_path = self.generate_sample_file(template_path, size, "en")
                generated_files.append(output_path)
                print(f"  Generated: {output_path}")
                
                # Generate Tamil version if template supports it
                if has_tamil:
                    output_path = self.generate_sample_file(template_path, size, "ta")
                    generated_files.append(output_path)
                    print(f"  Generated: {output_path}")
        
        return generated_files

    def create_index_file(self, generated_files: List[Path]):
        """Create an index HTML file to view all generated samples."""
        index_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Template Samples Index</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }}
        .template-group {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .template-name {{
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}
        .samples-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}
        .sample-item {{
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            background: #fafafa;
        }}
        .sample-title {{
            font-weight: bold;
            color: #34495e;
            margin-bottom: 8px;
        }}
        .sample-links {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .sample-link {{
            display: inline-block;
            padding: 6px 12px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            transition: background 0.2s;
        }}
        .sample-link:hover {{
            background: #2980b9;
        }}
        .sample-link.small {{ background: #27ae60; }}
        .sample-link.medium {{ background: #f39c12; }}
        .sample-link.large {{ background: #e74c3c; }}
        .sample-link.small:hover {{ background: #229954; }}
        .sample-link.medium:hover {{ background: #e67e22; }}
        .sample-link.large:hover {{ background: #c0392b; }}
        .stats {{
            background: #2c3e50;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Template Samples Index</h1>
        
        <div class="stats">
            <strong>Generated {total_files} sample files</strong> | 
            <span style="color: #27ae60;">Small Content</span> | 
            <span style="color: #f39c12;">Medium Content</span> | 
            <span style="color: #e74c3c;">Large Content</span>
        </div>
        
        {template_groups}
    </div>
</body>
</html>"""
        
        # Group files by template
        template_groups = {}
        for file_path in generated_files:
            # Get template name from path
            relative_path = file_path.relative_to(self.output_dir)
            template_name = relative_path.stem.split('_')[0]  # Remove size and language suffixes
            
            if template_name not in template_groups:
                template_groups[template_name] = []
            template_groups[template_name].append(file_path)
        
        # Generate HTML for each template group
        groups_html = ""
        for template_name, files in template_groups.items():
            groups_html += f'<div class="template-group">\n'
            groups_html += f'<div class="template-name">{template_name}</div>\n'
            groups_html += '<div class="samples-grid">\n'
            
            # Group files by size and language
            samples = {}
            for file_path in files:
                parts = file_path.stem.split('_')
                if len(parts) >= 3:
                    size = parts[-2]
                    lang = parts[-1]
                    if size not in samples:
                        samples[size] = {}
                    samples[size][lang] = file_path
            
            for size in ["small", "medium", "large"]:
                if size in samples:
                    groups_html += '<div class="sample-item">\n'
                    groups_html += f'<div class="sample-title">{size.title()} Content</div>\n'
                    groups_html += '<div class="sample-links">\n'
                    
                    for lang, file_path in samples[size].items():
                        relative_url = file_path.relative_to(self.output_dir)
                        groups_html += f'<a href="{relative_url}" class="sample-link {size}" target="_blank">{lang.upper()}</a>\n'
                    
                    groups_html += '</div>\n</div>\n'
            
            groups_html += '</div>\n</div>\n'
        
        # Write index file
        final_content = index_content.format(
            total_files=len(generated_files),
            template_groups=groups_html
        )
        
        index_path = self.output_dir / "index.html"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        print(f"\nIndex file created: {index_path}")
        return index_path

    def run(self):
        """Main method to run the sample generation process."""
        print("Template Sample Generator")
        print("=" * 50)
        
        if not self.templates_dir.exists():
            print(f"Error: Templates directory '{self.templates_dir}' not found!")
            return
        
        # Generate all samples
        generated_files = self.generate_all_samples()
        
        # Create index file
        index_path = self.create_index_file(generated_files)
        
        print(f"\n" + "=" * 50)
        print(f"Generation complete!")
        print(f"Generated {len(generated_files)} sample files")
        print(f"Output directory: {self.output_dir}")
        print(f"Index file: {index_path}")
        print(f"\nOpen {index_path} in your browser to view all samples!")

def main():
    """Main entry point."""
    generator = TemplateSampleGenerator()
    generator.run()

if __name__ == "__main__":
    main()
