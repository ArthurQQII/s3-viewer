package views

import (
	"fmt"
	"time"

	"github.com/ArthurQQII/s9s/internal/aws"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
)

// BucketItem represents a bucket in the list
type BucketItem struct {
	name         string
	creationDate time.Time
}

func (i BucketItem) Title() string       { return i.name }
func (i BucketItem) Description() string { return fmt.Sprintf("Created: %s", i.creationDate.Format("2006-01-02 15:04:05")) }
func (i BucketItem) FilterValue() string { return i.name }

// BucketSelectedMsg is sent when a bucket is selected
type BucketSelectedMsg struct {
	Bucket string
}

// BucketView represents the view for listing S3 buckets
type BucketView struct {
	BaseView
	list list.Model
}

// NewBucketView creates a new bucket view
func NewBucketView(theme Theme) *BucketView {
	l := list.New([]list.Item{}, list.NewDefaultDelegate(), 0, 0)
	l.Title = "Select S3 Bucket"
	l.SetShowHelp(true)
	l.SetFilteringEnabled(true)
	l.Styles.Title = titleStyle

	return &BucketView{
		BaseView: NewBaseView(theme),
		list:     l,
	}
}

// SetBuckets updates the list of buckets
func (b *BucketView) SetBuckets(buckets []aws.BucketItem) {
	items := make([]list.Item, len(buckets))
	for i, bucket := range buckets {
		items[i] = BucketItem{
			name:         bucket.Name,
			creationDate: bucket.CreationDate,
		}
	}
	b.list.SetItems(items)
}

// Init implements the tea.Model interface
func (b *BucketView) Init() tea.Cmd {
	return nil
}

// Update implements the tea.Model interface
func (b *BucketView) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "enter" {
			if i, ok := b.list.SelectedItem().(BucketItem); ok {
				return b, func() tea.Msg {
					return BucketSelectedMsg{Bucket: i.name}
				}
			}
		}
	case tea.WindowSizeMsg:
		h, v := appStyle.GetFrameSize()
		b.list.SetSize(msg.Width-h, msg.Height-v)
	}

	var cmd tea.Cmd
	b.list, cmd = b.list.Update(msg)
	return b, cmd
}

// View implements the tea.Model interface
func (b *BucketView) View() string {
	return fmt.Sprintf("\n%s\n\n%s\n\n%s",
		titleStyle.Render("S3 Bucket Selection"),
		dimmedStyle.Render("Use ↑/↓ to navigate, Enter to select, / to filter, ? for help"),
		b.list.View())
} 