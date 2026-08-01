#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DokuZen Pro - Code Splitter
===============================
Analysiert und zerlegt Python-Dateien in Komponenten.
"""

import ast
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum

from utils.logger import LoggerMixin


class CodeElementType(Enum):
    """Typen von Code-Elementen."""
    MODULE = "module"
    IMPORT = "import"
    CONSTANT = "constant"
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    DOCSTRING = "docstring"
    COMMENT = "comment"


@dataclass
class CodeElement:
    """Repräsentiert ein Code-Element."""
    element_type: CodeElementType
    name: str
    start_line: int
    end_line: int
    content: str
    docstring: Optional[str] = None
    parent: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    
    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1
    
    @property
    def preview(self) -> str:
        """Kurze Vorschau."""
        first_line = self.content.split('\n')[0][:60]
        return f"{self.name}: {first_line}..."


@dataclass
class CodeAnalysis:
    """Ergebnis einer Code-Analyse."""
    filepath: str
    elements: List[CodeElement]
    imports: List[str]
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    
    @property
    def classes(self) -> List[CodeElement]:
        return [e for e in self.elements if e.element_type == CodeElementType.CLASS]
    
    @property
    def functions(self) -> List[CodeElement]:
        return [e for e in self.elements if e.element_type == CodeElementType.FUNCTION]
    
    @property
    def summary(self) -> str:
        return (
            f"Datei: {Path(self.filepath).name}\n"
            f"Zeilen: {self.total_lines} (Code: {self.code_lines}, "
            f"Kommentare: {self.comment_lines}, Leer: {self.blank_lines})\n"
            f"Klassen: {len(self.classes)}, Funktionen: {len(self.functions)}\n"
            f"Imports: {len(self.imports)}"
        )


class CodeSplitter(LoggerMixin):
    """
    Analysiert und zerlegt Python-Code.
    
    Features:
    - AST-basierte Analyse
    - Extraktion von Klassen/Funktionen
    - Docstring-Erkennung
    - Export einzelner Komponenten
    - Statistiken
    """
    
    def __init__(self):
        self._current_source: str = ""
        self._current_lines: List[str] = []
    
    def analyze_file(self, filepath: str) -> Optional[CodeAnalysis]:
        """
        Analysiert eine Python-Datei.
        
        Args:
            filepath: Pfad zur .py-Datei
            
        Returns:
            CodeAnalysis oder None bei Fehler
        """
        path = Path(filepath)
        
        if not path.exists():
            self.logger.error(f"Datei nicht gefunden: {filepath}")
            return None
        
        if path.suffix.lower() != '.py':
            self.logger.error(f"Keine Python-Datei: {filepath} (Endung: {path.suffix})")
            return None  # Abbruch statt nur Warnung
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    source = f.read()
            except Exception as e:
                self.logger.error(f"Lesefehler: {e}")
                return None
        
        return self.analyze_source(source, filepath)
    
    def analyze_source(self, source: str, filepath: str = "<string>") -> Optional[CodeAnalysis]:
        """
        Analysiert Python-Quellcode.
        
        Args:
            source: Python-Quellcode
            filepath: Optionaler Dateipfad
            
        Returns:
            CodeAnalysis oder None bei Fehler
        """
        self._current_source = source
        self._current_lines = source.split('\n')
        
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            self.logger.error(f"Syntax-Fehler: {e}")
            return None
        
        elements = []
        imports = []
        
        # Top-Level-Elemente verarbeiten
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.extend(self._extract_imports(node))
            
            elif isinstance(node, ast.FunctionDef):
                elements.append(self._extract_function(node))
            
            elif isinstance(node, ast.AsyncFunctionDef):
                elements.append(self._extract_function(node, is_async=True))
            
            elif isinstance(node, ast.ClassDef):
                elements.append(self._extract_class(node))
            
            elif isinstance(node, ast.Assign):
                # Modul-Konstanten
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        elements.append(self._extract_constant(node, target.id))
        
        # Statistiken berechnen
        total_lines = len(self._current_lines)
        blank_lines = sum(1 for line in self._current_lines if not line.strip())
        comment_lines = sum(1 for line in self._current_lines if line.strip().startswith('#'))
        code_lines = total_lines - blank_lines - comment_lines
        
        return CodeAnalysis(
            filepath=filepath,
            elements=elements,
            imports=imports,
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines
        )
    
    def _extract_imports(self, node) -> List[str]:
        """Extrahiert Import-Statements."""
        imports = []
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        
        return imports
    
    def _extract_function(self, node: ast.FunctionDef, is_async: bool = False) -> CodeElement:
        """Extrahiert eine Funktion."""
        start_line = node.lineno
        end_line = self._get_end_line(node)
        
        # Decorators berücksichtigen
        if node.decorator_list:
            start_line = node.decorator_list[0].lineno
        
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        content = self._get_lines(start_line, end_line)
        docstring = ast.get_docstring(node)
        
        return CodeElement(
            element_type=CodeElementType.FUNCTION,
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            content=content,
            docstring=docstring,
            decorators=decorators
        )
    
    def _extract_class(self, node: ast.ClassDef) -> CodeElement:
        """Extrahiert eine Klasse."""
        start_line = node.lineno
        end_line = self._get_end_line(node)
        
        if node.decorator_list:
            start_line = node.decorator_list[0].lineno
        
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        content = self._get_lines(start_line, end_line)
        docstring = ast.get_docstring(node)
        
        return CodeElement(
            element_type=CodeElementType.CLASS,
            name=node.name,
            start_line=start_line,
            end_line=end_line,
            content=content,
            docstring=docstring,
            decorators=decorators
        )
    
    def _extract_constant(self, node: ast.Assign, name: str) -> CodeElement:
        """Extrahiert eine Konstante."""
        start_line = node.lineno
        end_line = self._get_end_line(node)
        content = self._get_lines(start_line, end_line)
        
        return CodeElement(
            element_type=CodeElementType.CONSTANT,
            name=name,
            start_line=start_line,
            end_line=end_line,
            content=content
        )
    
    def _get_end_line(self, node) -> int:
        """Ermittelt die Endzeile eines Nodes."""
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # Fallback: Maximale Endzeile aller Kinder
        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno'):
                max_line = max(max_line, child.lineno)
            if hasattr(child, 'end_lineno') and child.end_lineno:
                max_line = max(max_line, child.end_lineno)
        
        return max_line
    
    def _get_lines(self, start: int, end: int) -> str:
        """Holt Zeilen aus dem Quellcode."""
        return '\n'.join(self._current_lines[start-1:end])
    
    def _get_decorator_name(self, decorator) -> str:
        """Extrahiert den Decorator-Namen."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        return str(decorator)
    
    def split_to_files(self, analysis: CodeAnalysis, output_dir: str,
                       split_classes: bool = True,
                       split_functions: bool = True) -> List[str]:
        """
        Zerlegt Code in separate Dateien.
        
        Args:
            analysis: Code-Analyse
            output_dir: Ausgabeverzeichnis
            split_classes: Klassen in eigene Dateien
            split_functions: Funktionen in eigene Dateien
            
        Returns:
            Liste der erstellten Dateipfade
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        base_name = Path(analysis.filepath).stem
        
        # Imports sammeln
        imports_content = self._generate_imports_header(analysis.imports)
        
        # Klassen extrahieren
        if split_classes:
            for element in analysis.classes:
                filename = f"{base_name}_{element.name.lower()}.py"
                filepath = output_path / filename
                
                content = imports_content + "\n\n" + element.content
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                created_files.append(str(filepath))
                self.logger.info(f"Klasse extrahiert: {filename}")
        
        # Funktionen extrahieren
        if split_functions:
            # Nur Top-Level-Funktionen (nicht Methoden)
            functions = [e for e in analysis.functions if not e.parent]
            
            if functions:
                filename = f"{base_name}_functions.py"
                filepath = output_path / filename
                
                content = imports_content + "\n\n"
                content += "\n\n".join(e.content for e in functions)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                created_files.append(str(filepath))
                self.logger.info(f"Funktionen extrahiert: {filename}")
        
        return created_files
    
    def _generate_imports_header(self, imports: List[str]) -> str:
        """Generiert Import-Header."""
        if not imports:
            return ""
        
        lines = ["#!/usr/bin/env python3", "# -*- coding: utf-8 -*-", ""]
        
        # Standard-Imports gruppieren
        std_imports = []
        third_party = []
        
        for imp in imports:
            module = imp.split('.')[0]
            if module in ['os', 'sys', 're', 'json', 'typing', 'pathlib', 
                          'dataclasses', 'enum', 'datetime', 'collections']:
                std_imports.append(imp)
            else:
                third_party.append(imp)
        
        if std_imports:
            for imp in sorted(set(std_imports)):
                lines.append(f"import {imp}")
            lines.append("")
        
        if third_party:
            for imp in sorted(set(third_party)):
                lines.append(f"import {imp}")
        
        return '\n'.join(lines)
    
    def generate_summary(self, analysis: CodeAnalysis) -> str:
        """Generiert eine Zusammenfassung."""
        lines = [
            "=" * 60,
            f"CODE-ANALYSE: {Path(analysis.filepath).name}",
            "=" * 60,
            "",
            "STATISTIK:",
            f"  Gesamtzeilen:    {analysis.total_lines}",
            f"  Code-Zeilen:     {analysis.code_lines}",
            f"  Kommentare:      {analysis.comment_lines}",
            f"  Leerzeilen:      {analysis.blank_lines}",
            "",
            f"IMPORTE: {len(analysis.imports)}",
        ]
        
        for imp in analysis.imports[:10]:
            lines.append(f"  - {imp}")
        if len(analysis.imports) > 10:
            lines.append(f"  ... und {len(analysis.imports) - 10} weitere")
        
        lines.extend(["", f"KLASSEN: {len(analysis.classes)}"])
        for cls in analysis.classes:
            doc = f" - {cls.docstring[:40]}..." if cls.docstring else ""
            lines.append(f"  • {cls.name} (Z.{cls.start_line}-{cls.end_line}){doc}")
        
        lines.extend(["", f"FUNKTIONEN: {len(analysis.functions)}"])
        for func in analysis.functions:
            dec = f" @{func.decorators[0]}" if func.decorators else ""
            lines.append(f"  • {func.name}(){dec} (Z.{func.start_line}-{func.end_line})")
        
        lines.append("")
        lines.append("=" * 60)
        
        return '\n'.join(lines)


# === Hilfsfunktionen ===

def analyze_python_file(filepath: str) -> Optional[CodeAnalysis]:
    """Schnelle Analyse einer Python-Datei."""
    splitter = CodeSplitter()
    return splitter.analyze_file(filepath)


def split_python_file(filepath: str, output_dir: str) -> List[str]:
    """Zerlegt eine Python-Datei in Komponenten."""
    splitter = CodeSplitter()
    analysis = splitter.analyze_file(filepath)
    
    if analysis:
        return splitter.split_to_files(analysis, output_dir)
    return []
