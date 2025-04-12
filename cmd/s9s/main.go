package main

import (
	"fmt"
	"os"

	"github.com/ArthurQQII/s9s/internal/app"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "s9s",
	Short: "S9s is a terminal UI for managing AWS S3 buckets",
	Long: `S9s provides a fast and intuitive terminal interface for browsing and managing AWS S3 buckets.
Features include:
- Vim-style navigation
- Fast file operations
- Real-time updates
- Resource-efficient design`,
	Run: func(cmd *cobra.Command, args []string) {
		app, err := app.New()
		if err != nil {
			fmt.Printf("Error initializing app: %v\n", err)
			os.Exit(1)
		}

		if err := app.Run(); err != nil {
			fmt.Printf("Error running app: %v\n", err)
			os.Exit(1)
		}
	},
}

func init() {
	rootCmd.PersistentFlags().StringP("profile", "p", "", "AWS profile to use")
	rootCmd.PersistentFlags().StringP("region", "r", "", "AWS region to use")
	rootCmd.PersistentFlags().BoolP("debug", "d", false, "Enable debug logging")
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Printf("Error: %v\n", err)
		os.Exit(1)
	}
} 