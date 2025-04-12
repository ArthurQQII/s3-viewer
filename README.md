# S3 Viewer

A desktop application for browsing and managing AWS S3 buckets with a modern, user-friendly interface.

## Features

### Bucket Navigation
- Browse S3 buckets and folders with an intuitive interface
- Breadcrumb navigation for easy folder traversal
- Efficient loading of large buckets with progressive loading
- Clear folder structure visualization

### File Management
- View file details: name, size, last modified date, and content type
- Download individual files or entire folders
- Preview support for multiple file types:
  - Images: Direct preview in the application
  - Videos: Browser-based preview with pre-signed URLs
  - Text files: Built-in text viewer
  - JSON files: Formatted preview

### Search and Filter
- Real-time search functionality
- Search by:
  - File name
  - File extension (e.g., .mp4, .jpg)
  - Content type
- Clear search button for quick reset

### Sorting
- Sort by any column:
  - Name
  - Size
  - Last Modified
  - Content Type
- Toggle between ascending and descending order

### Performance Features
- Progressive loading for large buckets
- Background loading of objects
- Immediate display of first 100 items
- Responsive UI during loading
- Pagination with customizable page size

### AWS Integration
- AWS CLI profile support
- Secure credential management
- Pre-signed URLs for video streaming
- Proper error handling for invalid credentials

## Requirements

- Python 3.8 or higher
- PyQt6
- boto3
- AWS CLI configured with valid credentials

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/s3-viewer.git
cd s3-viewer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure AWS credentials:
```bash
aws configure
```

## Usage

1. Start the application:
```bash
python src/main.py
```

2. Select an AWS profile from the credentials page
3. Browse your S3 buckets and objects
4. Use the search bar to filter objects
5. Click column headers to sort
6. Double-click folders to navigate
7. Right-click objects for additional options

## Development

The application is built with:
- PyQt6 for the GUI
- boto3 for AWS S3 interaction
- Python's threading for background operations

### Project Structure
```
s3-viewer/
├── src/
│   ├── main.py
│   ├── ui/
│   │   ├── bucket_explorer_page.py
│   │   ├── bucket_list_page.py
│   │   ├── credential_page.py
│   │   ├── loading_animation.py
│   │   └── main_window.py
│   └── utils/
│       └── aws_utils.py
├── requirements.txt
└── README.md
```

## License

[MIT License](LICENSE)

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
