import os
import logging
from langchain_core.tools import tool
from core.utils import timing_decorator

logger = logging.getLogger(__name__)

@tool
@timing_decorator
def read_local_file(file_path: str) -> str:
    """Read the content of a local file. Use this to read uploaded challenge files.
    
    Args:
        file_path: The path to the file to read (e.g., 'files/app.js')
    
    Returns:
        The content of the file or an error message.
    """
    logger.info(f"📖 Reading local file: {file_path}")
    try:
        # Security check: Ensure file is within the 'files/' directory
        base_dir = os.path.abspath("files")
        target_file = os.path.abspath(file_path)
        
        # Check if the target file is within the base directory
        if not target_file.startswith(base_dir):
            logger.warning(f"⚠️ Access denied: Attempt to read file outside 'files/' directory: {file_path}")
            return "Error: Access denied. You can only read files in the 'files/' directory."

        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"
            
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        logger.info(f"✅ Read {len(content)} characters from {file_path}")
        
        # Truncate if too large, but give a generous limit for code files
        if len(content) > 100000:
            return f"File content (first 100000 chars):\n{content[:100000]}\n...(truncated)"
            
        return content
        
    except Exception as e:
        logger.error(f"❌ Error reading file {file_path}: {str(e)}")
        return f"Error reading file: {str(e)}"