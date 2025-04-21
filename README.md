# FLAC to MP3 Transcoder & Copier

This script recursively transcodes FLAC audio files to MP3 format and copies existing MP3 files, flattening the directory structure into a single output folder.

## Usage

```bash
python autotranscode.py input_folder output_folder [options]
```

## Arguments

*   `input_folder`: The path to the folder containing the source audio files (FLAC and MP3).
*   `output_folder`: The path to the folder where the transcoded/copied MP3 files will be saved.

## Options

*   `-h`, `--help`: Show the help message and exit.
*   `--threads THREADS`: Number of CPU threads to use for transcoding (default: number of CPU cores).
*   `--min-size MIN_SIZE`: Minimum file size in KB to consider a file valid (default: 200KB). Files smaller than this are skipped.
*   `--delete-small`: Delete files smaller than the specified `--min-size`. Use with caution, as this permanently removes files considered potentially fake or incomplete.