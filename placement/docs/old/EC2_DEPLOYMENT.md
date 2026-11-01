# Deploying to EC2 Instance

This guide covers the steps needed to run the S3 Column Cache system on an EC2 instance.

## Prerequisites

1. **EC2 Instance Requirements**:
   - Amazon Linux 2, Ubuntu, or similar Linux distribution
   - Python 3.8 or higher
   - Sufficient disk space for cache (adjust `max_cache_size_gb` as needed)
   - Internet access for package installation

2. **IAM Role Configuration** (Recommended):
   - Attach an IAM role to your EC2 instance with S3 read permissions
   - Minimum required policy:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "s3:GetObject",
             "s3:ListBucket"
           ],
           "Resource": [
             "arn:aws:s3:::your-bucket-name/*",
             "arn:aws:s3:::your-bucket-name"
           ]
         }
       ]
     }
     ```

## Step-by-Step Deployment

### 1. Transfer Files to EC2

```bash
# From your local machine, copy files to EC2
scp -r /path/to/s3-column-cache ec2-user@your-ec2-ip:/home/ec2-user/
```

Or clone from your repository:
```bash
# On EC2 instance
git clone <your-repo-url>
cd s3-column-cache
```

### 2. Install Python Dependencies

```bash
# Update package manager (Ubuntu/Debian)
sudo apt-get update

# Or for Amazon Linux
sudo yum update -y

# Install Python and pip if not already installed
sudo apt-get install -y python3 python3-pip  # Ubuntu
# OR
sudo yum install -y python3 python3-pip      # Amazon Linux

# Install project dependencies
pip3 install -r requirements.txt
```

### 3. Configure AWS Credentials

**Option A: Use IAM Role (Recommended for EC2)**
- No additional configuration needed if IAM role is attached
- The code will automatically use IAM role credentials via AWS SDK defaults
- Just ensure the region is set correctly in your code

**Option B: Use Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: Use AWS Credentials File**
```bash
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = your-access-key
aws_secret_access_key = your-secret-key
EOF

cat > ~/.aws/config << EOF
[default]
region = us-east-1
EOF
```

### 4. Update Configuration

Edit `example.py` or your application code:

```python
cache = ColumnCache(
    cache_dir="/home/ec2-user/cache",  # Use absolute path
    max_cache_size_gb=10.0,
    s3_region="us-east-1"  # Your S3 bucket region
    # No credentials needed if using IAM role
)
```

### 5. Set Up Cache Directory Permissions

```bash
# Create cache directory with proper permissions
mkdir -p /home/ec2-user/cache
chmod 755 /home/ec2-user/cache
```

### 6. Test the Installation

```bash
# Run the example
python3 example.py
```

## Important Considerations for EC2

### 1. Disk Space Management
- Monitor disk usage: `df -h`
- Adjust `max_cache_size_gb` based on available disk space
- Consider using EBS volumes for cache storage if needed

### 2. Network Configuration
- Ensure security groups allow outbound HTTPS (port 443) for S3 access
- If using VPC endpoints, configure accordingly

### 3. IAM Role vs Credentials
- **Best Practice**: Use IAM roles instead of access keys
- IAM roles are more secure and automatically rotated
- The code supports IAM roles when no explicit credentials are provided

### 4. Cache Directory Location
- Use absolute paths instead of relative paths (`./cache`)
- Consider using `/var/cache/` or `/tmp/` for system-wide deployments
- For persistent cache across reboots, use EBS volumes

### 5. Running as a Service (Optional)

Create a systemd service file `/etc/systemd/system/column-cache.service`:

```ini
[Unit]
Description=S3 Column Cache Service
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/s3-column-cache
ExecStart=/usr/bin/python3 /home/ec2-user/s3-column-cache/your_script.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable column-cache
sudo systemctl start column-cache
```

## Troubleshooting

### Issue: "Access Denied" when accessing S3
- **Solution**: Verify IAM role permissions or credentials
- Test with: `aws s3 ls s3://your-bucket/`

### Issue: "No module named 'duckdb'"
- **Solution**: Ensure you ran `pip3 install -r requirements.txt`
- May need: `pip3 install --user -r requirements.txt`

### Issue: Cache directory permission errors
- **Solution**: Check directory permissions: `ls -la /path/to/cache`
- Fix with: `chmod 755 /path/to/cache`

### Issue: Out of disk space
- **Solution**: Reduce `max_cache_size_gb` or add more storage
- Monitor with: `du -sh /path/to/cache`

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use IAM roles** instead of access keys when possible
3. **Restrict IAM permissions** to only required S3 buckets
4. **Use security groups** to limit network access
5. **Enable CloudTrail** to monitor S3 access

## Performance Optimization

1. **Instance Type**: Choose instance with sufficient memory and network bandwidth
2. **EBS Volume**: Use provisioned IOPS for better cache performance
3. **Cache Size**: Balance between cache hit rate and disk space
4. **Region**: Deploy EC2 in same region as S3 bucket for lower latency

