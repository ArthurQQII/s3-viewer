package views

import (
	"fmt"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
)

// ProfileItem represents a profile in the list
type ProfileItem struct {
	profile string
}

func (i ProfileItem) Title() string       { return i.profile }
func (i ProfileItem) Description() string { return "AWS Profile" }
func (i ProfileItem) FilterValue() string { return i.profile }

// ProfileSelectedMsg is sent when a profile is selected
type ProfileSelectedMsg struct {
	Profile string
}

// ProfileView represents the view for selecting AWS profiles
type ProfileView struct {
	BaseView
	list     list.Model
	profiles []string
}

// NewProfileView creates a new profile view
func NewProfileView(theme Theme, profiles []string) *ProfileView {
	items := make([]list.Item, len(profiles))
	for i, p := range profiles {
		items[i] = ProfileItem{profile: p}
	}

	l := list.New(items, list.NewDefaultDelegate(), 0, 0)
	l.Title = "Select AWS Profile"
	l.SetShowHelp(true)
	l.SetShowStatusBar(false)
	l.SetFilteringEnabled(true)
	l.Styles.Title = titleStyle

	return &ProfileView{
		BaseView: NewBaseView(theme),
		list:     l,
		profiles: profiles,
	}
}

// Init implements tea.Model
func (p *ProfileView) Init() tea.Cmd {
	return nil
}

// Update implements tea.Model
func (p *ProfileView) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "enter" {
			if i, ok := p.list.SelectedItem().(ProfileItem); ok {
				return p, func() tea.Msg {
					return ProfileSelectedMsg{Profile: i.profile}
				}
			}
		}
	case tea.WindowSizeMsg:
		h, v := appStyle.GetFrameSize()
		p.list.SetSize(msg.Width-h, msg.Height-v)
	}

	var cmd tea.Cmd
	p.list, cmd = p.list.Update(msg)
	return p, cmd
}

// View implements tea.Model
func (p *ProfileView) View() string {
	return fmt.Sprintf("\n%s\n\n%s\n\n%s",
		titleStyle.Render("AWS Profile Selection"),
		dimmedStyle.Render("Use ↑/↓ to navigate, Enter to select, ? for help"),
		p.list.View())
} 