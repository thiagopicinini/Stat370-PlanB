"""
Data preparation utilities for Stat370-PlanB project.

Provides functions to:
- Filter enrollment data for undergraduate students only
- Extract text from PDF catalog files
- Batch process multiple data files
"""
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import ORIGINAL_DATA_DIR, FILTERED_DATA_DIR

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    print("Warning: PyPDF2 not installed. Install with: pip install PyPDF2")


def filter_ugrd_students(input_file, output_file):
    """
    Filter TSV file to keep only rows where Career == 'UGRD'
    
    Args:
        input_file: Path to input TSV file
        output_file: Path to output TSV file
    """
    # Read the TSV file
    df = pd.read_csv(input_file, sep='\t')
    
    # Filter for UGRD career only
    filtered_df = df[df['Career'] == 'UGRD']
    
    # Save filtered data
    filtered_df.to_csv(output_file, sep='\t', index=False)
    
    print(f"Processed {input_file}")
    print(f"  Original rows: {len(df)}")
    print(f"  Filtered rows: {len(filtered_df)}")
    print(f"  Removed rows: {len(df) - len(filtered_df)}")
    print(f"  Saved to: {output_file}\n")

def extract_text_from_pdf(pdf_file, output_file=None):
    """
    Extract text from a PDF file
    
    Args:
        pdf_file: Path to input PDF file
        output_file: Optional path to save extracted text (if None, returns text)
    
    Returns:
        Extracted text as string (if output_file is None)
    """
    if PyPDF2 is None:
        raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")
    
    pdf_file = Path(pdf_file)
    
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")
    
    # Extract text from PDF
    text_content = []
    
    try:
        with open(pdf_file, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            print(f"Processing PDF: {pdf_file.name}")
            print(f"  Total pages: {num_pages}")
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                text_content.append(f"--- Page {page_num + 1} ---\n{text}\n")
            
            full_text = '\n'.join(text_content)
            
            # Save to file if specified
            if output_file:
                output_file = Path(output_file)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(full_text)
                
                print(f"  Text extracted and saved to: {output_file}")
                print(f"  Total characters: {len(full_text)}\n")
            else:
                print(f"  Text extracted successfully")
                print(f"  Total characters: {len(full_text)}\n")
                return full_text
                
    except Exception as e:
        print(f"Error processing PDF {pdf_file}: {str(e)}")
        raise

def batch_extract_pdfs(pdf_directory, output_directory=None):
    """
    Extract text from all PDFs in a directory
    
    Args:
        pdf_directory: Directory containing PDF files
        output_directory: Directory to save extracted text files (default: pdf_directory/extracted_text)
    
    Returns:
        Dictionary mapping PDF filenames to extracted text
    """
    pdf_dir = Path(pdf_directory)
    
    if not pdf_dir.exists():
        raise FileNotFoundError(f"Directory not found: {pdf_dir}")
    
    # Set output directory
    if output_directory is None:
        output_dir = pdf_dir / 'extracted_text'
    else:
        output_dir = Path(output_directory)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(pdf_dir.glob('*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return {}
    
    print(f"Found {len(pdf_files)} PDF files\n")
    
    extracted_texts = {}
    
    for pdf_file in pdf_files:
        output_file = output_dir / f"{pdf_file.stem}.txt"
        try:
            text = extract_text_from_pdf(pdf_file, output_file)
            extracted_texts[pdf_file.name] = text
        except Exception as e:
            print(f"Failed to process {pdf_file.name}: {str(e)}\n")
            continue
    
    print(f"Extraction complete. Text files saved to: {output_dir}")
    return extracted_texts

def process_all_enrollment_files():
    """
    Process all enrollment files: filter for UGRD students and save to filtered_data.
    """
    print("Processing all enrollment files...\n")
    
    # Get all TSV files from original_data
    input_files = sorted(ORIGINAL_DATA_DIR.glob('deident_student_enrollment_*.tsv'))
    
    if not input_files:
        print(f"No enrollment files found in {ORIGINAL_DATA_DIR}")
        return
    
    print(f"Found {len(input_files)} files to process\n")
    
    for input_file in input_files:
        output_file = FILTERED_DATA_DIR / input_file.name
        filter_ugrd_students(str(input_file), str(output_file))
    
    print("\nAll files processed successfully!")


if __name__ == "__main__":
    process_all_enrollment_files()