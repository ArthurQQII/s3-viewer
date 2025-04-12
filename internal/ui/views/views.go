package views

import (
	"github.com/charmbracelet/bubbles/help"
	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
)

// Theme defines the color scheme for the UI
type Theme struct {
	Primary   string
	Secondary string
	Error     string
	Success   string
	Warning   string
	Info      string
}

// DefaultTheme returns the default theme
func DefaultTheme() Theme {
	return Theme{
		Primary:   "#00ff00",
		Secondary: "#666666",
		Error:     "#ff0000",
		Success:   "#00ff00",
		Warning:   "#ffff00",
		Info:      "#0000ff",
	}
}

// View is the interface that all views must implement
type View interface {
	tea.Model
	View() string
	Init() tea.Cmd
	Update(msg tea.Msg) (tea.Model, tea.Cmd)
}

// BaseView provides common functionality for all views
type BaseView struct {
	help help.Model
	keys map[string]key.Binding
	theme Theme
}

// NewBaseView creates a new base view
func NewBaseView(theme Theme) BaseView {
	return BaseView{
		help:  help.New(),
		keys:  make(map[string]key.Binding),
		theme: theme,
	}
}

// Init implements the tea.Model interface
func (b BaseView) Init() tea.Cmd {
	return nil
}

// Update implements the tea.Model interface
func (b BaseView) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	return b, nil
}

// View implements the tea.Model interface
func (b BaseView) View() string {
	return ""
} 