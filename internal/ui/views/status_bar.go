package views

import (
	"fmt"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

// StatusBar represents the status bar at the bottom of the UI
type StatusBar struct {
	BaseView
	message string
	time    time.Time
}

// NewStatusBar creates a new status bar
func NewStatusBar(theme Theme) *StatusBar {
	return &StatusBar{
		BaseView: NewBaseView(theme),
		time:     time.Now(),
	}
}

// Init implements the tea.Model interface
func (s *StatusBar) Init() tea.Cmd {
	return nil
}

// Update implements the tea.Model interface
func (s *StatusBar) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			return s, tea.Quit
		}
	}

	return s, nil
}

// View implements the tea.Model interface
func (s *StatusBar) View() string {
	return fmt.Sprintf("\n  %s | %s", s.message, s.time.Format("15:04:05"))
}

// SetMessage sets the status bar message
func (s *StatusBar) SetMessage(msg string) {
	s.message = msg
	s.time = time.Now()
} 