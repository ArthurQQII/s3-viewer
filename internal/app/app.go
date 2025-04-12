package app

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	awslocal "github.com/ArthurQQII/s9s/internal/aws"
	"github.com/ArthurQQII/s9s/internal/config"
	"github.com/ArthurQQII/s9s/internal/ui/views"
	"github.com/charmbracelet/bubbles/help"
	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbletea"
)

// App represents the main application
type App struct {
	client       *awslocal.Client
	config       *config.Config
	help         help.Model
	keyMap       *KeyMap
	activeView   string
	profileView  *views.ProfileView
	bucketView   *views.BucketView
	objectView   *views.ObjectView
	statusBar    *views.StatusBar
}

// KeyMap defines the key bindings
type KeyMap struct {
	Quit    key.Binding
	Help    key.Binding
	Back    key.Binding
	Refresh key.Binding
}

// DefaultKeyMap returns the default key bindings
func DefaultKeyMap() *KeyMap {
	return &KeyMap{
		Quit: key.NewBinding(
			key.WithKeys("q", "ctrl+c"),
			key.WithHelp("q/ctrl+c", "quit"),
		),
		Help: key.NewBinding(
			key.WithKeys("?"),
			key.WithHelp("?", "help"),
		),
		Back: key.NewBinding(
			key.WithKeys("esc"),
			key.WithHelp("esc", "back"),
		),
		Refresh: key.NewBinding(
			key.WithKeys("r"),
			key.WithHelp("r", "refresh"),
		),
	}
}

func getAWSProfiles() ([]string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return nil, fmt.Errorf("failed to get home directory: %w", err)
	}

	credentialsFile := filepath.Join(home, ".aws", "credentials")
	configFile := filepath.Join(home, ".aws", "config")

	profiles := make(map[string]bool)
	profiles["default"] = true // Always include default profile

	// Read credentials file
	if credData, err := os.ReadFile(credentialsFile); err == nil {
		// Simple parsing of credentials file
		lines := strings.Split(string(credData), "\n")
		for _, line := range lines {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
				profile := strings.Trim(line, "[]")
				if profile != "default" {
					profiles[profile] = true
				}
			}
		}
	}

	// Read config file
	if configData, err := os.ReadFile(configFile); err == nil {
		// Simple parsing of config file
		lines := strings.Split(string(configData), "\n")
		for _, line := range lines {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, "[profile ") && strings.HasSuffix(line, "]") {
				profile := strings.TrimPrefix(strings.TrimSuffix(line, "]"), "[profile ")
				profiles[profile] = true
			} else if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") && !strings.HasPrefix(line, "[sso-session") {
				profile := strings.Trim(line, "[]")
				if !strings.HasPrefix(profile, "profile ") && profile != "default" {
					profiles[profile] = true
				}
			}
		}
	}

	// Convert map to slice
	result := make([]string, 0, len(profiles))
	for profile := range profiles {
		result = append(result, profile)
	}

	// Sort profiles alphabetically
	sort.Strings(result)

	return result, nil
}

// New creates a new application
func New() (*App, error) {
	profiles, err := getAWSProfiles()
	if err != nil {
		return nil, fmt.Errorf("failed to get AWS profiles: %w", err)
	}

	theme := views.DefaultTheme()
	return &App{
		help:        help.New(),
		keyMap:      DefaultKeyMap(),
		activeView:  "profile",
		profileView: views.NewProfileView(theme, profiles),
		bucketView:  views.NewBucketView(theme),
		objectView:  views.NewObjectView(theme),
		statusBar:   views.NewStatusBar(theme),
	}, nil
}

// Init implements the tea.Model interface
func (a *App) Init() tea.Cmd {
	return nil
}

// Update implements the tea.Model interface
func (a *App) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch {
		case key.Matches(msg, a.keyMap.Quit):
			return a, tea.Quit
		case key.Matches(msg, a.keyMap.Help):
			a.help.ShowAll = !a.help.ShowAll
			return a, nil
		case key.Matches(msg, a.keyMap.Back):
			if a.activeView == "object" {
				a.activeView = "bucket"
				return a, nil
			}
		case key.Matches(msg, a.keyMap.Refresh):
			return a, nil
		}
	case views.ProfileSelectedMsg:
		if err := a.UpdateConfig(msg.Profile, "us-east-1"); err != nil {
			a.statusBar.SetMessage(fmt.Sprintf("Error: %v", err))
			return a, nil
		}
		a.activeView = "bucket"
		
		// Load buckets after profile selection
		fmt.Printf("Loading buckets for profile: %s\n", msg.Profile)
		buckets, err := a.ListBuckets(context.Background())
		if err != nil {
			fmt.Printf("Error loading buckets: %v\n", err)
			a.statusBar.SetMessage(fmt.Sprintf("Error loading buckets: %v", err))
			return a, nil
		}
		fmt.Printf("Found %d buckets\n", len(buckets))
		a.bucketView.SetBuckets(buckets)
		return a, nil
	}

	var cmd tea.Cmd
	switch a.activeView {
	case "profile":
		var model tea.Model
		model, cmd = a.profileView.Update(msg)
		a.profileView = model.(*views.ProfileView)
	case "bucket":
		var model tea.Model
		model, cmd = a.bucketView.Update(msg)
		a.bucketView = model.(*views.BucketView)
	case "object":
		var model tea.Model
		model, cmd = a.objectView.Update(msg)
		a.objectView = model.(*views.ObjectView)
	}

	return a, cmd
}

// View implements the tea.Model interface
func (a *App) View() string {
	switch a.activeView {
	case "profile":
		return a.profileView.View()
	case "bucket":
		return a.bucketView.View()
	case "object":
		return a.objectView.View()
	default:
		return "Invalid view"
	}
}

// Run starts the application
func (a *App) Run() error {
	p := tea.NewProgram(a)
	_, err := p.Run()
	return err
}

// ListBuckets returns a list of S3 buckets
func (a *App) ListBuckets(ctx context.Context) ([]awslocal.BucketItem, error) {
	return a.client.ListBuckets(ctx)
}

// ListObjects returns a list of objects in a bucket
func (a *App) ListObjects(ctx context.Context, bucket, prefix string) ([]awslocal.ObjectItem, error) {
	return a.client.ListObjects(ctx, bucket, prefix, 100)
}

// DownloadObject downloads an object from S3
func (a *App) DownloadObject(ctx context.Context, bucket, key string, w io.Writer) error {
	obj, err := a.client.GetObject(ctx, bucket, key)
	if err != nil {
		return fmt.Errorf("failed to get object: %w", err)
	}
	defer obj.Close()

	_, err = io.Copy(w, obj)
	if err != nil {
		return fmt.Errorf("failed to copy object data: %w", err)
	}

	return nil
}

// GetObjectInfo returns object metadata
func (a *App) GetObjectInfo(ctx context.Context, bucket, key string) (*awslocal.ObjectItem, error) {
	head, err := a.client.HeadObject(ctx, bucket, key)
	if err != nil {
		return nil, fmt.Errorf("failed to get object info: %w", err)
	}

	if head.ContentLength == nil || head.LastModified == nil {
		return nil, fmt.Errorf("invalid object metadata")
	}

	return &awslocal.ObjectItem{
		Key:          key,
		Size:         *head.ContentLength,
		LastModified: *head.LastModified,
		StorageClass: string(head.StorageClass),
		IsDirectory:  false,
	}, nil
}

// UpdateConfig updates the AWS configuration
func (a *App) UpdateConfig(profile, region string) error {
	client, err := awslocal.NewClient(profile, region)
	if err != nil {
		return fmt.Errorf("failed to create new AWS client: %w", err)
	}

	if a.config == nil {
		a.config = &config.Config{}
	}

	a.client = client
	a.config.Profile = profile
	a.config.Region = region

	return nil
} 