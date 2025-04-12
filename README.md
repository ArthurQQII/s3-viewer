# S9s - Terminal Based S3 Explorer

A powerful, terminal-based S3 bucket explorer with an intuitive interface inspired by k9s.

![S9s Demo](docs/images/demo.gif)

## Features

### Terminal UI
- Clean, responsive terminal interface
- Vim-style keybindings
- Real-time updates
- Resource usage optimized
- Color-coded status indicators

### Navigation
- Fast bucket and object browsing
- Breadcrumb navigation
- Quick folder traversal
- Fuzzy search support
- Customizable views

### File Operations
- Streaming file preview
- Batch operations support
- Progress indicators
- Background downloads
- Multi-file selection

### Performance
- Asynchronous operations
- Efficient memory usage
- Lazy loading of large directories
- Cached responses
- Minimal CPU footprint

### AWS Integration
- AWS profile support
- IAM role assumption
- MFA support
- Cross-region access
- Endpoint configuration

## Installation

### From Source
```bash
go install github.com/ArthurQQII/s9s@latest
```

### Binary Releases
Download the latest release from the [releases page](https://github.com/ArthurQQII/s9s/releases).

## Requirements
- Go 1.21 or higher
- AWS credentials configured
- Terminal with 256 color support

## Usage

1. Start S9s:
```bash
s9s
```

2. Key Bindings:
```
Navigation:
  ↑/k         : Move up
  ↓/j         : Move down
  →/l         : Enter folder
  ←/h         : Go back
  g           : Go to top
  G           : Go to bottom
  /           : Search
  n           : Next search result
  N           : Previous search result

Operations:
  space       : Select item
  d           : Download selected
  p           : Preview file
  c           : Copy path
  r           : Refresh
  s           : Sort menu
  f           : Filter menu

Views:
  1           : Bucket view
  2           : Object view
  3           : Preview view
  :           : Command mode
  ?           : Help

General:
  q           : Back/Quit
  ctrl+c      : Exit
  ctrl+r      : Refresh
```

## Project Structure
```
s9s/
├── cmd/
│   └── s9s/
│       └── main.go
├── internal/
│   ├── app/
│   │   ├── app.go
│   │   └── config.go
│   ├── aws/
│   │   ├── client.go
│   │   └── session.go
│   ├── ui/
│   │   ├── components/
│   │   ├── views/
│   │   └── styles/
│   └── utils/
├── pkg/
│   ├── s3/
│   └── tui/
├── go.mod
├── go.sum
└── README.md
```

## Development

### Architecture
- Clean architecture principles
- Dependency injection
- Interface-based design
- Event-driven UI
- Modular components

### Technology Stack
- [Bubble Tea](https://github.com/charmbracelet/bubbletea) - Terminal UI framework
- [Lip Gloss](https://github.com/charmbracelet/lipgloss) - Style definitions
- [AWS SDK for Go](https://github.com/aws/aws-sdk-go-v2) - AWS integration
- [Cobra](https://github.com/spf13/cobra) - CLI framework
- [Viper](https://github.com/spf13/viper) - Configuration

### Building
```bash
make build
```

### Testing
```bash
make test
```

## Contributing
Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

## License
[MIT License](LICENSE)

<a href="https://www.buymeacoffee.com/aurtherqi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>
