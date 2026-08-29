import io
import zipfile

def extract_file_from_zip_io(zip_buffer:io.BytesIO, filepath:str):
    """
    Receive BytesIO buffer of a zip-file and returns bytes buffer
    of unzipped file from specified path
    """
    with zipfile.ZipFile(zip_buffer) as z:
        # Reads raw bytes into memory
        file_bytes = z.read(filepath)
        # Remains open after context closes
        return io.BytesIO(file_bytes)