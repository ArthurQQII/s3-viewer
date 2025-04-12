package views

import "github.com/charmbracelet/lipgloss"

var (
	appStyle = lipgloss.NewStyle().
		Margin(1, 2)

	titleStyle = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#00ff00")).
		MarginLeft(2)

	selectedStyle = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#00ff00"))

	dimmedStyle = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#666666"))

	errorStyle = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#ff0000"))

	successStyle = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#00ff00"))

	warningStyle = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#ffff00"))

	infoStyle = lipgloss.NewStyle().
		Foreground(lipgloss.Color("#0000ff"))
) 