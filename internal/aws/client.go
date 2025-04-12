package aws

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

// Client represents an AWS S3 client
type Client struct {
	s3Client *s3.Client
}

type BucketItem struct {
	Name         string
	CreationDate time.Time
}

type ObjectItem struct {
	Key          string
	Size         int64
	LastModified time.Time
	StorageClass string
	IsDirectory  bool
}

// NewClient creates a new AWS S3 client
func NewClient(profile, region string) (*Client, error) {
	fmt.Printf("Creating AWS client for profile: %s, region: %s\n", profile, region)
	
	cfg, err := config.LoadDefaultConfig(context.Background(),
		config.WithSharedConfigProfile(profile),
		config.WithRegion(region),
		config.WithClientLogMode(aws.LogSigning|aws.LogRetries),
	)
	if err != nil {
		return nil, fmt.Errorf("unable to load SDK config: %w", err)
	}

	// Verify credentials are loaded
	_, err = cfg.Credentials.Retrieve(context.Background())
	if err != nil {
		return nil, fmt.Errorf("unable to retrieve credentials: %w", err)
	}
	fmt.Printf("Successfully loaded credentials for profile: %s\n", profile)

	return &Client{
		s3Client: s3.NewFromConfig(cfg),
	}, nil
}

// ListBuckets returns a list of S3 buckets
func (c *Client) ListBuckets(ctx context.Context) ([]BucketItem, error) {
	result, err := c.s3Client.ListBuckets(ctx, &s3.ListBucketsInput{})
	if err != nil {
		return nil, err
	}

	buckets := make([]BucketItem, len(result.Buckets))
	for i, bucket := range result.Buckets {
		buckets[i] = BucketItem{
			Name:         aws.ToString(bucket.Name),
			CreationDate: aws.ToTime(bucket.CreationDate),
		}
	}

	return buckets, nil
}

// ListObjects returns a list of objects in a bucket
func (c *Client) ListObjects(ctx context.Context, bucket, prefix string, maxKeys int32) ([]ObjectItem, error) {
	input := &s3.ListObjectsV2Input{
		Bucket:  aws.String(bucket),
		Prefix:  aws.String(prefix),
		MaxKeys: aws.Int32(maxKeys),
	}

	result, err := c.s3Client.ListObjectsV2(ctx, input)
	if err != nil {
		return nil, err
	}

	objects := make([]ObjectItem, len(result.Contents))
	for i, obj := range result.Contents {
		objects[i] = ObjectItem{
			Key:          aws.ToString(obj.Key),
			Size:         aws.ToInt64(obj.Size),
			LastModified: aws.ToTime(obj.LastModified),
			StorageClass: string(obj.StorageClass),
			IsDirectory:  false,
		}
	}

	return objects, nil
}

// GetObject returns an object from S3
func (c *Client) GetObject(ctx context.Context, bucket, key string) (io.ReadCloser, error) {
	result, err := c.s3Client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, err
	}

	return result.Body, nil
}

// HeadObject returns object metadata
func (c *Client) HeadObject(ctx context.Context, bucket, key string) (*s3.HeadObjectOutput, error) {
	return c.s3Client.HeadObject(ctx, &s3.HeadObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	})
}
