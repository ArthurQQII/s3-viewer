# S3 Viewer

A modern, cross-platform desktop application for browsing and managing AWS S3 buckets and objects.

## Features

- Browse S3 buckets and objects with a clean, modern interface
- Support for multiple AWS profiles
- Search and filter buckets and objects
- Download files
- Folder navigation with breadcrumb path
- Pagination for large buckets
- Cross-platform support (Windows, macOS, Linux)

## Requirements

- Python 3.8 or higher
- AWS CLI configured with at least one profile

## Installation

1. Clone the repository:
```bash
git clone git@github.com:ArthurQQII/s3-viewer.git
cd s3-viewer
```

2. Create and activate a virtual environment:
```bash
# Windows
py -m venv venv
.\venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Make sure you have AWS CLI configured with at least one profile:
```bash
aws configure --profile your-profile-name
```

2. Run the application:
```bash
python src/main.py
```

3. Select your AWS profile from the dropdown menu
4. Browse your S3 buckets and objects
5. Double-click on folders to navigate
6. Double-click on files to preview (coming soon)
7. Select a file and click "Download" to save it locally

## Development

The application is built using:
- PyQt6 for the GUI
- boto3 for AWS S3 operations
- Python 3.8+ for the backend

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Building the Application

To build the application into a standalone executable, follow these steps:

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```

2. **Create the Executable**:
   Run the following command in your terminal:
   ```bash
   pyinstaller --onefile --windowed --icon=src/resources/app-icon.png --name=s3-viewer src/main.py
   ```

   - `--onefile`: Packages everything into a single executable.
   - `--windowed`: Suppresses the console window (useful for GUI apps).
   - `--icon`: Specifies the icon for the executable.
   - `--name`: Sets the name of the executable to `s3-viewer`.

3. **Find the Executable**:
   After running the command, you'll find the executable in the `dist` directory.

4. **Test the Executable**:
   Run the executable to ensure everything works as expected.


<a href="https://www.buymeacoffee.com/aurtherqi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
