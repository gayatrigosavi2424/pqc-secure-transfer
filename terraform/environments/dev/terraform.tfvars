# Development environment configuration
environment = "dev"
cloud_provider = "aws"
instance_count = 1
instance_size = "small"
enable_autoscaling = false
pqc_algorithm = "Kyber768"

# AWS-specific settings
aws_region = "us-west-2"
aws_instance_type = "t3.medium"

# Resource limits for development
max_instances = 3
min_instances = 1
cpu_limit = "1000m"
memory_limit = "2Gi"

# Security settings
enable_encryption_at_rest = true
enable_encryption_in_transit = true
key_rotation_days = 30

# Monitoring settings
enable_detailed_monitoring = false
log_retention_days = 7