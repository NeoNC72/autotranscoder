import os
import sys
import argparse
import concurrent.futures
import subprocess
import shutil
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser(description="Transcode FLAC files to MP3")
    parser.add_argument("input_folder", help="Input folder containing FLAC files")
    parser.add_argument("output_folder", help="Output folder for MP3 files")
    parser.add_argument("--threads", type=int, default=os.cpu_count(), 
                        help="Number of threads to use (default: number of CPU cores)")
    parser.add_argument("--min-size", type=int, default=200, 
                        help="Minimum file size in KB (default: 200KB)")
    parser.add_argument("--delete-small", action="store_true",
                        help="Delete small files that are likely fake")
    return parser.parse_args()

def is_file_too_small(file_path, min_size_kb):
    """Check if file is too small (likely fake)"""
    try:
        file_size_kb = os.path.getsize(file_path) / 1024
        return file_size_kb < min_size_kb
    except Exception:
        return False

def delete_small_file(file_path):
    """Delete a file that's too small (likely fake)"""
    try:
        os.remove(file_path)
        print(f"Deleted small file (likely fake): {file_path}")
        return True
    except Exception as e:
        print(f"Failed to delete {file_path}: {str(e)}")
        return False

def find_audio_files(input_folder, min_size_kb=200, delete_small=False):
    """Recursively find all .flac and .mp3 files in the input folder"""
    audio_files = []
    small_files_count = 0
    
    for root, _, files in os.walk(input_folder):
        for file in files:
            file_lower = file.lower()
            full_path = os.path.join(root, file)
            
            if file_lower.endswith(('.flac', '.mp3')):
                # Check if file is too small (likely fake)
                if is_file_too_small(full_path, min_size_kb):
                    small_files_count += 1
                    print(f"Found small file (likely fake): {full_path}")
                    if delete_small:
                        delete_small_file(full_path)
                    continue
                
                file_type = 'flac' if file_lower.endswith('.flac') else 'mp3'
                audio_files.append((full_path, file_type))
    
    if small_files_count > 0:
        action = "Deleted" if delete_small else "Skipped"
        print(f"{action} {small_files_count} small files (likely fake)")
    
    return audio_files

def get_unique_output_path(output_file):
    """Handle filename conflicts by adding an index if necessary"""
    if not os.path.exists(output_file):
        return output_file
    
    name, ext = os.path.splitext(output_file)
    index = 1
    while os.path.exists(f"{name}_{index}{ext}"):
        index += 1
    
    return f"{name}_{index}{ext}"

def copy_file(mp3_file, output_folder):
    """Copy an MP3 file to the output folder"""
    try:
        # Use Path objects to handle Unicode paths correctly
        mp3_path = Path(mp3_file)
        output_dir = Path(output_folder)
        
        # Create the output path
        output_file = output_dir / mp3_path.name
        # Get a unique output path if there's a conflict
        output_file = get_unique_output_path(str(output_file))
        
        # Copy the file
        shutil.copy2(mp3_file, output_file)
        
        print(f"\nCopied MP3 file: {mp3_file} -> {output_file}")
        return True
    except Exception as e:
        print(f"Exception while copying {mp3_file}: {str(e)}")
        return False

def transcode_file(flac_file, output_folder):
    """Transcode a FLAC file to MP3 using ffmpeg"""
    try:
        # Use Path objects to handle Unicode paths correctly
        flac_path = Path(flac_file)
        output_dir = Path(output_folder)
        
        # Extract just the filename without the path
        filename = flac_path.name
        # Change extension from .flac to .mp3
        mp3_filename = flac_path.stem + ".mp3"
        # Create the output path
        output_file = output_dir / mp3_filename
        # Get a unique output path if there's a conflict
        output_file = get_unique_output_path(str(output_file))
        
        # Set environment with UTF-8 encoding for subprocess
        my_env = os.environ.copy()
        my_env["PYTHONIOENCODING"] = "utf-8"
        
        # Run ffmpeg to transcode the file
        cmd = [
            "ffmpeg",
            "-i", str(flac_path),
            "-b:a", "320k",  # 320 kbps bitrate
            "-c:a", "libmp3lame",  # MP3 codec
            "-y",  # Overwrite output file if it exists
            "-loglevel", "error",  # Reduce log output
            str(output_file)
        ]
        
        process = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            encoding='utf-8',  # Explicitly set encoding to UTF-8
            errors='replace',  # Replace invalid characters
            env=my_env,
        )
        
        if process.returncode == 0:
            print(f"\nSuccessfully transcoded: {flac_file} -> {output_file}")
            return True
        else:
            print(f"\nError transcoding {flac_file}: {process.stderr}")
            return False
            
    except Exception as e:
        print(f"Exception while processing {flac_file}: {str(e)}")
        return False

def process_file(file_info, output_folder):
    """Process a file based on its type"""
    file_path, file_type = file_info
    
    if file_type == 'mp3':
        return copy_file(file_path, output_folder)
    else:  # flac
        return transcode_file(file_path, output_folder)

def display_progress(completed, failed, total):
    """Display a simple progress bar"""
    width = 50  # width of the progress bar
    percentage = (completed + failed) / total if total > 0 else 0
    filled_width = int(width * percentage)
    bar = '█' * filled_width + '-' * (width - filled_width)
    sys.stdout.write(f"\rProgress: [{bar}] {percentage*100:.1f}% ({completed + failed}/{total}, {completed} succeeded, {failed} failed)")
    sys.stdout.flush()

def main():
    args = parse_arguments()
    
    # Ensure the output folder exists
    os.makedirs(args.output_folder, exist_ok=True)
    
    # Find all audio files
    print("Scanning for FLAC and MP3 files...")
    audio_files = find_audio_files(args.input_folder, args.min_size, args.delete_small)
    total_files = len(audio_files)
    
    if total_files == 0:
        print("No valid audio files found in the input folder.")
        sys.exit(0)
    
    flac_count = sum(1 for _, file_type in audio_files if file_type == 'flac')
    mp3_count = sum(1 for _, file_type in audio_files if file_type == 'mp3')
    print(f"Found {total_files} valid audio files ({flac_count} FLAC, {mp3_count} MP3).")
    
    # Process files in parallel
    print(f"Processing with {args.threads} threads...")
    
    completed = 0
    failed = 0
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(process_file, file_info, args.output_folder): file_info 
                  for file_info in audio_files}
        
        # Process as they complete
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                completed += 1
            else:
                failed += 1
            display_progress(completed, failed, total_files)
    
    print(f"\nProcessing complete. {completed} files succeeded, {failed} files failed.")

if __name__ == "__main__":
    # Ensure proper handling of Unicode characters
    if sys.platform == "win32":
        # For Windows
        os.system("chcp 65001 > NUL")
        # Force UTF-8 for I/O operations
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    
    main()
