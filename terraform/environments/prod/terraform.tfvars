# Production environment configuration
environment = "prod"
cloud_provider = "aws"
instance_count = 5
instance_size = "large"
enable_autoscaling = true
pqc_algorithm = "Kyber768"

# AWS-specific settings
aws_region = "us-east-1"
aws_instance_type = "c5.xlarge"

# Resource limits for production
max_instances = 50
min_instances = 3
cpu_limit = "4000m"
memory_limit = "8Gi"

# Security settings
enable_encryption_at_rest = true
enable_encryption_in_transit = true
key_rotation_days = 7

# Monitoring settings
enable_detailed_monitoring = true
log_retention_days = 90