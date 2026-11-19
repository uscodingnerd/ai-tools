import requests
from io import BytesIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

def extract_text_from_docx(docx_bytes):
    try:
        # Load the DOCX file from bytes
        with ZipFile(BytesIO(docx_bytes)) as docx:
            # Read the document.xml file which contains the text
            with docx.open('word/document.xml') as document:
                tree = ET.parse(document)
                root = tree.getroot()
                # Extract text from the XML structure
                text = []
                for elem in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                    if elem.text:
                        text.append(elem.text)
                return ''.join(text)
    except Exception as e:
        return f'Error extracting DOCX: {str(e)}'

# Fetch the document from the provided URL
try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(input_data.get('document_url', ''), headers=headers, timeout=30)
    response.raise_for_status()
    
    # Try to extract as DOCX (most common)
    extracted_text = extract_text_from_docx(response.content)
    
    if not extracted_text or 'Error' in extracted_text:
        extracted_text = 'Could not extract text from document. Ensure it is a valid DOCX file.'
    
    return {
        'resume_text': extracted_text,
        'success': True
    }
except Exception as e:
    return {'error': f'Failed to fetch/extract document: {str(e)}', 'success': False}
