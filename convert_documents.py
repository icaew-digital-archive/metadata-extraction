#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Standalone document conversion script for converting DOCX/DOC files and images to PDF.
This script processes all Office documents and image files in a directory and converts them to PDF format.
"""

import os
import tempfile
import subprocess
from pathlib import Path
from typing import List, Tuple


def convert_to_pdf(input_path: str) -> Tuple[str, bool]:
    """
    Convert a DOCX/DOC/TXT/SRT or image file to PDF format.
    
    Args:
        input_path (str): Path to the input file (DOCX, DOC, TXT, SRT, JPG, JPEG, PNG, or TIFF)
        
    Returns:
        Tuple[str, bool]: (path_to_pdf, was_converted)
            - path_to_pdf: Path to the converted PDF file (or original if already PDF)
            - was_converted: True if conversion was performed, False if already PDF
    """
    input_path = Path(input_path)
    
    # Check if file exists
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # If already PDF, return as-is
    if input_path.suffix.lower() == '.pdf':
        return str(input_path), False
    
    # Check if it's a supported format
    supported_formats = ['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.srt', '.vtt', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
    if input_path.suffix.lower() not in supported_formats:
        raise ValueError(f"Unsupported file format: {input_path.suffix}. Supported formats: {', '.join(supported_formats)}")
    
    print(f"Converting {input_path.name} to PDF...")
    
    try:
        # For text-based files (TXT, SRT), use text-to-PDF conversion
        if input_path.suffix.lower() in ['.txt', '.srt']:
            pdf_path = _convert_text_to_pdf(input_path)
            if pdf_path:
                print(f"Successfully converted {input_path.name} to PDF using text conversion")
                return pdf_path, True
        
        # For image files, use image-to-PDF conversion
        if input_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            pdf_path = _convert_image_to_pdf(input_path)
            if pdf_path:
                print(f"Successfully converted {input_path.name} to PDF using image conversion")
                return pdf_path, True
        
        # For Office documents, try LibreOffice first
        pdf_path = _convert_with_libreoffice(input_path)
        if pdf_path:
            print(f"Successfully converted {input_path.name} to PDF using LibreOffice")
            return pdf_path, True
        
        # Fallback to Pandoc if LibreOffice fails
        pdf_path = _convert_with_pandoc(input_path)
        if pdf_path:
            print(f"Successfully converted {input_path.name} to PDF using Pandoc")
            return pdf_path, True
        
        # If all methods fail, raise an error
        raise RuntimeError(f"Failed to convert {input_path.name} to PDF. Please ensure LibreOffice, Pandoc, or Pillow is installed.")
        
    except Exception as e:
        print(f"Error converting {input_path.name}: {str(e)}")
        raise


def _convert_with_libreoffice(input_path: Path) -> str:
    """
    Convert document to PDF using LibreOffice.
    
    Args:
        input_path (Path): Path to the input file
        
    Returns:
        str: Path to the converted PDF file
    """
    # Create temporary directory for output
    temp_dir = tempfile.mkdtemp()
    output_dir = Path(temp_dir)
    
    try:
        # LibreOffice command
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', str(output_dir),
            str(input_path)
        ]
        
        # Run conversion
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Find the generated PDF file
            pdf_files = list(output_dir.glob('*.pdf'))
            if pdf_files:
                pdf_path = pdf_files[0]
                # Move to the same directory as the original file
                final_pdf_path = input_path.with_suffix('.pdf')
                pdf_path.rename(final_pdf_path)
                return str(final_pdf_path)
        
        raise RuntimeError(f"LibreOffice conversion failed for {input_path.name}")
        
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary directory {temp_dir}: {str(e)}")


def _convert_with_pandoc(input_path: Path) -> str:
    """
    Convert document to PDF using Pandoc.
    
    Args:
        input_path (Path): Path to the input file
        
    Returns:
        str: Path to the converted PDF file
    """
    output_path = input_path.with_suffix('.pdf')
    
    # Pandoc command
    cmd = [
        'pandoc',
        str(input_path),
        '-o', str(output_path)
    ]
    
    # Run conversion
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0 and output_path.exists():
        return str(output_path)
    
    raise RuntimeError(f"Pandoc conversion failed for {input_path.name}")


def _convert_text_to_pdf(input_path: Path) -> str:
    """
    Convert text-based files (TXT, SRT) to PDF using Python.
    
    Args:
        input_path (Path): Path to the input file
        
    Returns:
        str: Path to the converted PDF file
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        raise RuntimeError("reportlab library is required for text-to-PDF conversion. Install with: pip install reportlab")
    
    output_path = input_path.with_suffix('.pdf')
    
    # Read the text file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding if UTF-8 fails
        try:
            with open(input_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            raise RuntimeError(f"Could not read file {input_path.name}: {str(e)}")
    
    # Create PDF document with ultra-minimal margins for maximum text density
    doc = SimpleDocTemplate(
        str(output_path), 
        pagesize=A4,
        leftMargin=0.25*inch,   # Ultra-reduced from 0.5 inch
        rightMargin=0.25*inch,  # Ultra-reduced from 0.5 inch
        topMargin=0.25*inch,    # Ultra-reduced from 0.5 inch
        bottomMargin=0.25*inch  # Ultra-reduced from 0.5 inch
    )
    styles = getSampleStyleSheet()
    
    # Create ultra-compact style for maximum text density
    text_style = ParagraphStyle(
        'UltraCompactText',
        parent=styles['Normal'],
        fontSize=8,              # Further reduced from 9
        leading=9,               # Further reduced from 11 (ultra-tight line spacing)
        spaceAfter=1,            # Minimal paragraph spacing
        spaceBefore=0,           # No space before paragraphs
        alignment=0,             # Left alignment
        wordWrap='CJK',          # Better word wrapping
        leftIndent=0,            # No left indentation
        rightIndent=0,           # No right indentation
        firstLineIndent=0        # No first line indentation
    )
    
    # Process content based on file type
    if input_path.suffix.lower() == '.srt':
        # For SRT files, clean up subtitle formatting
        content = _clean_srt_content(content)
    elif input_path.suffix.lower() == '.vtt':
        # For VTT files, clean up WebVTT formatting
        content = _clean_vtt_content(content)
    
    # Create continuous text flow by joining all content with spaces
    # This eliminates all line breaks and creates one massive paragraph
    continuous_text = content.replace('\n\n', ' ').replace('\n', ' ').strip()
    
    # Create story (content) for PDF - just one continuous paragraph
    story = [Paragraph(continuous_text, text_style)]
    
    # Build PDF
    doc.build(story)
    
    return str(output_path)


def _convert_image_to_pdf(input_path: Path) -> str:
    """
    Convert image files to PDF using Pillow (PIL).
    
    Args:
        input_path (Path): Path to the input image file
        
    Returns:
        str: Path to the converted PDF file
    """
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow (PIL) library is required for image-to-PDF conversion. Install with: pip install Pillow")
    
    output_path = input_path.with_suffix('.pdf')
    
    try:
        # Open the image
        with Image.open(input_path) as img:
            # Convert to RGB if necessary (PDF doesn't support RGBA)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Save as PDF
            img.save(str(output_path), 'PDF', resolution=100.0)
            
            return str(output_path)
            
    except Exception as e:
        raise RuntimeError(f"Failed to convert image {input_path.name} to PDF: {str(e)}")


def _clean_srt_content(content: str) -> str:
    """
    Clean up SRT subtitle content for better PDF formatting.
    
    Args:
        content (str): Raw SRT content
        
    Returns:
        str: Cleaned content
    """
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip subtitle numbers and timestamps
        if (line.isdigit() or 
            '-->' in line or 
            line == '' or
            line.startswith('[') and line.endswith(']')):
            continue
        
        # Keep actual subtitle text
        if line:
            cleaned_lines.append(line)
    
    # Join lines with double newlines for paragraph separation
    return '\n\n'.join(cleaned_lines)


def _clean_vtt_content(content: str) -> str:
    """
    Clean up WebVTT subtitle content for better PDF formatting.
    
    Args:
        content (str): Raw WebVTT content
        
    Returns:
        str: Cleaned content
    """
    lines = content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip WebVTT header lines
        if line.startswith('WEBVTT') or line.startswith('X-TIMESTAMP-MAP') or line.startswith('X-WRITER'):
            continue
        
        # Keep actual subtitle text
        if line:
            cleaned_lines.append(line)
    
    # Join lines with double newlines for paragraph separation
    return '\n\n'.join(cleaned_lines)


def get_supported_formats() -> list:
    """
    Get list of supported input file formats.
    
    Returns:
        list: List of supported file extensions
    """
    return ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.srt', '.vtt', '.jpg', '.jpeg', '.png', '.tiff', '.tif']


def is_supported_format(file_path: str) -> bool:
    """
    Check if a file format is supported for processing.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if the format is supported
    """
    return Path(file_path).suffix.lower() in get_supported_formats()


def convert_directory(directory_path: str) -> List[str]:
    """
    Convert all DOCX/DOC files in a directory to PDF.
    
    Args:
        directory_path (str): Path to the directory containing files
        
    Returns:
        List[str]: List of paths to all PDF files (original + converted)
    """
    directory = Path(directory_path)
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    print(f"Scanning directory: {directory_path}")
    
    # Get all supported files
    supported_files = []
    for file_path in directory.iterdir():
        if file_path.is_file() and is_supported_format(str(file_path)):
            supported_files.append(str(file_path))
    
    print(f"Found {len(supported_files)} supported files")
    
    # Convert files and collect PDF paths
    pdf_files = []
    converted_count = 0
    
    # Create a format mapping file to track original formats
    format_mapping = {}
    
    for file_path in supported_files:
        try:
            pdf_path, was_converted = convert_to_pdf(file_path)
            pdf_files.append(pdf_path)
            
            if was_converted:
                converted_count += 1
                # Store the original format mapping
                original_ext = Path(file_path).suffix.lower()
                if original_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.srt', '.vtt']:
                    format_mapping[str(pdf_path)] = original_ext[1:]  # Remove the dot
                
        except Exception as e:
            print(f"Failed to convert {file_path}: {str(e)}")
            # If conversion fails, skip the file
            continue
    
    # Write format mapping to a JSON file
    if format_mapping:
        import json
        mapping_file = directory / "format_mapping.json"
        with open(mapping_file, 'w') as f:
            json.dump(format_mapping, f, indent=2)
        print(f"Format mapping saved to: {mapping_file}")
    
    print(f"Conversion complete: {converted_count} files converted to PDF")
    print(f"Total PDF files available: {len(pdf_files)}")
    
    return pdf_files


def main():
    """Main function for standalone document conversion."""
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python convert_documents.py <directory_path>")
        print("This script converts all DOCX/DOC/XLSX/XLS/PPTX/PPT/TXT/SRT/VTT and image files (JPG, PNG, TIFF) in the specified directory to PDF.")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    
    try:
        pdf_files = convert_directory(directory_path)
        print(f"\nSuccessfully processed {len(pdf_files)} files")
        print("PDF files ready for metadata extraction:")
        for pdf_file in pdf_files:
            print(f"  - {pdf_file}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 