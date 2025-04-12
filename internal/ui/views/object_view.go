package views

import (
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
)

// ObjectView represents the view for listing S3 objects
type ObjectView struct {
	BaseView
	list list.Model
}

// NewObjectView creates a new object view
func NewObjectView(theme Theme) *ObjectView {
	return &ObjectView{
		BaseView: NewBaseView(theme),
		list:     list.New([]list.Item{}, list.NewDefaultDelegate(), 0, 0),
	}
}

// Init implements the tea.Model interface
func (o *ObjectView) Init() tea.Cmd {
	return nil
}

// Update implements the tea.Model interface
func (o *ObjectView) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			return o, tea.Quit
		}
	}

	var cmd tea.Cmd
	o.list, cmd = o.list.Update(msg)
	return o, cmd
}

// View implements the tea.Model interface
func (o *ObjectView) View() string {
	return "\n  " + o.list.View()
} 